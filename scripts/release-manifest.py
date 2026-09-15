#!/usr/bin/env python3
"""Emit deterministic release metadata and an SPDX 2.3 file inventory."""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--output", type=Path); args = p.parse_args()
    root = Path.cwd(); revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    paths = subprocess.check_output(["git", "ls-files", "-z"], text=False).split(b"\0")
    files = []
    for raw in paths:
        if not raw: continue
        rel = raw.decode("utf-8"); path = root / rel
        if not path.is_file(): continue
        files.append({"SPDXID": "SPDXRef-File-" + hashlib.sha256(raw).hexdigest()[:16], "fileName": rel, "checksums": [{"algorithm": "SHA256", "checksumValue": hashlib.sha256(path.read_bytes()).hexdigest()}]})
    components = []
    manifest = root / "config" / "dependencies.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        components = data.get("components", [])
    doc = {"spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0", "SPDXID": "SPDXRef-DOCUMENT", "name": "CoderSkill-release", "documentNamespace": "https://github.com/droltr/CoderSkill/releases/" + revision, "creationInfo": {"creators": ["Tool: CoderSkill release-manifest"], "created": "1970-01-01T00:00:00Z"}, "files": files, "packages": components, "release": {"gitRevision": revision}}
    output = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if args.output: args.output.write_text(output, encoding="utf-8")
    else: print(output, end="")
    return 0

if __name__ == "__main__": raise SystemExit(main())
