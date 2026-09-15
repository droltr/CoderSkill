#!/usr/bin/env python3
"""Generate Agent Skills discovery directories from the canonical skills tree.

The generator is intentionally dependency-free and only writes paths beneath
the repository root. Use --check in CI to detect drift without changing files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


TARGETS = (".agents/skills", ".claude/skills", ".gemini/skills")


def digest_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if item.is_file():
            digest.update(item.relative_to(path).as_posix().encode())
            digest.update(b"\0")
            digest.update(item.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def canonical_skills(root: Path) -> list[Path]:
    skills_root = root / "skills"
    if not skills_root.is_dir():
        raise ValueError(f"canonical skills directory is missing: {skills_root}")
    skills = sorted(path for path in skills_root.iterdir() if (path / "SKILL.md").is_file())
    if not skills:
        raise ValueError(f"no canonical skills found in {skills_root}")
    return skills


def expected_files(root: Path, skills: list[Path]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for target in TARGETS:
        for skill in skills:
            for source in skill.rglob("*"):
                if source.is_file():
                    relative = Path(target) / skill.name / source.relative_to(skill)
                    files[relative.as_posix()] = source.read_bytes()
    return files


def check(root: Path, files: dict[str, bytes]) -> list[str]:
    mismatches: list[str] = []
    for relative, content in files.items():
        destination = root / relative
        if not destination.is_file() or destination.read_bytes() != content:
            mismatches.append(relative)
    return mismatches


def write(root: Path, files: dict[str, bytes]) -> None:
    for relative, content in files.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

    manifest = {
        "schema": 1,
        "source": "skills/",
        "targets": list(TARGETS),
        "skills": {
            skill.name: digest_tree(skill)
            for skill in canonical_skills(root)
        },
    }
    manifest_path = root / "adapters" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args()

    root = args.root.resolve()
    try:
        skills = canonical_skills(root)
        files = expected_files(root, skills)
        mismatches = check(root, files)
        if args.check:
            if mismatches:
                print("adapter drift detected:")
                print("\n".join(f"- {item}" for item in mismatches))
                return 1
            print(f"adapters are in sync ({len(skills)} skills, {len(files)} files)")
            return 0
        write(root, files)
        print(f"generated adapters ({len(skills)} skills, {len(files)} files)")
        return 0
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
