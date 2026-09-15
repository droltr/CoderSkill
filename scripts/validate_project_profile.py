#!/usr/bin/env python3
"""Validate a project profile without revealing local or sensitive values."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED = {"schema", "project_id", "repository", "default_branch", "artifact_language", "user_communication_language", "active_profiles"}
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


def load(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError as error:
        raise RuntimeError("PyYAML is required to validate project profiles") from error
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("profile root must be a mapping")
    return data


def validate(data: dict) -> list[str]:
    errors = [f"missing field: {key}" for key in sorted(REQUIRED - data.keys())]
    if data.get("schema") != 1:
        errors.append("schema must be integer 1")
    if not IDENTIFIER.fullmatch(str(data.get("project_id", ""))):
        errors.append("project_id must be lowercase kebab-case")
    if not re.fullmatch(r"droltr/[A-Za-z0-9_.-]+", str(data.get("repository", ""))):
        errors.append("repository must identify a droltr repository without credentials")
    if data.get("default_branch") != "main":
        errors.append("default_branch must be main")
    if data.get("artifact_language") != "english":
        errors.append("artifact_language must be english")
    if data.get("user_communication_language") != "turkish":
        errors.append("user_communication_language must be turkish")
    if not isinstance(data.get("active_profiles"), list) or not all(isinstance(item, str) for item in data.get("active_profiles", [])):
        errors.append("active_profiles must be a list of strings")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    try:
        errors = validate(load(args.profile))
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"status": "invalid", "errors": [str(error)]}, indent=2))
        return 1
    result = {"status": "invalid" if errors else "valid", "errors": errors}
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
