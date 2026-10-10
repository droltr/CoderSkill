#!/usr/bin/env python3
"""Record and check the confirmed GitHub identity and target for a repository.

`check` compares the authenticated `gh` account and the `origin` remote with the local record
`.coderskill/local/identity.json` and prints one of: `match`, `missing`, `mismatch`.
`confirm` writes the record; run it only after the user confirmed the shown values.
The record is local and git-ignored; it never contains tokens.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

RECORD = Path(".coderskill") / "local" / "identity.json"


def run(*command: str, cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=20, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def origin_repository(origin: str) -> str:
    """Return owner/name from a GitHub remote URL, without credentials."""
    clean = re.sub(r"[?#].*$", "", origin).rstrip("/")
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", clean)
    return f"{match.group(1)}/{match.group(2)}" if match else ""


def current(root: Path) -> dict[str, str]:
    origin = run("git", "remote", "get-url", "origin", cwd=root)
    return {
        "account": run("gh", "api", "user", "--jq", ".login"),
        "repository": origin_repository(origin),
        "origin": re.sub(r"//[^@/]*@", "//", origin),
    }


def compare(record: dict | None, now: dict[str, str]) -> tuple[str, list[str]]:
    if not record:
        return "missing", []
    changed = [key for key in ("account", "repository", "origin") if record.get(key) != now.get(key)]
    return ("mismatch", changed) if changed else ("match", [])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("check", "confirm"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = Path(run("git", "rev-parse", "--show-toplevel", cwd=args.root) or args.root)
    path = root / RECORD
    now = current(root)
    if args.command == "confirm":
        if not now["account"] or not now["repository"]:
            print(json.dumps({"status": "unavailable", "current": now}, indent=2))
            return 2
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**now, "confirmed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "recorded", "current": now}, indent=2))
        return 0
    try:
        record = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, json.JSONDecodeError):
        record = None
    status, changed = compare(record, now)
    print(json.dumps({"status": status, "changed": changed, "current": now}, indent=2))
    return {"match": 0, "missing": 3, "mismatch": 4}[status]


if __name__ == "__main__":
    sys.exit(main())
