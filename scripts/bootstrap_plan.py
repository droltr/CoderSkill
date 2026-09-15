#!/usr/bin/env python3
"""Produce a read-only, official-source installation plan."""
import json, platform, shutil

TOOLS = {
    "git": "https://git-scm.com/downloads",
    "gh": "https://cli.github.com/",
    "python3": "https://www.python.org/downloads/",
}

def main():
    checks = [{"tool": t, "available": shutil.which(t) is not None, "official_source": url, "mutation": "requires explicit approval"} for t, url in TOOLS.items()]
    print(json.dumps({"schema": 1, "read_only": True, "platform": platform.platform(), "architecture": platform.machine(), "checks": checks, "status": "ready" if all(c["available"] for c in checks) else "action-required"}, indent=2))

if __name__ == "__main__": main()
