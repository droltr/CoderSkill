#!/usr/bin/env python3
"""Verify GitHub security and main-branch policy without mutating remote state."""
import json, subprocess

def api(path):
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=False)
    if result.returncode: raise RuntimeError(result.stderr.strip() or "GitHub CLI request failed")
    return json.loads(result.stdout)

def main():
    repo = "repos/droltr/CoderSkill"
    metadata = api(repo); protection = api(repo + "/branches/main/protection")
    security = metadata.get("security_and_analysis", {})
    checks = {
        "public_framework_repository": str(metadata.get("visibility", "")).lower() == "public",
        "default_branch_main": metadata.get("default_branch") == "main",
        "secret_scanning": security.get("secret_scanning", {}).get("status") == "enabled",
        "push_protection": security.get("secret_scanning_push_protection", {}).get("status") == "enabled",
        "dependabot_security_updates": security.get("dependabot_security_updates", {}).get("status") == "enabled",
        "main_protected": bool(protection),
        "required_ci_checks": bool(protection.get("required_status_checks", {}).get("contexts")),
        "force_push_disabled": not protection.get("allow_force_pushes", {}).get("enabled", True),
        "branch_deletion_disabled": not protection.get("allow_deletions", {}).get("enabled", True),
    }
    print(json.dumps({"schema": 1, "read_only": True, "status": "pass" if all(checks.values()) else "fail", "checks": checks}, indent=2))
    return 0 if all(checks.values()) else 1

if __name__ == "__main__": raise SystemExit(main())
