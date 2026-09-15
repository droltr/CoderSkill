#!/usr/bin/env python3
"""Plan, but never apply, the issue-to-pull-request workflow."""
import argparse, json, os, subprocess

def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("command", choices=("plan", "apply")); p.add_argument("--issue", required=True, type=int); p.add_argument("--kind", choices=("feature", "fix", "security", "docs", "test", "chore"), default="feature"); args = p.parse_args()
    branch = f"{args.kind}/issue-{args.issue}"
    result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, check=False)
    if args.command == "plan":
        print(json.dumps({"schema": 1, "read_only": True, "issue": args.issue, "current_branch": result.stdout.strip(), "planned_branch": branch, "steps": ["verify main is synchronized", "create topic branch", "implement and validate", "commit with issue reference", "push topic branch", "open focused pull request", "wait for required checks", "review and merge"], "mutations": "not performed"}, indent=2)); return
    if os.environ.get("CODERSKILL_CONFIRM_ACCOUNT") != "droltr" or os.environ.get("CODERSKILL_CONFIRM_REPOSITORY") != "droltr/CoderSkill":
        print(json.dumps({"schema": 1, "read_only": False, "status": "blocked", "reason": "explicit identity and repository confirmation required"}, indent=2)); return 2
    print(json.dumps({"schema": 1, "read_only": False, "status": "authorized", "mutations": "available only to the caller", "issue": args.issue, "planned_branch": branch}, indent=2))

if __name__ == "__main__": main()
