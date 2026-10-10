#!/usr/bin/env python3
"""Install CoderSkill globally and generate a safe project-start prompt."""
from __future__ import annotations
import argparse, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_hooks  # noqa: E402
from build_adapters import digest_tree  # noqa: E402 - the same digest as adapters/manifest.json
from update_channel import (  # noqa: E402
    AGENT_SOURCES, AGENT_TARGETS, RECEIPT, REMOTE_REF, SOURCE_COMMIT, ensure_trust, export_snapshot, fetch,
    git_value, install_lock, installed_commit, read_json, record_source, source_repo, status, unsigned_commits,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]

BACKUP_DIR = Path.home() / ".local/share/coderskill/backups"


def read_receipt(target: Path) -> dict:
    return read_json(target / RECEIPT)


def make_read_only(folder: Path) -> None:
    for item in folder.rglob("*"):
        if item.is_file():
            item.chmod(item.stat().st_mode & ~0o222)


def back_up(agent: str, folder: Path) -> Path:
    """Move a folder out of the skills directory, so the agent never loads the backup as a skill."""
    destination = BACKUP_DIR / agent / f"{folder.name}.backup-{time.strftime('%Y%m%d-%H%M%S')}"
    counter = 1
    while destination.exists():
        destination = destination.with_name(f"{destination.name}-{counter}"); counter += 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder), destination)
    return destination


def install_agent(agent: str, home: Path, source_root: Path, update: bool, force: bool, commit: str | None) -> int:
    source = source_root / AGENT_SOURCES[agent] / "skills"
    target = home / AGENT_TARGETS[agent]
    target.mkdir(parents=True, exist_ok=True)
    receipt = read_receipt(target)
    status = 0
    skills = sorted(p for p in source.iterdir() if p.is_dir())
    for skill in skills:
        destination = target / skill.name
        if destination.exists() and not update:
            print(f"preserved existing {agent}/{skill.name}; use --update to replace")
            continue
        new_digest = digest_tree(skill)
        if destination.exists():
            current = digest_tree(destination)
            if current == new_digest:
                receipt[skill.name] = new_digest
                make_read_only(destination)
                print(f"up to date {agent}/{skill.name}")
                continue
            if receipt.get(skill.name) != current and not force:
                print(f"stopped {agent}/{skill.name}: it was changed after installation (or not installed by CoderSkill); "
                      "rerun with --update --force to back it up and replace it", file=sys.stderr)
                status = 3
                continue
        # Stage next to the target, then swap: readers see the old or the new folder, never a mix.
        staged = target / f".{skill.name}.incoming"
        shutil.rmtree(staged, ignore_errors=True)
        shutil.copytree(skill, staged)
        make_read_only(staged)
        if destination.exists():
            if receipt.get(skill.name) != digest_tree(destination):
                print(f"backed up {agent}/{skill.name} to {back_up(agent, destination)}")
            else:
                shutil.rmtree(destination)
        staged.rename(destination)
        receipt[skill.name] = new_digest
        print(f"installed {agent}/{skill.name}")
    if update:
        names = {skill.name for skill in skills}
        for name in [n for n in receipt if not n.startswith("_") and n not in names]:
            folder = target / name
            if folder.exists() and digest_tree(folder) != receipt[name]:
                print(f"kept {agent}/{name}: removed from CoderSkill but changed locally", file=sys.stderr)
                continue
            shutil.rmtree(folder, ignore_errors=True)
            del receipt[name]
            print(f"removed {agent}/{name}: no longer part of CoderSkill")
    if commit:
        receipt[SOURCE_COMMIT] = commit
    else:
        receipt.pop(SOURCE_COMMIT, None)  # a working-tree install is not a reviewed version
    write_json(target / RECEIPT, receipt)
    return status


