#!/usr/bin/env python3
"""Git pre-push check: refuse updates to protected branches on any remote.

Installed globally through `core.hooksPath` by `scripts/install-hooks git`. Git passes every
ref it is about to push on stdin (`<local ref> <local sha> <remote ref> <remote sha>`, see
https://git-scm.com/docs/githooks#_pre_push), so aliases, `HEAD`, `-C`, `cd` and wildcard
refspecs are all covered, for agents and for manual pushes.

The owner can allow a deliberate push for one command with
`CODERSKILL_ALLOW_PROTECTED_PUSH=1 git push ...`; the agent hook denies that variable.
After the check the repository's own `.git/hooks/pre-push` runs with the same input.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coderskill_hook import OVERRIDE_VARIABLE as OVERRIDE, PROTECTED_BRANCHES, run_repository_hook  # noqa: E402

PROTECTED = {f"refs/heads/{branch}" for branch in PROTECTED_BRANCHES}


def blocked_refs(lines: list[str]) -> list[str]:
    refs = []
    for line in lines:
        parts = line.split()
        if len(parts) == 4 and parts[2] in PROTECTED:
            refs.append(parts[2])
    return refs


def main() -> int:
    data = sys.stdin.read()
    refs = blocked_refs(data.splitlines())
    if refs and os.environ.get(OVERRIDE) != "1":
        print(f"CoderSkill pre-push: refusing to update {', '.join(sorted(set(refs)))}.", file=sys.stderr)
        print("Push a topic branch and open a pull request. For a deliberate owner push, run the command "
              f"again with {OVERRIDE}=1.", file=sys.stderr)
        return 1
    return run_repository_hook("pre-push", sys.argv[1:], data)


if __name__ == "__main__":
    sys.exit(main())
