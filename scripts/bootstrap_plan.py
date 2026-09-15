#!/usr/bin/env python3
"""Produce a read-only, official-source installation plan."""
import argparse, json, os, platform, shutil

TOOLS = {
    "git": "https://git-scm.com/downloads",
    "gh": "https://cli.github.com/",
    "python3": "https://www.python.org/downloads/",
}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("plan", "apply")); parser.add_argument("--confirm", action="store_true"); args = parser.parse_args()
    checks = [{"tool": t, "available": shutil.which(t) is not None, "official_source": url, "mutation": "requires explicit approval"} for t, url in TOOLS.items()]
    ready = all(c["available"] for c in checks)
    if args.command == "apply":
        authorized = args.confirm and os.environ.get("CODERSKILL_BOOTSTRAP_PLAN") == "approved"
        print(json.dumps({"schema": 1, "read_only": False, "status": "authorized" if authorized and ready else "blocked", "reason": None if authorized and ready else "approved expiring plan and --confirm are required", "checks": checks}, indent=2)); return 0 if authorized and ready else 2
    print(json.dumps({"schema": 1, "read_only": True, "platform": platform.platform(), "architecture": platform.machine(), "checks": checks, "status": "ready" if ready else "action-required"}, indent=2))

if __name__ == "__main__": main()