def deploy(source_root: Path, agents: list[str], update: bool, force: bool, commit: str | None) -> int:
    home = Path.home()
    status = 0
    for agent in agents:
        status = install_agent(agent, home, source_root, update, force, commit) or status
    # Run the command and the hooks from copies, so that switching branches in a checkout cannot break them.
    share = home / ".local/share/coderskill"
    if (share / "scripts").exists():
        shutil.rmtree(share / "scripts")
    shutil.copytree(source_root / "scripts", share / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    bindir = home / ".local/bin"; bindir.mkdir(parents=True, exist_ok=True)
    link = bindir / "coderskill"
    if link.exists() or link.is_symlink(): link.unlink()
    link.symlink_to(share / "scripts" / "coderskill.py")
    print(f"installed command at {link}")
    if all((source_root / f).is_file() for f in install_hooks.RUNTIME_FILES):
        install_hooks.refresh_installed(source_root)
    return status


def install(update: bool, agents: list[str] | None = None, force: bool = False, worktree: bool = False) -> int:
    if (ROOT / "skills").is_dir() and git_value(ROOT, "rev-parse", "--git-dir"):
        record_source(ROOT)  # running from a clone: remember it as the update source
    selected = agents or [name for name in AGENT_TARGETS if shutil.which(name)]
    if not selected:
        print("No supported AI CLI found; choose with --agents claude,codex,gemini", file=sys.stderr)
        return 2
    if worktree:
        if not (ROOT / "skills").is_dir():
            print("--worktree must run from a CoderSkill clone (scripts/coderskill install --worktree)", file=sys.stderr)
            return 2
        with install_lock():
            return deploy(ROOT, selected, update, force, None)
    repo = source_repo()
    if repo is None:
        print("No CoderSkill clone recorded; run scripts/coderskill install once from the clone", file=sys.stderr)
        return 2
    with install_lock():
        error = ensure_trust()
        if error:
            print(f"cannot verify signatures: {error}", file=sys.stderr)
            return 4
        if fetch(repo, force=True) is False:
            print(f"warning: fetch failed; installing the last fetched {REMOTE_REF}", file=sys.stderr)
        commit = git_value(repo, "rev-parse", "--verify", "--quiet", f"{REMOTE_REF}^{{commit}}")
        if not commit:
            print(f"{REMOTE_REF} not found in {repo.name}", file=sys.stderr)
            return 2
        for agent in selected:
            unsigned = unsigned_commits(repo, installed_commit(agent), commit)
            if unsigned:
                print(f"refusing to install {commit[:12]} for {agent}: commits without a trusted signature: "
                      f"{', '.join(c[:12] for c in unsigned)}", file=sys.stderr)
                return 4
        with tempfile.TemporaryDirectory() as temporary:
            export_snapshot(repo, commit, Path(temporary))
            result = deploy(Path(temporary), selected, update, force, commit)
        for agent in selected:
            status(agent, do_fetch=False)  # refresh the cached state the hooks read
        print(f"installed CoderSkill {commit[:12]} from {REMOTE_REF}")
        return result


def request(title: str, details: str, agent: str | None) -> int:
    """Record a skill change request in the source clone's local, git-ignored .private/ folder."""
    repo = source_repo()
    if repo is None:
        print("No CoderSkill clone recorded; run scripts/coderskill install once from the clone", file=sys.stderr)
        return 2
    folder = repo / ".private" / "change-requests"
    folder.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "request"
    path = folder / f"{time.strftime('%Y-%m-%d')}-{slug}.md"
    counter = 1
    while path.exists():
        path = folder / f"{time.strftime('%Y-%m-%d')}-{slug}-{counter}.md"; counter += 1
    project = Path(git_value(Path.cwd(), "rev-parse", "--show-toplevel") or Path.cwd()).name
    path.write_text(f"# {title}\n\n- Date: {time.strftime('%Y-%m-%d %H:%M')}\n- From project: {project}\n"
                    f"- Agent: {agent or 'unknown'}\n- Status: new\n\n{details.strip()}\n", encoding="utf-8")
    print(f"recorded change request: {path.relative_to(repo)}")
    return 0


def start(args) -> int:
    placeholders = {"https://github.com/droltr/your-project", "https://github.com/droltr/example-project", "droltr/your-project", "droltr/example-project", "/path/to/CoderSkill"}
    supplied = (args.github or "").strip()
    if supplied in placeholders:
        supplied = ""
    detected = subprocess.run(["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True, check=False).stdout.strip()
    repo = supplied or detected or "not yet assigned"
    normalize = lambda value: value.rstrip("/").removesuffix(".git")
    if supplied and detected and normalize(supplied) != normalize(detected):
        print(f"Repository target conflicts with local origin: {supplied} != {detected}", file=sys.stderr)
        return 2
    auth = subprocess.run(["gh", "auth", "status", "--hostname", "github.com"], capture_output=True, text=True, check=False) if shutil.which("gh") else None
    account_line = next((line.strip() for line in ((auth.stdout + "\n" + auth.stderr).splitlines()) if " account " in line.lower()), "unavailable") if auth else "gh CLI unavailable"
    print(f"GitHub identity check: {account_line}")
    print(f"Target repository: {repo}")
    if args.run and not args.confirm_account:
        print("Account confirmation required. Re-run with --confirm-account only after reviewing the identity and target.", file=sys.stderr)
        return 2
    prompt = f"Use the professional-coding skill. Read the current project instructions and profile. GitHub repository: {repo}. Classify this directory, preserve main, select only applicable skills, and execute the complete validated workflow. Do not copy CoderSkill into this project. Do not perform destructive actions, credential operations, or hardware writes. Communicate with the user in the operating system's language. Write repository artifacts in English. Carry the work through without asking whether to continue; stop only for the reasons listed in professional-coding."
    print(prompt)
    if not args.run: return 0
    agent = args.agent
    if not agent:
        available = [name for name in ("codex", "claude", "gemini") if shutil.which(name)]
        if len(available) != 1:
            if not available: print("No supported AI CLI found. Install or specify --agent codex|claude|gemini.", file=sys.stderr)
            else: print("Multiple AI CLIs found; choose one with --agent: " + ", ".join(available), file=sys.stderr)
            return 2
        agent = available[0]
    command = {"codex": "codex", "claude": "claude", "gemini": "gemini"}[agent]
    return subprocess.call([command, prompt])

def main():
    parser = argparse.ArgumentParser(prog="coderskill"); sub = parser.add_subparsers(dest="command", required=True)
    i = sub.add_parser("install"); i.add_argument("--update", action="store_true"); i.add_argument("--force", action="store_true", help="back up and replace skills changed after installation"); i.add_argument("--agents", help="comma-separated: claude,codex,gemini (default: installed CLIs)"); i.add_argument("--worktree", action="store_true", help="owner only: install the clone's working tree instead of the signed origin/main")
    r = sub.add_parser("request", help="record a skill change request for the CoderSkill project"); r.add_argument("title"); r.add_argument("--details", default="", help="what should change and why (no private data)"); r.add_argument("--agent", choices=("claude", "codex", "gemini"))
    s = sub.add_parser("start"); s.add_argument("phrase", nargs="+"); s.add_argument("--github"); s.add_argument("--agent", choices=("codex", "claude", "gemini")); s.add_argument("--run", action="store_true"); s.add_argument("--confirm-account", action="store_true")
    args = parser.parse_args()
    if args.command == "install":
        agents = [a.strip() for a in args.agents.split(",")] if args.agents else None
        unknown = [a for a in agents or [] if a not in AGENT_TARGETS]
        if unknown: print(f"unknown agent(s): {', '.join(unknown)}", file=sys.stderr); return 2
        return install(args.update, agents, args.force, args.worktree)
    if args.command == "request":
        return request(args.title, args.details or (sys.stdin.read() if not sys.stdin.isatty() else ""), args.agent)
    phrase = " ".join(args.phrase).lower()
    if phrase not in ("execute order 66", "projeye başla", "projeye basla"): print("Use: coderskill start execute order 66 (or: projeye başla)", file=sys.stderr); return 2
    return start(args)

if __name__ == "__main__": raise SystemExit(main())
