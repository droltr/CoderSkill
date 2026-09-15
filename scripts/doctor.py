#!/usr/bin/env python3
"""Read-only local project and tool readiness report.

The command never installs packages, fetches repositories, changes Git
configuration, authenticates, or writes files. Its JSON output is safe to pipe
to another process; raw command output is intentionally not included.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


COMMANDS = {
    "git": ["git", "--version"],
    "gh": ["gh", "--version"],
    "codex": ["codex", "--version"],
    "claude": ["claude", "--version"],
    "gemini": ["gemini", "--version"],
    "python": ["python3", "--version"],
    "node": ["node", "--version"],
    "go": ["go", "version"],
    "rust": ["rustc", "--version"],
    "java": ["java", "--version"],
}

MANIFEST_TOOLS = {
    "pyproject.toml": ("python",),
    "requirements.txt": ("python",),
    "package.json": ("node",),
    "go.mod": ("go",),
    "Cargo.toml": ("rust",),
    "pom.xml": ("java",),
    "build.gradle": ("java",),
}


def run(command: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, "unavailable"
    if result.returncode != 0:
        return False, "execution-failed"
    version = (result.stdout or result.stderr).splitlines()
    return True, version[0].strip() if version else ""


def tool_status(name: str, command: list[str], root: Path) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if not executable:
        return {"status": "missing"}
    ok, version = run(command, root)
    return {"status": "ready" if ok else "execution-failed", "version": version or "available"}


def git_value(root: Path, args: list[str]) -> str | None:
    ok, value = run(["git", *args], root)
    return value if ok else None


def repository_state(root: Path) -> dict[str, Any]:
    top = git_value(root, ["rev-parse", "--show-toplevel"])
    if not top:
        return {"status": "not-a-worktree"}
    branch = git_value(root, ["branch", "--show-current"]) or "detached"
    origin = git_value(root, ["remote", "get-url", "origin"])
    remote_identity = None
    if origin:
        clean = re.sub(r"[?#].*$", "", origin).rstrip("/")
        match = re.search(r"(?:github\.com[/:])([^/]+)/([^/]+?)(?:\.git)?$", clean)
        if match:
            remote_identity = f"{match.group(1)}/{match.group(2)}"
    status = git_value(root, ["status", "--porcelain=v1"])
    return {
        "status": "ready",
        "branch": branch,
        "origin_identity": remote_identity or ("unverified" if origin else "missing"),
        "worktree": "clean" if status == "" else "changes-present",
    }


def required_tools(root: Path) -> dict[str, dict[str, Any]]:
    required = {"git", "python"}
    if (root / ".git").exists():
        required.add("gh")
    for marker, tools in MANIFEST_TOOLS.items():
        if (root / marker).is_file():
            required.update(tools)
    return {name: tool_status(name, COMMANDS[name], root) for name in sorted(required)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    repo = repository_state(root)
    tools = required_tools(root)
    result: dict[str, Any] = {
        "schema": 1,
        "status": "ready",
        "system": {
            "os": platform.system(),
            "os_version": platform.release(),
            "architecture": platform.machine(),
            "shell": os.environ.get("SHELL") or os.environ.get("ComSpec") or "unknown",
        },
        "repository": repo,
        "tools": tools,
        "notes": [],
    }
    if repo["status"] != "ready":
        result["status"] = "not-ready"
        result["notes"].append("current directory is not a Git worktree")
    for name, details in tools.items():
        if details["status"] != "ready":
            result["status"] = "not-ready"
            result["notes"].append(f"{name}: {details['status']}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
