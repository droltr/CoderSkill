#!/usr/bin/env python3
"""Validate a durable project lesson and reject sensitive or local data."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

REQUIRED = {"schema", "id", "title", "status", "source", "scope", "observed_at", "rule", "evidence", "privacy_reviewed", "reviewed_by", "expires_at"}
# Values, not words: a lesson may say "never commit tokens" but must not contain one.
SENSITIVE = re.compile(
    r"(?i)(?:(?:api[_-]?key|token|password|passwd|secret)\s*[:=]\s*\S{6,}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|serial(?:\s|_)?number\s*[:=]\s*\S+"
    r"|/home/(?!user\b)[a-z]|/Users/(?!user\b)[A-Za-z]|[A-Za-z]:\\Users\\)"
)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lesson", type=Path)
    args = parser.parse_args()
    try:
        import yaml
        data = yaml.safe_load(args.lesson.read_text(encoding="utf-8"))
        if not isinstance(data, dict): raise ValueError("lesson root must be a mapping")
        errors = [f"missing field: {k}" for k in sorted(REQUIRED - data.keys())]
        if data.get("schema") != 1: errors.append("schema must be integer 1")
        if not re.fullmatch(r"LESSON-[0-9]{4}-[0-9]{4}", str(data.get("id", ""))): errors.append("id must match LESSON-YYYY-NNNN")
        if data.get("status") not in {"proposed", "accepted", "deprecated"}: errors.append("status is invalid")
        if data.get("source") not in {"user-rule", "agent-observation", "review-finding"}: errors.append("source is invalid")
        if not isinstance(data.get("evidence"), list): errors.append("evidence must be a list")
        if not isinstance(data.get("privacy_reviewed"), bool): errors.append("privacy_reviewed must be boolean")
        observed = str(data.get("observed_at", ""))
        if observed != "YYYY-MM-DD" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", observed): errors.append("observed_at must be YYYY-MM-DD")
        if SENSITIVE.search(args.lesson.read_text(encoding="utf-8")): errors.append("possible sensitive or local identifier detected")
    except Exception as error:
        print(json.dumps({"status": "invalid", "errors": [str(error)]}, indent=2)); return 1
    print(json.dumps({"status": "invalid" if errors else "valid", "errors": errors}, indent=2)); return int(bool(errors))

if __name__ == "__main__": raise SystemExit(main())
