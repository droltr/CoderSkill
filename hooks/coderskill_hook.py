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
import hashlib
import json
import re
import shlex
import shutil
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
NAME_ALLOWED = re.compile(r"^[A-Za-z0-9._@+\[\]-]+$")
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
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else None


def local_dir(root: Path) -> Path:
    """Create the git-ignored local record folder and return it."""
    path = root / LOCAL_DIR
    path.mkdir(exist_ok=True)
    ignore = path / ".gitignore"
    if not ignore.exists():
        ignore.write_text("# Local agent session data. Never commit.\n*\n", encoding="utf-8")
    return path


def current_branch(cwd: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", cwd, "branch", "--show-current"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


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
    fetch_head = root / ".git" / "FETCH_HEAD"
    if lines and fetch_head.is_file():
        age_hours = (time.time() - fetch_head.stat().st_mtime) / 3600
        lines.append(f"- Based on the last fetch, {age_hours:.0f} hour(s) ago; run `git fetch` for current data.")
    return lines


# ---------------------------------------------------------------- session start


def session_start(data: dict, subagent: bool = False) -> dict:
    text = CONTEXT_FILE.read_text(encoding="utf-8")
    root = project_root(data.get("cwd"))
    if root and not subagent:
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
        with open(local_dir(root) / "requests.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    if text.strip().lower() in STOP_WORDS:
        return context_output(
            "UserPromptSubmit",
            "The user said STOP. Make no further tool calls on the target. Report the current "
            "state: what was done, what is unverified, and what is left.",
        )
    return None


# ---------------------------------------------------------------- pre tool use


def split_commands(command: str) -> list[list[str]]:
    """Split a shell command line into simple commands (best effort, no execution)."""
    parts = re.split(r"\|\||&&|;|\||\n", command)
    commands = []
    for part in parts:
        try:
            tokens = shlex.split(part, comments=True)
        except ValueError:
            tokens = part.split()
        while tokens and ("=" in tokens[0] and not tokens[0].startswith("-")) and tokens[0] not in ("=",):
            tokens = tokens[1:]  # drop leading VAR=value assignments
        while tokens and tokens[0] in ("sudo", "doas", "env", "exec", "command", "nohup", "time"):
            tokens = tokens[1:]
        if tokens:
            commands.append(tokens)
    return commands


def git_args(tokens: list[str]) -> list[str] | None:
    """Return git arguments without global options, or None if not a git command."""
    if Path(tokens[0]).name != "git":
        return None
    args = tokens[1:]
    while args and args[0].startswith("-"):
        option = args.pop(0)
        if option in ("-C", "-c", "--git-dir", "--work-tree") and args:
            args.pop(0)
    return args


def check_git(args: list[str], cwd: str) -> tuple[str, str] | None:
    if not args:
        return None
    sub, rest = args[0], args[1:]
    if sub == "push":
        if any(flag in rest for flag in ("--all", "--mirror")):
            return "deny", "CoderSkill: pushing all branches or mirroring is not allowed; push a topic branch."
        positional = [a for a in rest if not a.startswith("-")]
        refspecs = positional[1:]
        for ref in refspecs:
            target = ref.split(":")[-1].removeprefix("+").removeprefix("refs/heads/")
            # A wildcard refspec such as refs/heads/*:refs/heads/* also writes main.
            hit = [b for b in PROTECTED_BRANCHES if fnmatch.fnmatchcase(b, target)]
            if hit:
                return "deny", f"CoderSkill: never push to {hit[0]}. Push a topic branch and open a pull request; the user merges."
        if not refspecs and current_branch(cwd) in PROTECTED_BRANCHES:
            return "deny", "CoderSkill: the current branch is protected. Create a topic branch and push that."
    if sub == "merge" and current_branch(cwd) in PROTECTED_BRANCHES:
        return "deny", "CoderSkill: merging into a protected branch is the user's action."
    if sub == "commit":
        finding = staged_secret(cwd)
        if finding:
            return "deny", f"CoderSkill: staged changes contain a {finding}. Remove it before committing."
    return None


def staged_secret(cwd: str) -> str | None:
    """Return a redacted description of the first secret in added staged lines."""
    try:
        diff = subprocess.run(
            ["git", "-C", cwd, "diff", "--cached", "--no-color", "-U0"],
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
            match = pattern.search(line)
            if match:
                digest = hashlib.sha256(match.group(0).encode()).hexdigest()[:12]
                return f"{name} in {current} (fingerprint {digest})"
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


def bash_decision(command: str, cwd: str) -> tuple[str, str] | None:
    lowered = command.lower()
    if re.search(r"\bgh\s+pr\s+merge\b", lowered) or (
        re.search(r"\bgh\s+api\b", lowered) and re.search(r"pulls/\d+/merge", lowered)
    ):
        return "deny", "CoderSkill: the user performs every merge. Report that the pull request is ready instead."
    result = None
    for tokens in split_commands(command):
        args = git_args(tokens)
        found = check_git(args, cwd) if args is not None else check_hardware(tokens)
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
    bad = [part for part in new_parts if part and not NAME_ALLOWED.match(part)]
    if bad:
        return "deny", (
            f"CoderSkill: new name {bad[0]!r} is not GitHub-compatible. Use ASCII letters, digits, "
            "'.', '-' and '_' only (kebab-case), no spaces or special characters."
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


def records_missing(root: Path, session_id: str | None) -> bool:
    """True when this session logged requests and changed files but touched no record."""
    log = root / LOCAL_DIR / "requests.jsonl"
    if not log.is_file() or not session_id:
        return False
    started = None
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("session_id") == session_id:
            started = entry.get("time")
            break
    if started is None:
        return False
    try:
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    changed = [line[3:] for line in status.splitlines() if line[3:] and not line[3:].startswith(LOCAL_DIR)]
    if not changed:
        return False
    records = [*(root / r for r in REQUEST_FILES), *(root / PRIVATE_DIR / "sessions").glob("*.md")]
    return not any(p.is_file() and p.stat().st_mtime >= started for p in records)


# ---------------------------------------------------------------- session end


def session_end(data: dict, agent: str) -> None:
    source = data.get("transcript_path")
    root = project_root(data.get("cwd"))
    if not source or not root or not Path(source).is_file():
        return
    target_dir = local_dir(root) / "transcripts"
    target_dir.mkdir(exist_ok=True)
    source_path = Path(source)
    shutil.copy2(source_path, target_dir / f"{agent}-{source_path.name}")
    subagents = source_path.with_suffix("") / "subagents"
    if subagents.is_dir():
        shutil.copytree(subagents, target_dir / f"{agent}-{source_path.stem}-subagents", dirs_exist_ok=True)


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
