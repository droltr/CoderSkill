#!/usr/bin/env python3
"""Verify GitHub security and default-branch policy without mutating remote state."""
import argparse, json, re, subprocess


def api(path):
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=False)
    if result.returncode:
        return None, (result.stderr.strip() or "GitHub CLI request failed")
    return json.loads(result.stdout), None


def origin_repository():
    origin = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=False).stdout.strip()
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?/?$", origin)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="owner/name; defaults to the origin remote")
    parser.add_argument("--expect-visibility", choices=("public", "private"), help="fail when the visibility differs")
    args = parser.parse_args()
    repo = args.repo or origin_repository()
    if not repo:
        print(json.dumps({"schema": 1, "read_only": True, "status": "error", "reason": "no GitHub origin; pass --repo"}, indent=2))
        return 2
    metadata, error = api(f"repos/{repo}")
    if metadata is None:
        print(json.dumps({"schema": 1, "read_only": True, "status": "error", "reason": error}, indent=2))
        return 2
    branch = metadata.get("default_branch", "main")
    protection, _ = api(f"repos/{repo}/branches/{branch}/protection")
    protection = protection or {}
    security = metadata.get("security_and_analysis") or {}
    checks = {
        "default_branch_main": branch == "main",
        "secret_scanning": security.get("secret_scanning", {}).get("status") == "enabled",
        "push_protection": security.get("secret_scanning_push_protection", {}).get("status") == "enabled",
        "dependabot_security_updates": security.get("dependabot_security_updates", {}).get("status") == "enabled",
        "main_protected": bool(protection),
        "required_ci_checks": bool((protection.get("required_status_checks") or {}).get("contexts")),
        "force_push_disabled": bool(protection) and not protection.get("allow_force_pushes", {}).get("enabled", True),
        "branch_deletion_disabled": bool(protection) and not protection.get("allow_deletions", {}).get("enabled", True),
    }
    if args.expect_visibility:
        checks["visibility_" + args.expect_visibility] = str(metadata.get("visibility", "")).lower() == args.expect_visibility
    status = "pass" if all(checks.values()) else "fail"
    print(json.dumps({"schema": 1, "read_only": True, "repository": repo, "status": status, "checks": checks}, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
