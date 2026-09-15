#!/usr/bin/env python3
"""Run read-only publication checks for the requested repository scope."""
from __future__ import annotations
import argparse, json, subprocess

def run(command):
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return {"command": " ".join(command), "returncode": result.returncode, "output": result.stdout.strip()[-2000:]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("staged", "branch", "history"), default="branch")
    args = parser.parse_args()
    checks = [run(["python3", "-m", "unittest", "discover", "-s", "tests", "-v"]), run(["scripts/build-adapters", "--check"]), run(["scripts/security-audit", "--format", "json", "--root", "."]), run(["git", "diff", "--check"])]
    print(json.dumps({"schema": 1, "scope": args.scope, "read_only": True, "status": "pass" if all(c["returncode"] == 0 for c in checks) else "fail", "checks": checks}, indent=2))
    return 0 if all(c["returncode"] == 0 for c in checks) else 1

if __name__ == "__main__": raise SystemExit(main())
