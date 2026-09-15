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
)
IGNORED_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache"}


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def files(root: Path, selected: Path | None) -> list[Path]:
    base = (root / selected).resolve() if selected else root
    if not base.is_relative_to(root):
        raise ValueError("scan path must remain inside repository root")
    candidates = [base] if base.is_file() else base.rglob("*")
    return [path for path in candidates if path.is_file() and not any(part in IGNORED_DIRS for part in path.relative_to(root).parts)]


def audit(root: Path, selected: Path | None) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in files(root, selected):
        try:
            data = path.read_bytes()
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for category, severity, rule in RULES:
            for match in rule.finditer(text):
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
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        findings = audit(root, args.path)
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
