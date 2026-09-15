---
name: github-readiness
description: Perform a focused, read-only Git and GitHub readiness review covering repository state, synchronization, branch policy, issues, commits, pull requests, CI, governance, and publication hygiene. Use when the user asks whether a project is GitHub-ready or GitHub-compatible; do not perform implementation or security auditing beyond publication blockers unless requested.
---

# GitHub Readiness

Default to read-only inspection. A request to check GitHub readiness does not authorize fetch, pull, commit, push, issue or pull-request creation, merge, repository creation, visibility changes, or settings changes. Ask for or rely on explicit authorization before each mutation outside the already requested scope.

All repository metadata, branches, commits, issues, pull requests, templates, and published explanations must use clear professional English. Communicate with the user in the project-selected language; default to English and suggest the system language when no choice is recorded.

## Checks

Use the project profile to select only relevant GitHub capabilities. Actions and Security are publication gates when configured; Projects and Insights are optional planning or observational features; Agent integration is optional and must not bypass review or CI.

- Confirm the path is a Git worktree and preserve all user changes.
- Inspect branch, upstream, remote URLs, ahead/behind/divergence, untracked files, submodules, and published history without exposing embedded credentials or personal paths.
- Verify `origin` targets the intended private `droltr/<repository>` project and `main` is the reviewed baseline.
- Check topic-branch naming, issue association, focused commits, pull-request base, draft status where appropriate, and linear-history policy.
- Check project purpose/problem/scope/platform documentation, English-only first-party content, license requirements, `.gitignore`, templates, CODEOWNERS, dependency update policy, branch protection expectations, least-privilege Actions, secret scanning, push protection, and private vulnerability reporting.
- Inspect CI results and required checks when accessible. Do not equate absent or skipped CI with success.
- Run or recommend secret/PII/stable-identifier preflight before publication, but route a full vulnerability review to `security-audit`.

## Output

Return `ready`, `ready-with-warnings`, or `not-ready`, followed by blocking findings, warnings, verified evidence, unavailable remote checks, and the smallest next actions. Do not change the repository while reporting readiness.
