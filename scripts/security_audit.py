#!/usr/bin/env python3
"""Run a conservative, local-only secret and identifier audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


RULES = (
    ("secret", "critical", re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})")),
    ("private-key", "critical", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("mac-address", "high", re.compile(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}")),
    ("ipv4-address", "medium", re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")),
    ("email-address", "medium", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")),
    ("home-path", "medium", re.compile(r"(?:/var/home/|/home/|/Users/|[A-Za-z]:\\{1,2}Users\\{1,2})(?!user\b|username\b|runner\b|<)[A-Za-z][A-Za-z0-9._-]*")),
)
# Addresses that identify no person: placeholders, documentation domains, service no-reply senders.
BENIGN_EMAIL = re.compile(r"^git@|noreply|no-reply|@example\.(?:com|org|net|invalid)$|\.invalid$|\.test$|\.local$|@localhost|@\d+x\.", re.IGNORECASE)
IGNORED_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache"}


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def publishable(root: Path) -> set[Path] | None:
    """Files that git would publish (tracked or not ignored), or None outside a work tree."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True, check=False,
    )
    if result.returncode != 0:
        return None
    return {root / name for name in result.stdout.decode("utf-8", "replace").split("\0") if name}


def files(root: Path, selected: Path | None, all_files: bool = False, allowed: set[Path] | None = None) -> list[Path]:
    base = (root / selected).resolve() if selected else root
    if not base.is_relative_to(root):
        raise ValueError("scan path must remain inside repository root")
    candidates = [base] if base.is_file() else base.rglob("*")
    if allowed is None and not all_files:
        allowed = publishable(root)
    return [
        path for path in candidates
        if path.is_file()
        and not any(part in IGNORED_DIRS for part in path.relative_to(root).parts)
        and (allowed is None or path in allowed)
    ]


def audit(root: Path, selected: Path | None, all_files: bool = False,
          allowed: set[Path] | None = None) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in files(root, selected, all_files, allowed):
        try:
            data = path.read_bytes()
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for category, severity, rule in RULES:
            for match in rule.finditer(text):
                if category == "email-address" and BENIGN_EMAIL.search(match.group(0)):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                findings.append({
                    "category": category,
                    "severity": severity,
                    "confidence": "high",
                    "path": path.relative_to(root).as_posix(),
                    "line": line,
                    "fingerprint": fingerprint(match.group(0)),
                    "message": "redacted match; inspect locally without publishing the value",
                })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--path", type=Path, help="optional file or directory below root")
    parser.add_argument("--format", choices=("json", "sarif"), default="json")
    parser.add_argument("--all-files", action="store_true", help="also scan git-ignored local files")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        findings = audit(root, args.path, args.all_files)
    except ValueError as error:
        parser.error(str(error))
    if args.format == "sarif":
        output = {
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [{"tool": {"driver": {"name": "coder-skill-security-audit"}}, "results": [
                {"ruleId": item["category"], "level": "error" if item["severity"] in {"critical", "high"} else "warning", "message": {"text": item["message"]}, "locations": [{"physicalLocation": {"artifactLocation": {"uri": item["path"]}, "region": {"startLine": item["line"]}}}]} for item in findings
            ]}],
        }
    else:
        output = {"schema": 1, "status": "findings" if findings else "clean", "findings": findings}
    print(json.dumps(output, indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
