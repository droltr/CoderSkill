#!/usr/bin/env python3
"""Verify release metadata and checksums without publishing anything."""
import argparse, hashlib, json
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    args = p.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    failures = []
    for entry in data.get("files", []):
        path = Path(entry["fileName"])
        if not path.is_file():
            failures.append({"file": str(path), "reason": "missing"}); continue
        expected = entry.get("checksums", [{}])[0].get("checksumValue")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected != actual: failures.append({"file": str(path), "reason": "checksum-mismatch"})
    print(json.dumps({"schema": 1, "read_only": True, "status": "pass" if not failures else "fail", "failures": failures}, indent=2))
    return 0 if not failures else 1

if __name__ == "__main__": raise SystemExit(main())
