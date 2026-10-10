#!/usr/bin/env python3
"""CoderSkill agent hook: load the rules at session start and enforce the mandatory ones.

Usage: coderskill_hook.py <event> [--agent claude|codex|gemini]

Events and the hook they serve:
  session-start   SessionStart     inject the CoderSkill rules, sync state, open requests
  subagent-start  SubagentStart    inject the CoderSkill rules into a subagent
  prompt          UserPromptSubmit log the request locally; reinforce "stop"
  pre-tool        PreToolUse       deny merges/pushes to main, staged secrets, bad file names;
                                   ask before hardware writes
  stop            Stop             block once on unlabelled hedging; remind about records
  session-end     SessionEnd       copy the transcript into the project (git-ignored)

The input JSON shapes follow the Claude Code hooks reference
(https://code.claude.com/docs/en/hooks.md); Codex 0.162.1 uses the same field names and
`hookSpecificOutput.additionalContext` (openai/codex, tag rust-v0.162.1, hooks schema).

A hook must never break a session: on any internal error it exits 0 without output, so the
rules fail open. The permission system, not this script, is the hard security boundary.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
CONTEXT_FILE = HOOK_DIR / "session-context.md"
LOCAL_DIR = ".agent-sessions"
PRIVATE_DIR = ".private"
# Request logs, newest layout first; docs/REQUESTS.md is the older tracked layout.
REQUEST_FILES = (f"{PRIVATE_DIR}/requests.md", "docs/REQUESTS.md")
MAX_LISTED_FILES = 20
OPEN_MARKERS = ("🔄", "⏳", "❓")
MAX_OPEN_REQUESTS = 10

sys.path.insert(0, str(HOOK_DIR.parent / "scripts"))
from security_audit import RULES  # noqa: E402 - shared with the repository audit

# Only critical findings block a commit; identifiers are left to the full audit.
SECRET_PATTERNS = tuple((name, pattern) for name, severity, pattern in RULES if severity == "critical")
PROTECTED_BRANCHES = {"main", "master"}
# Commands that can write to hardware. Each entry: program, then optional argument markers
# of which at least one must be present; an empty tuple means every invocation.
HARDWARE_WRITES = {
    "i2cset": (),
    "i2ctransfer": (),
    "flashrom": ("-w", "--write", "-E", "--erase"),
    "nvflash": (),
    "setpci": ("=",),
    "nvidia-smi": ("-pl", "--power-limit", "-ac", "--applications-clocks", "-lgc", "-lmc", "--gpu-reset", "-r"),
    "liquidctl": ("set", "initialize"),
    "openrgb": ("-c", "--color", "-m", "--mode", "-b", "--brightness", "--profile", "-p"),
    "ipmitool": ("raw",),
    "ectool": (),
    "dd": ("of=/dev/",),
}
NAME_ALLOWED = re.compile(r"^[A-Za-z0-9._@\[\]-]+$")  # [] and @ for framework names (e.g. [id].tsx, icon@2x.png)
WINDOWS_RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.IGNORECASE)
NAME_SKIP_PARTS = {".git", "node_modules", "vendor", "third_party", "third-party", ".venv"}
HEDGES = re.compile(
    r"\b(probably|most likely|likely|presumably|muhtemelen|büyük ihtimalle|büyük olasılıkla|sanırım|galiba|herhalde)\b",
    re.IGNORECASE,
)
LABELS = re.compile(r"UNVERIFIED|ASSUMPTION|DOĞRULANMADI|VARSAYIM", re.IGNORECASE)
STOP_WORDS = {"dur", "stop", "dur!", "stop!", "durdur"}


# ---------------------------------------------------------------- helpers


def project_root(cwd: str | None) -> Path | None:
    """Return the git work-tree root of cwd, or None outside a repository."""
    if not cwd:
        return None
    top = git_out(Path(cwd), "rev-parse", "--show-toplevel")
    return Path(top) if top else None


LOCAL_IGNORE = "# Local agent session data. Never commit.\n*\n"


def local_dir(root: Path) -> Path | None:
    """Return the git-ignored local record folder, or None when it is not safe to write.

    A cloned repository is untrusted: it may track files or symlinks under the folder, or
    un-ignore it, to redirect prompts and transcripts into tracked or arbitrary files.
    """
    path = root / LOCAL_DIR
    if path.is_symlink() or git_out(root, "ls-files", "--", LOCAL_DIR):
        return None
    path.mkdir(exist_ok=True)
    if path.resolve() != root.resolve() / LOCAL_DIR:
        return None
    ignore = path / ".gitignore"
    if ignore.is_symlink():
        return None
    if not ignore.exists() or ignore.read_text(encoding="utf-8", errors="replace") != LOCAL_IGNORE:
        write_replacing(ignore, LOCAL_IGNORE.encode())
    # The repository's own .gitignore can re-include the folder; refuse in that case.
    probe = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", f"{LOCAL_DIR}/requests.jsonl"],
        capture_output=True, timeout=5, check=False,
    )
    return path if probe.returncode == 0 else None


def safe_subdir(base: Path, name: str) -> Path | None:
    """Create base/name unless it is a symlink."""
    path = base / name
    if path.is_symlink():
        return None
    path.mkdir(exist_ok=True)
    return path


def write_replacing(target: Path, data: bytes | None = None, source: Path | None = None) -> None:
    """Write data (or stream source) through a new temporary file and rename it over target.

    Renaming replaces a symlink at target instead of writing through it.
    """
    import shutil
    import tempfile  # imported here: most hook events never write files

    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            if source is not None:
                with open(source, "rb") as reader:
                    shutil.copyfileobj(reader, handle)
            else:
                handle.write(data or b"")
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def append_no_follow(target: Path, text: str) -> None:
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(text)


def current_branch(cwd: str) -> str:
    return git_out(Path(cwd), "branch", "--show-current")


def context_output(event: str, text: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def pre_tool_output(decision: str, reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def request_file(root: Path) -> Path | None:
    for relative in REQUEST_FILES:
        if (root / relative).is_file():
            return root / relative
    return None


def open_requests(path: Path) -> list[str]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("| ") and any(marker in line for marker in OPEN_MARKERS):
            rows.append(line.strip())
    return rows


def git_out(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def signing_configured(root: Path) -> bool:
    """True when git will sign commits here with a key file that exists."""
    if git_out(root, "config", "--type=bool", "--get", "commit.gpgsign") != "true":
        return False
    key = git_out(root, "config", "--get", "user.signingkey")
    if git_out(root, "config", "--get", "gpg.format") == "ssh" and not key.startswith("key::"):
        return bool(key) and Path(key).expanduser().is_file()
    return bool(key)


def sync_report(root: Path) -> list[str]:
    """Describe how the local repository differs from its remote, as of the last fetch."""
    lines = []
    changed = [l for l in git_out(root, "status", "--porcelain").splitlines() if l]
    if changed:
        lines.append(f"- {len(changed)} uncommitted change(s).")
    refs = git_out(root, "for-each-ref", "--format=%(refname:short)|%(upstream:short)|%(upstream:track)", "refs/heads")
    no_upstream, ahead = [], []
    for ref in refs.splitlines():
        name, upstream, track = (ref.split("|") + ["", ""])[:3]
        if not upstream:
            no_upstream.append(name)
        elif "gone" in track:
            lines.append(f"- {name}: upstream {upstream} is gone (merged or deleted on the remote).")
        else:
            if "ahead" in track:
                ahead.append(name)
            if "behind" in track:
                lines.append(f"- {name}: {track.strip('[]')} compared with {upstream}.")
    if ahead:
        lines.append(f"- Unpushed commits on: {', '.join(ahead)}.")
    if no_upstream:
        lines.append(f"- Branches without a remote copy: {', '.join(no_upstream)}.")
    if not git_out(root, "remote"):
        lines.append("- No remote configured; GitHub does not track this project yet.")
    if not signing_configured(root):
        lines.append("- Commit signing is not configured on this machine; set it up before committing "
                     "(professional-coding, environment-bootstrap: Commit signing).")
    fetch_head = root / ".git" / "FETCH_HEAD"
    if lines and fetch_head.is_file():
        age_hours = (time.time() - fetch_head.stat().st_mtime) / 3600
        lines.append(f"- Based on the last fetch, {age_hours:.0f} hour(s) ago; run `git fetch` for current data.")
    return lines


def run_repository_hook(name: str, argv: list[str], data: str | None = None) -> int:
    """Run the repository's own git hook of the same name, as git would without core.hooksPath."""
    common = git_out(Path.cwd(), "rev-parse", "--git-common-dir")
    hook = Path(common) / "hooks" / name
    if common and hook.is_file() and os.access(hook, os.X_OK):
        return subprocess.run([str(hook), *argv], input=data, text=True, check=False).returncode
    return 0


