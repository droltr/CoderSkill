#!/usr/bin/env python3
"""Run read-only publication checks for the requested repository scope.

Scopes decide what the privacy and secret audit looks at:
  staged   files in the index (what the next commit would contain)
  branch   files changed since the merge base with the base branch (default: main)
  history  every line ever added in any reachable commit (secrets and private keys only)
Tests, adapter drift and patch formatting run for every scope.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from security_audit import RULES, audit, fingerprint, publishable  # noqa: E402

HISTORY_RULES = [rule for rule in RULES if rule[0] in {"secret", "private-key"}]


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return {"command": " ".join(command), "returncode": result.returncode, "output": result.stdout.strip()[-2000:]}


def git_lines(*args: str) -> list[str]:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return [line for line in result.stdout.splitlines() if line] if result.returncode == 0 else []


def scope_files(scope: str, base: str) -> list[str]:
    if scope == "staged":
        return git_lines("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return git_lines("diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD")


def history_findings() -> list[dict]:
    log = subprocess.run(["git", "log", "--all", "-p", "--no-color", "-U0", "--format=@%H"],
                         capture_output=True, text=True, errors="replace", check=False).stdout
    findings, commit, path = [], "", ""
    for line in log.splitlines():
        if line.startswith("@") and len(line) == 41:
            commit = line[1:11]
        elif line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("+"):
            for category, severity, rule in HISTORY_RULES:
                for match in rule.finditer(line):
                    findings.append({"category": category, "severity": severity, "commit": commit,
                                     "path": path, "fingerprint": fingerprint(match.group(0))})
    return findings


def audit_check(scope: str, base: str) -> dict:
    root = Path.cwd().resolve()
    if scope == "history":
        findings = history_findings()
        description = "history secret scan"
    else:
        paths = scope_files(scope, base)
        allowed = publishable(root)
        findings = [item for path in paths if (root / path).is_file() for item in audit(root, Path(path), allowed=allowed)]
        description = f"{scope} audit of {len(paths)} file(s)"
    return {"command": description, "returncode": 1 if findings else 0,
            "output": json.dumps(findings)[-2000:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scope", choices=("staged", "branch", "history"), default="branch")
    parser.add_argument("--base", default="main", help="base branch for the branch scope")
    args = parser.parse_args()
    checks = [
        audit_check(args.scope, args.base),
        run(["python3", "-m", "unittest", "discover", "-s", "tests"]),
        run(["scripts/build-adapters", "--check"]),
        run(["git", "diff", "--check"]),
    ]
    ok = all(c["returncode"] == 0 for c in checks)
    print(json.dumps({"schema": 1, "scope": args.scope, "read_only": True, "status": "pass" if ok else "fail", "checks": checks}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
