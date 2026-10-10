#!/usr/bin/env python3
"""Install the CoderSkill agent hooks into user-level agent settings.

Claude Code: ~/.claude/settings.json (https://code.claude.com/docs/en/hooks.md)
Codex:       ~/.codex/hooks.json     (openai/codex rust-v0.162.1, codex-rs/config/src/hook_config.rs)
Gemini CLI:  ~/.gemini/settings.json (https://github.com/google-gemini/gemini-cli/blob/v0.63.0/docs/hooks/reference.md)
Git:         global core.hooksPath and global ignore file (https://git-scm.com/docs/githooks,
             https://git-scm.com/docs/gitignore)

The hook files are copied to ~/.config/coderskill/ first, so the installed hooks do not
depend on the branch checked out in this repository. Every command ends in `|| true`: a
missing interpreter or script must never turn into exit code 2, which blocks a tool call.
Existing CoderSkill entries are replaced, other hooks are kept, and every changed file is
backed up first. Use --dry-run to print the result without writing.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
INSTALL_DIR = CONFIG_HOME / "coderskill"
# Copied to the same relative paths under INSTALL_DIR; the hook imports scripts/security_audit.py.
RUNTIME_FILES = (
    "hooks/coderskill_hook.py",
    "hooks/git_pre_commit.py",
    "hooks/git_pre_push.py",
    "hooks/session-context.md",
    "scripts/security_audit.py",
)
HOOK = INSTALL_DIR / "hooks" / "coderskill_hook.py"
GIT_PRE_COMMIT = INSTALL_DIR / "hooks" / "git_pre_commit.py"
GIT_PRE_PUSH = INSTALL_DIR / "hooks" / "git_pre_push.py"
GIT_HOOKS_DIR = INSTALL_DIR / "git-hooks"
GLOBAL_IGNORES = (".private/", ".agent-sessions/", ".coderskill/local/")
# Client-side hooks that are passed through to the repository's own hook.
CHAINED_GIT_HOOKS = (
    "applypatch-msg", "pre-applypatch", "post-applypatch", "pre-merge-commit",
    "prepare-commit-msg", "commit-msg", "post-commit", "pre-rebase", "post-checkout",
    "post-merge", "pre-auto-gc", "post-rewrite",
)
CHAIN_SCRIPT = """#!/bin/sh
# CoderSkill: run the repository's own hook of the same name, if present.
hook="$(git rev-parse --git-common-dir)/hooks/$(basename "$0")"
if [ -x "$hook" ]; then exec "$hook" "$@"; fi
exit 0
"""
MARKER = "coderskill_hook.py"

# event -> (hook argument, matcher or None, timeout in seconds)
CLAUDE_EVENTS = {
    "SessionStart": ("session-start", None, 10),
    "SubagentStart": ("subagent-start", None, 10),
    "UserPromptSubmit": ("prompt", None, 10),
    "PreToolUse": ("pre-tool", "Bash|Write", 30),
    "Stop": ("stop", None, 10),
    "SessionEnd": ("session-end", None, 60),
}
# Codex runs the same events; its PreToolUse tool names are not mapped yet.
CODEX_EVENTS = {k: v for k, v in CLAUDE_EVENTS.items() if k != "PreToolUse"}
GEMINI_EVENTS = {"SessionStart": ("session-start", None, 10)}

TARGETS = {
    "claude": (Path.home() / ".claude" / "settings.json", CLAUDE_EVENTS, 1),
    "codex": (Path.home() / ".codex" / "hooks.json", CODEX_EVENTS, 1),
    # Gemini CLI timeouts are in milliseconds.
    "gemini": (Path.home() / ".gemini" / "settings.json", GEMINI_EVENTS, 1000),
}


def entry(agent: str, argument: str, matcher: str | None, timeout: int) -> dict:
    group: dict = {
        "hooks": [
            {
                "type": "command",
                "command": f'python3 -I "{HOOK}" {argument} --agent {agent} || true',
                "timeout": timeout,
            }
        ]
    }
    if matcher:
        group["matcher"] = matcher
    return group


def is_coderskill(group: dict) -> bool:
    return any(MARKER in str(hook.get("command", "")) for hook in group.get("hooks", []))


def merged(settings: dict, agent: str, events: dict, timeout_unit: int) -> dict:
    hooks = settings.setdefault("hooks", {})
    for event, (argument, matcher, timeout) in events.items():
        groups = [g for g in hooks.get(event, []) if not is_coderskill(g)]
        groups.append(entry(agent, argument, matcher, timeout * timeout_unit))
        hooks[event] = groups
    return settings


def install(agent: str, dry_run: bool) -> None:
    path, events, unit = TARGETS[agent]
    settings = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    result = merged(settings, agent, events, unit)
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if dry_run:
        print(f"--- {path} (dry run)\n{text}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}.bak-{stamp}")
        counter = 1
        while backup.exists():  # never overwrite an earlier backup
            backup = path.with_name(f"{path.name}.bak-{stamp}-{counter}")
            counter += 1
        shutil.copy2(path, backup)
        print(f"backup: {backup}")
    path.write_text(text, encoding="utf-8")
    print(f"installed {len(events)} hook(s) for {agent}: {path}")


def git_config(*args: str) -> str:
    return subprocess.run(["git", "config", "--global", *args], capture_output=True, text=True, check=False).stdout.strip()


def global_ignore_file() -> Path:
    configured = git_config("core.excludesfile")
    if configured:
        return Path(os.path.expanduser(configured))
    return CONFIG_HOME / "git" / "ignore"


def install_git(dry_run: bool, force: bool) -> int:
    current = git_config("core.hooksPath")
    if current and Path(os.path.expanduser(current)) != GIT_HOOKS_DIR and not force:
        print(f"global core.hooksPath is already {current}; rerun with --force to replace it", file=sys.stderr)
        return 2
    ignore = global_ignore_file()
    existing = ignore.read_text(encoding="utf-8").splitlines() if ignore.is_file() else []
    missing = [line for line in GLOBAL_IGNORES if line not in existing]
    if dry_run:
        print(f"--- git (dry run)\nhooks: {GIT_HOOKS_DIR} (pre-commit, pre-push + {len(CHAINED_GIT_HOOKS)} chained)")
        print(f"git config --global core.hooksPath {GIT_HOOKS_DIR}")
        print(f"append to {ignore}: {missing or 'nothing'}")
        return 0
    GIT_HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    # Unlike the agent hooks, the git hooks fail closed: git stops if the check cannot run.
    for name, script in (("pre-commit", GIT_PRE_COMMIT), ("pre-push", GIT_PRE_PUSH)):
        path = GIT_HOOKS_DIR / name
        path.write_text(f'#!/bin/sh\nexec python3 -I "{script}" "$@"\n', encoding="utf-8")
        path.chmod(0o755)
    for name in CHAINED_GIT_HOOKS:
        path = GIT_HOOKS_DIR / name
        path.write_text(CHAIN_SCRIPT, encoding="utf-8")
        path.chmod(0o755)
    subprocess.run(["git", "config", "--global", "core.hooksPath", str(GIT_HOOKS_DIR)], check=True)
    if missing:
        ignore.parent.mkdir(parents=True, exist_ok=True)
        with open(ignore, "a", encoding="utf-8") as handle:
            if existing and existing[-1].strip():
                handle.write("\n")
            handle.write("# CoderSkill: local-only private work files\n" + "\n".join(missing) + "\n")
    print(f"installed git hooks: {GIT_HOOKS_DIR}; global ignore: {ignore}")
    return 0


def copy_runtime(dry_run: bool) -> None:
    if dry_run:
        print(f"copy hook runtime to {INSTALL_DIR}")
        return
    for source in RUNTIME_FILES:
        destination = INSTALL_DIR / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / source, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("agents", nargs="+", choices=sorted([*TARGETS, "git"]))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="replace another global core.hooksPath")
    args = parser.parse_args()
    missing = [source for source in RUNTIME_FILES if not (REPO / source).is_file()]
    if missing:
        print(f"hook files not found in this checkout: {', '.join(missing)}", file=sys.stderr)
        return 2
    copy_runtime(args.dry_run)
    status = 0
    for agent in args.agents:
        if agent == "git":
            status = install_git(args.dry_run, args.force) or status
        else:
            install(agent, args.dry_run)
    return status


if __name__ == "__main__":
    sys.exit(main())