# ---------------------------------------------------------------- session start


def system_language() -> str | None:
    """Return the locale's language tag (``tr_TR.UTF-8`` -> ``tr-TR``), or None for C/POSIX."""
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):  # POSIX precedence for message language
        value = os.environ.get(name, "").split(".")[0].split("@")[0]
        if value:
            return None if value in ("C", "POSIX") else value.replace("_", "-")
    return None


def language_note() -> str:
    tag = system_language()
    if tag:
        return f"\nUser communication language: {tag} (system locale). Write everything in the repository in English."
    return ("\nUser communication language: no system locale is set; use the language the user writes in. "
            "Write everything in the repository in English.")


def session_start(data: dict, subagent: bool = False) -> dict:
    text = CONTEXT_FILE.read_text(encoding="utf-8") + language_note() + "\n"
    root = None if subagent else project_root(data.get("cwd"))
    if root:
        save_snapshot(root, data.get("session_id"))
        notes = [f"\nProject root: {root.name}"]
        if (root / ".coderskill" / "project.yml").is_file():
            notes.append("Project profile: .coderskill/project.yml (read it).")
        sync = sync_report(root)
        if sync:
            notes.append("Local and GitHub state:")
            notes.extend(sync)
        requests = request_file(root)
        rows = open_requests(requests) if requests else []
        if rows:
            notes.append(f"Open requests in {requests.relative_to(root)} ({len(rows)}):")
            notes.extend(rows[:MAX_OPEN_REQUESTS])
            if len(rows) > MAX_OPEN_REQUESTS:
                notes.append(f"... and {len(rows) - MAX_OPEN_REQUESTS} more.")
        research = sorted((root / PRIVATE_DIR / "research").glob("*.md"))
        if research:
            notes.append(f"Research notes in {PRIVATE_DIR}/research/ (read before researching again):")
            notes.extend(f"- {path.name}" for path in research[-MAX_LISTED_FILES:])
        text += "\n".join(notes) + "\n"
    return context_output("SubagentStart" if subagent else "SessionStart", text)


