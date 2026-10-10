#!/usr/bin/env python3
"""Install the CoderSkill agent hooks into user-level agent settings.

Claude Code: ~/.claude/settings.json (https://code.claude.com/docs/en/hooks.md)
Codex:       ~/.codex/hooks.json     (openai/codex rust-v0.162.1, codex-rs/config/src/hook_config.rs)
Gemini CLI:  ~/.gemini/settings.json (https://github.com/google-gemini/gemini-cli/blob/v0.63.0/docs/hooks/reference.md)

Existing CoderSkill entries are replaced, other hooks are kept, and every changed file is
backed up first. Use --dry-run to print the result without writing.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "coderskill_hook.py"
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
                "command": f'python3 -I "{HOOK}" {argument} --agent {agent}',
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("agents", nargs="+", choices=sorted(TARGETS))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not HOOK.is_file():
        print(f"hook script not found: {HOOK}", file=sys.stderr)
        return 2
    for agent in args.agents:
        install(agent, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
