#!/usr/bin/env python3
"""Install CoderSkill globally and generate a safe project-start prompt."""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_adapters import digest_tree  # noqa: E402 - the same digest as adapters/manifest.json

ROOT = Path(__file__).resolve().parents[1]

RECEIPT = ".coderskill-installed.json"
AGENT_SOURCES = {"claude": ".claude", "codex": ".agents", "gemini": ".gemini"}
# Codex reads user skills from ~/.codex/skills and ~/.agents/skills (openai/codex, codex-rs/ext/skills/src/host_roots.rs).
AGENT_TARGETS = {"claude": ".claude/skills", "codex": ".codex/skills", "gemini": ".gemini/skills"}


def read_receipt(target: Path) -> dict:
    try:
        return json.loads((target / RECEIPT).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def install_agent(agent: str, home: Path, update: bool, force: bool) -> int:
    source = ROOT / AGENT_SOURCES[agent] / "skills"
    target = home / AGENT_TARGETS[agent]
    target.mkdir(parents=True, exist_ok=True)
    receipt = read_receipt(target)
    status = 0
    for skill in sorted(p for p in source.iterdir() if p.is_dir()):
        destination = target / skill.name
        if destination.exists() and not update:
            print(f"preserved existing {agent}/{skill.name}; use --update to replace")
            continue
        new_digest = digest_tree(skill)
        if destination.exists():
            current = digest_tree(destination)
            if current == new_digest:
                receipt[skill.name] = new_digest
                print(f"up to date {agent}/{skill.name}")
                continue
            if receipt.get(skill.name) != current:
                if not force:
                    print(f"stopped {agent}/{skill.name}: it was changed after installation (or not installed by CoderSkill); "
                          "rerun with --update --force to back it up and replace it", file=sys.stderr)
                    status = 3
                    continue
                backup = destination.with_name(f"{skill.name}.backup-{time.strftime('%Y%m%d-%H%M%S')}")
                destination.rename(backup)
                print(f"backed up {agent}/{skill.name} to {backup.name}")
            else:
                shutil.rmtree(destination)
        shutil.copytree(skill, destination)
        receipt[skill.name] = new_digest
        print(f"installed {agent}/{skill.name}")
    (target / RECEIPT).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return status


def install(update: bool, agents: list[str] | None = None, force: bool = False) -> int:
    home = Path.home()
    if not (ROOT / "skills").is_dir():
        print("install must run from a CoderSkill clone (scripts/coderskill install)", file=sys.stderr)
        return 2
    selected = agents or [name for name in AGENT_TARGETS if shutil.which(name)]
    if not selected:
        print("No supported AI CLI found; choose with --agents claude,codex,gemini", file=sys.stderr)
        return 2
    status = 0
    for agent in selected:
        status = install_agent(agent, home, update, force) or status
    # Run the command from a copy so that switching branches in this checkout cannot break it.
    share = home / ".local/share/coderskill"
    if (share / "scripts").exists():
        shutil.rmtree(share / "scripts")
    shutil.copytree(ROOT / "scripts", share / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    bindir = home / ".local/bin"; bindir.mkdir(parents=True, exist_ok=True)
    link = bindir / "coderskill"
    if link.exists() or link.is_symlink(): link.unlink()
    link.symlink_to(share / "scripts" / "coderskill.py")
    print(f"installed command at {link}")
    return status


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
    i = sub.add_parser("install"); i.add_argument("--update", action="store_true"); i.add_argument("--force", action="store_true", help="back up and replace skills changed after installation"); i.add_argument("--agents", help="comma-separated: claude,codex,gemini (default: installed CLIs)")
    s = sub.add_parser("start"); s.add_argument("phrase", nargs="+"); s.add_argument("--github"); s.add_argument("--agent", choices=("codex", "claude", "gemini")); s.add_argument("--run", action="store_true"); s.add_argument("--confirm-account", action="store_true")
    args = parser.parse_args()
    if args.command == "install":
        agents = [a.strip() for a in args.agents.split(",")] if args.agents else None
        unknown = [a for a in agents or [] if a not in AGENT_TARGETS]
        if unknown: print(f"unknown agent(s): {', '.join(unknown)}", file=sys.stderr); return 2
        return install(args.update, agents, args.force)
    phrase = " ".join(args.phrase).lower()
    if phrase not in ("execute order 66", "projeye başla", "projeye basla"): print("Use: coderskill start execute order 66 (or: projeye başla)", file=sys.stderr); return 2
    return start(args)

if __name__ == "__main__": raise SystemExit(main())
