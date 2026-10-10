#!/usr/bin/env python3
"""Git pre-commit check: keep private working files and credentials out of every commit.

Installed globally through `core.hooksPath` by `scripts/install-hooks git`. Unlike the agent
hooks it also runs for manual commits and for every tool that calls git. It then runs the
repository's own `.git/hooks/pre-commit`, if any, so existing hooks keep working.

`git commit --no-verify` skips it; the agent hook and CI remain as further checks.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coderskill_hook import LOCAL_DIR, PRIVATE_DIR, staged_secret  # noqa: E402

PRIVATE_PREFIXES = (f"{PRIVATE_DIR}/", f"{LOCAL_DIR}/")
# Local notes that the workspace keeps out of Git through the global ignore file.
PRIVATE_NAMES = {"PROJECT_SCOPE.md", "PROJECT_STATUS_REPORT.md", "PROJECT_TASKS.md"}


def staged_paths() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        capture_output=True, text=True, check=False,
    ).stdout
    return [p for p in out.split("\0") if p]


def private_paths(paths: list[str]) -> list[str]:
    return [
        p for p in paths
        if any(f"/{prefix}" in f"/{p}" for prefix in PRIVATE_PREFIXES) or Path(p).name in PRIVATE_NAMES
    ]


def run_repository_hook() -> int:
    common = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=False,
    ).stdout.strip()
    hook = Path(common) / "hooks" / "pre-commit"
    if common and hook.is_file() and os.access(hook, os.X_OK):
        return subprocess.run([str(hook), *sys.argv[1:]], check=False).returncode
    return 0


def main() -> int:
    blocked = private_paths(staged_paths())
    if blocked:
        print("CoderSkill pre-commit: private working files are staged:", file=sys.stderr)
        for path in blocked[:20]:
            print(f"  {path}", file=sys.stderr)
        print("Unstage them with `git restore --staged <path>`; they belong in the local .private/ folder.", file=sys.stderr)
        return 1
    finding = staged_secret(".")
    if finding:
        print(f"CoderSkill pre-commit: staged changes contain a {finding}. Remove it before committing.", file=sys.stderr)
        return 1
    return run_repository_hook()


if __name__ == "__main__":
    sys.exit(main())
