#!/usr/bin/env python3
"""Create a read-only start plan for the current project directory."""
import json, subprocess
from pathlib import Path

def main():
    root = Path.cwd(); entries = [p.name for p in root.iterdir() if p.name != ".git"]
    has_git = (root / ".git").exists(); kind = "empty" if not entries else ("git-project" if has_git else "non-git-project")
    branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, check=False).stdout.strip() if has_git else None
    print(json.dumps({"schema": 1, "read_only": True, "directory": ".", "classification": kind, "current_branch": branch, "steps": ["read local instructions and profile", "verify tools and synchronization", "select applicable focused skills", "record purpose and constraints", "plan issue and topic branch", "validate before PR"], "mutations": "not performed"}, indent=2))

if __name__ == "__main__": main()
