# github-readiness

Source: [`skills/github-readiness/SKILL.md`](../../skills/github-readiness/SKILL.md)

## Purpose

A focused, read-only review of whether a repository is ready for GitHub: repository state,
synchronization, branch policy, issues, commits, pull requests, CI, governance and publication
hygiene.

## When it is used

"Is this project GitHub-ready?" or "GitHub-compatible?". It does not implement changes or perform a
full security audit.

## How it works

The project profile selects which GitHub capabilities matter (see
[`github-capabilities.md`](../../skills/professional-coding/references/github-capabilities.md)).
Actions and Security are publication gates when configured; Projects and Insights are optional.
The review then checks:

- the path is a Git worktree, and user changes are preserved;
- branch, upstream, remote URLs, ahead/behind state, untracked files, submodules and published
  history, without exposing embedded credentials or personal paths;
- `origin` points at the intended `droltr/<repository>` with the visibility recorded in the project
  profile, and `main` is the reviewed baseline;
- topic-branch names, issue links, focused commits, pull-request base, draft use, linear history;
- purpose and scope documentation, English-only content, license, `.gitignore`, templates,
  CODEOWNERS, dependency updates, branch protection, least-privilege Actions, secret scanning, push
  protection, private vulnerability reporting;
- CI results and required checks; skipped or missing CI is not success;
- the secret and identifier preflight before publication.

`scripts/github-settings-check` and `scripts/preflight` automate parts of it; see
[commands](../commands.md).

## Rules and why they exist

- **Read-only by default.** Checking readiness does not authorize fetch, pull, commit, push, issue or
  pull-request creation, merge, repository creation, visibility or settings changes. *Why:* a review
  must not change what it reviews.
- **No credentials or personal paths in output.**
- **A full vulnerability review goes to `security-audit`.** *Why:* each skill stays focused.

## Relationships

- Hands security reviews to [security-audit](security-audit.md).
- Fixes are made under [professional-coding](professional-coding.md).
- Claims follow [verified-agent-rules](verified-agent-rules.md).

## Outputs

`ready`, `ready-with-warnings` or `not-ready`, with blocking findings, warnings, evidence,
unavailable remote checks and the smallest next actions.