# ---------------------------------------------------------------- user prompt


def prompt(data: dict, agent: str) -> dict | None:
    text = data.get("prompt") or ""
    root = project_root(data.get("cwd"))
    if root and text.strip():
        record = {
            "time": int(time.time()),
            "agent": agent,
            "session_id": data.get("session_id"),
            "prompt": text,
        }
        folder = local_dir(root)
        if folder:
            append_no_follow(folder / "requests.jsonl", json.dumps(record, ensure_ascii=False) + "\n")
    if text.strip().lower() in STOP_WORDS:
        return context_output(
            "UserPromptSubmit",
            "The user said STOP. Make no further tool calls on the target. Report the current "
            "state: what was done, what is unverified, and what is left.",
        )
    return None


# ---------------------------------------------------------------- pre tool use


HEREDOC = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
SEPARATORS = re.compile(r"\|\||&&|;|\||(?<![<>&])&(?![&>])|\n")
# Options of sudo/doas that take a value.
SUDO_VALUE_OPTIONS = {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U", "-T", "--user", "--group",
                      "--host", "--prompt", "--chdir", "--role", "--type", "--other-user", "--command-timeout"}
ENV_VALUE_OPTIONS = {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
OVERRIDE_VARIABLE = "CODERSKILL_ALLOW_PROTECTED_PUSH"
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Variables that change git configuration (and so can switch hooks off) for one command.
GIT_CONFIG_VARIABLES = ("GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM",
                        "GIT_CONFIG_NOSYSTEM", "GIT_DIR", "GIT_EXEC_PATH")
# git commit options whose value is the next argument.
COMMIT_VALUE_OPTIONS = {"-m", "-F", "-c", "-C", "-t", "--message", "--file", "--author", "--date",
                        "--template", "--reuse-message", "--reedit-message", "--fixup", "--squash", "--cleanup"}


def strip_heredocs(command: str) -> str:
    """Remove here-document bodies: they are data for a command, not commands."""
    lines, kept, delimiter, strip_tabs = command.split("\n"), [], None, False
    for line in lines:
        if delimiter is not None:
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                delimiter = None
            continue
        kept.append(line)
        match = HEREDOC.search(line)
        if match:
            strip_tabs, delimiter = match.group(1) == "-", match.group(3)
    return "\n".join(kept)


def unwrap(tokens: list[str]) -> list[str] | str:
    """Drop wrappers such as VAR=value, sudo -u x, env -i, nice -n 5, timeout 10.

    Returns the remaining tokens, or the inner command string of `sh -c` / `eval`.
    """
    while tokens:
        head = Path(tokens[0]).name
        if ASSIGNMENT.match(tokens[0]):
            tokens = tokens[1:]
        elif head in ("sudo", "doas", "env"):
            values = SUDO_VALUE_OPTIONS if head != "env" else ENV_VALUE_OPTIONS
            rest = tokens[1:]
            while rest and (rest[0].startswith("-") or (head == "env" and "=" in rest[0])):
                option = rest.pop(0)
                if option == "--":
                    break
                if option in values and rest:
                    rest.pop(0)
            tokens = rest
        elif head in ("exec", "command", "nohup", "time", "builtin"):
            tokens = tokens[1:]
        elif head == "nice":
            rest = tokens[1:]
            if rest[:1] == ["-n"]:
                rest = rest[2:]
            elif rest and rest[0].startswith("-"):
                rest = rest[1:]
            tokens = rest
        elif head == "timeout":
            rest = tokens[1:]
            while rest and rest[0].startswith("-"):
                option = rest.pop(0)
                if option in ("-s", "--signal", "-k", "--kill-after") and rest:
                    rest.pop(0)
            tokens = rest[1:]  # drop the duration
        elif head in SHELLS and "-c" in tokens[1:]:
            index = tokens.index("-c")
            return tokens[index + 1] if index + 1 < len(tokens) else ""
        elif head == "eval":
            return " ".join(tokens[1:])
        else:
            return tokens
    return tokens


def split_commands(command: str, cwd: str, depth: int = 0) -> list[tuple[list[str], str, list[str]]]:
    """Split a shell command line into (tokens, working directory, assignments). No execution.

    Follows `cd <dir>` and nested `sh -c` / `eval` strings. This is best effort: the git
    pre-push hook and the agent permission system remain the hard boundaries.
    """
    commands = []
    for part in SEPARATORS.split(strip_heredocs(command)):
        try:
            tokens = shlex.split(part, comments=True)
        except ValueError:
            tokens = part.split()
        assignments = [t.split("=", 1)[0] for t in tokens if ASSIGNMENT.match(t)]
        if tokens and tokens[0] == "cd":
            if len(tokens) > 1:
                cwd = os.path.join(cwd, os.path.expanduser(tokens[1]))
            continue
        inner = unwrap(tokens)
        if isinstance(inner, str):
            if depth < 3:
                commands.extend(split_commands(inner, cwd, depth + 1))
            continue
        if inner:
            commands.append((inner, cwd, assignments))
    return commands


HOOK_SETTINGS = re.compile(r"^core\.hookspath\b|^core\.hookspath=", re.IGNORECASE)


def git_args(tokens: list[str], cwd: str) -> tuple[list[str], str, list[str]] | None:
    """Return (git arguments, repository directory, `-c` settings), or None if not git."""
    if Path(tokens[0]).name != "git":
        return None
    args, settings = tokens[1:], []
    while args and args[0].startswith("-"):
        option = args.pop(0)
        if option == "-C" and args:
            cwd = os.path.join(cwd, os.path.expanduser(args.pop(0)))
        elif option in ("-c", "--config-env") and args:
            settings.append(args.pop(0))
        elif option.startswith(("--config-env=", "-c")) and len(option) > 2:
            settings.append(option.split("=", 1)[1] if option.startswith("--") else option[2:])
        elif option in ("--git-dir", "--work-tree", "--namespace", "--exec-path") and args:
            args.pop(0)
    return args, cwd, settings


def push_targets(refspecs: list[str], cwd: str) -> list[str]:
    """Remote branch names a push would update, as far as the command line shows them."""
    targets = []
    for ref in refspecs:
        ref = ref.removeprefix("+")
        destination = ref.split(":", 1)[1] if ":" in ref else ref
        if destination in ("HEAD", "@"):
            destination = current_branch(cwd)
        targets.append(destination.removeprefix("refs/heads/"))
    return targets


def commit_includes_worktree(rest: list[str]) -> bool:
    """True when `git commit` takes changes beyond the index (-a, --all, -i/-o, or pathspecs)."""
    index = 0
    while index < len(rest):
        arg = rest[index]
        index += 1
        if arg == "--":
            return index < len(rest)
        if arg in ("--all", "--include", "--only", "-i", "-o"):
            return True
        if arg.startswith("--"):
            if arg in COMMIT_VALUE_OPTIONS:
                index += 1
            continue
        if arg.startswith("-") and len(arg) > 1:
            for position, letter in enumerate(arg[1:]):
                if letter == "a":
                    return True
                if letter in "mFcCt":
                    if position == len(arg) - 2:
                        index += 1  # the value is the next argument
                    break
            continue
        return True  # a pathspec
    return False


def check_git(args: list[str], cwd: str, settings: list[str] | None = None) -> tuple[str, str] | None:
    if any(HOOK_SETTINGS.match(setting) for setting in settings or []):
        return "deny", "CoderSkill: overriding core.hooksPath switches off the git hooks that protect main and block secrets."
    if not args:
        return None
    sub, rest = args[0], args[1:]
    if sub in ("push", "commit") and ("--no-verify" in rest or (sub == "commit" and "-n" in rest)):
        return "deny", "CoderSkill: --no-verify skips the git hooks that protect main and block secrets."
    if sub == "push":
        if any(flag in rest for flag in ("--all", "--mirror")):
            return "deny", "CoderSkill: pushing all branches or mirroring is not allowed; push a topic branch."
        positional = [a for a in rest if not a.startswith("-")]
        refspecs = positional[1:]
        targets = push_targets(refspecs, cwd) if refspecs else [current_branch(cwd)]
        for target in targets:
            # A wildcard refspec such as refs/heads/*:refs/heads/* also writes main.
            hit = [b for b in PROTECTED_BRANCHES if target and fnmatch.fnmatchcase(b, target)]
            if hit:
                return "deny", f"CoderSkill: never push to {hit[0]}. Push a topic branch and open a pull request; the user merges."
    if sub == "merge" and current_branch(cwd) in PROTECTED_BRANCHES:
        return "deny", "CoderSkill: merging into a protected branch is the user's action."
    if sub == "commit":
        finding = staged_secret(cwd, worktree=commit_includes_worktree(rest))
        if finding:
            return "deny", f"CoderSkill: the commit would contain a {finding}. Remove it before committing."
    return None


def staged_secret(cwd: str, worktree: bool = False) -> str | None:
    """Return a redacted description of the first secret in lines the commit would add."""
    diff_args = ["diff", "HEAD"] if worktree else ["diff", "--cached"]
    try:
        diff = subprocess.run(
            ["git", "-C", cwd, *diff_args, "--no-color", "-U0"],
            capture_output=True, text=True, timeout=20, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    current = "?"
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else line[4:]
            continue
        if not line.startswith("+"):
            continue
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                return f"{name} in {current}"
    return None


def check_hardware(tokens: list[str]) -> tuple[str, str] | None:
    program = Path(tokens[0]).name
    markers = HARDWARE_WRITES.get(program)
    if markers is None:
        return None
    def matches(marker: str, arg: str) -> bool:
        # Plain markers are whole arguments; markers with "=" or "/" match inside one.
        return arg == marker or (("=" in marker or "/" in marker) and marker in arg)

    if markers and not any(matches(m, arg) for m in markers for arg in tokens[1:]):
        return None
    return "ask", (
        f"CoderSkill: `{program}` can write to hardware. Confirm the exact device, the documented "
        "value, the rollback packet, and that the user authorized this write now."
    )


def merges_pull_request(tokens: list[str]) -> bool:
    if Path(tokens[0]).name != "gh":
        return False
    if tokens[1:3] == ["pr", "merge"]:
        return True
    return len(tokens) > 1 and tokens[1] == "api" and any(re.search(r"pulls/\d+/merge", t) for t in tokens[2:])


def bash_decision(command: str, cwd: str) -> tuple[str, str] | None:
    result = None
    for tokens, directory, assignments in split_commands(command, cwd):
        if OVERRIDE_VARIABLE in assignments:
            return "deny", f"CoderSkill: {OVERRIDE_VARIABLE} is reserved for the user."
        if Path(tokens[0]).name == "git" and any(v in assignments for v in GIT_CONFIG_VARIABLES):
            return "deny", "CoderSkill: GIT_CONFIG_* and GIT_DIR overrides can switch off the git hooks."
        if merges_pull_request(tokens):
            return "deny", "CoderSkill: the user performs every merge. Report that the pull request is ready instead."
        parsed = git_args(tokens, directory)
        found = check_git(*parsed) if parsed is not None else check_hardware(tokens)
        if found and found[0] == "deny":
            return found
        result = result or found
    return result


def write_decision(file_path: str) -> tuple[str, str] | None:
    path = Path(file_path)
    if path.exists() or NAME_SKIP_PARTS.intersection(path.parts):
        return None
    new_parts = []
    probe = path
    while not probe.exists() and probe != probe.parent:
        new_parts.append(probe.name)
        probe = probe.parent
    bad = [part for part in new_parts
           if part and (not NAME_ALLOWED.match(part) or part.endswith(".") or WINDOWS_RESERVED.match(part))]
    if bad:
        return "deny", (
            f"CoderSkill: new name {bad[0]!r} is not GitHub-compatible. Use ASCII letters, digits, "
            "'.', '-' and '_' only (kebab-case), no spaces or special characters, no trailing dot, "
            "and no Windows reserved names such as CON or NUL."
        )
    return None


def pre_tool(data: dict) -> dict | None:
    tool = data.get("tool_name")
    tool_input = data.get("tool_input") or {}
    cwd = data.get("cwd") or "."
    if tool == "Bash":
        found = bash_decision(tool_input.get("command") or "", cwd)
    elif tool == "Write":
        found = write_decision(tool_input.get("file_path") or "")
    else:
        found = None
    return pre_tool_output(*found) if found else None


# ---------------------------------------------------------------- stop


def unlabelled_hedges(message: str) -> list[str]:
    text = re.sub(r"```.*?```", "", message, flags=re.DOTALL)
    hits = []
    for line in text.splitlines():
        line = re.sub(r"`[^`]*`", "", line)
        if LABELS.search(line):
            continue
        match = HEDGES.search(line)
        if match:
            hits.append(match.group(0))
    return hits


def stop(data: dict) -> dict | None:
    if data.get("stop_hook_active"):
        return None
    hits = unlabelled_hedges(data.get("last_assistant_message") or "")
    if hits:
        return {
            "decision": "block",
            "reason": (
                f"CoderSkill: the answer uses hedging without a label ({', '.join(sorted(set(hits)))}). "
                "Rewrite those statements: verify them and cite the source, or label them "
                "UNVERIFIED / ASSUMPTION (DOĞRULANMADI / VARSAYIM) with what would verify them."
            ),
        }
    root = project_root(data.get("cwd"))
    if root and records_missing(root, data.get("session_id")):
        return {
            "systemMessage": (
                "CoderSkill: files changed in this session but neither the request log "
                f"({PRIVATE_DIR}/requests.md) nor a session record ({PRIVATE_DIR}/sessions/) was updated."
            )
        }
    return None


SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def worktree_state(root: Path) -> dict[str, str]:
    """Map each changed path to its status and modification time."""
    state = {}
    for line in git_out(root, "status", "--porcelain", "--untracked-files=all").splitlines():
        path = line[3:]
        if not path or path.startswith(LOCAL_DIR):
            continue
        try:
            mtime = (root / path).stat().st_mtime_ns
        except OSError:
            mtime = 0
        state[path] = f"{line[:2]}:{mtime}"
    return state


def snapshot_file(root: Path, session_id: str | None) -> Path | None:
    folder = local_dir(root)
    if not folder or not session_id or not SESSION_ID.fullmatch(session_id):
        return None
    state_dir = safe_subdir(folder, "state")
    return state_dir / f"{session_id}.json" if state_dir else None


def save_snapshot(root: Path, session_id: str | None) -> None:
    """Record the work-tree state at session start, so later checks see only this session's changes."""
    path = snapshot_file(root, session_id)
    if path and not path.exists():
        data = {"started": time.time(), "state": worktree_state(root)}
        write_replacing(path, json.dumps(data).encode())


def records_missing(root: Path, session_id: str | None) -> bool:
    """True when files changed during this session but no record was touched."""
    path = snapshot_file(root, session_id)
    if not path or not path.is_file() or path.is_symlink():
        return False
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    started = snapshot.get("started", 0)
    records = [*(root / r for r in REQUEST_FILES), *(root / PRIVATE_DIR / "sessions").glob("*.md")]
    if any(p.is_file() and p.stat().st_mtime >= started for p in records):
        return False
    before = snapshot.get("state", {})
    return any(before.get(p) != value for p, value in worktree_state(root).items())


# ---------------------------------------------------------------- session end


def session_end(data: dict, agent: str) -> None:
    source = data.get("transcript_path")
    root = project_root(data.get("cwd"))
    if not source or not root or not Path(source).is_file():
        return
    folder = local_dir(root)
    target_dir = safe_subdir(folder, "transcripts") if folder else None
    if not target_dir:
        return
    source_path = Path(source)
    write_replacing(target_dir / f"{agent}-{source_path.name}", source=source_path)
    subagents = source_path.with_suffix("") / "subagents"
    copy_root = safe_subdir(target_dir, f"{agent}-{source_path.stem}-subagents") if subagents.is_dir() else None
    if copy_root is None:
        return
    for item in sorted(subagents.rglob("*")):
        if item.is_symlink() or not item.is_file():
            continue
        parent = copy_root
        for part in item.relative_to(subagents).parent.parts:
            parent = safe_subdir(parent, part) if parent else None
        if parent:
            write_replacing(parent / item.name, source=item)


# ---------------------------------------------------------------- main


def run(event: str, agent: str, data: dict) -> dict | None:
    if event == "session-start":
        return session_start(data)
    if event == "subagent-start":
        return session_start(data, subagent=True)
    if event == "prompt":
        return prompt(data, agent)
    if event == "pre-tool":
        return pre_tool(data)
    if event == "stop":
        return stop(data)
    if event == "session-end":
        session_end(data, agent)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("event", choices=("session-start", "subagent-start", "prompt", "pre-tool", "stop", "session-end"))
    parser.add_argument("--agent", default="claude", choices=("claude", "codex", "gemini"))
    args = parser.parse_args()
    try:
        data = json.load(sys.stdin)
        output = run(args.event, args.agent, data if isinstance(data, dict) else {})
    except Exception:  # noqa: BLE001 - a hook must never break the agent session
        return 0
    if output:
        print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
