# Release Notes

This file records user-visible changes and durable workflow or security decisions. Entries are written in English and must not contain credentials, personal data, local paths, or unique device identifiers.

## Unreleased

### Security and identity

- Require an explicit confirmation of the active GitHub account and target repository before an AI agent starts implementation or performs remote mutation.
- Re-check the account session and `origin` before pushing or opening a pull request; stop and inform the user when either changes.
- Reject placeholder repository targets such as `droltr/your-project` and prefer the detected local remote when no valid target is supplied.

### Workflow

- Support `execute order 66` and `projeye başla` as equivalent safe project-start triggers.
- Keep CoderSkill outside target projects when using the system-wide `coderskill` command.
- Select only focused skills enabled by the project profile.

## v0.1.0 — Foundation

### Added

- Canonical professional-coding skill with Codex, Claude Code, Gemini CLI, and generic adapters.
- Focused project-bootstrap, security-audit, github-readiness, and code-quality-review skills.
- Environment doctor, read-only preflight, bootstrap planning, GitHub flow planning, and settings drift checks.
- Secret/PII audit, standards registry, project profiles, controlled lesson records, and deterministic release manifest/SPDX inventory.
- GitHub issue forms, milestones, CODEOWNERS, Dependabot, branch protection, required CI, and CodeQL scanning.
- LICENSE, SECURITY, CONTRIBUTING, and SESSION_RECORD documentation.

### Safety baseline

- Preserve verified `main` behavior through issue-linked topic branches and pull requests.
- Never expose credentials, personal data, local machine identifiers, or unredacted diagnostics.
- Automated tests do not perform physical hardware writes.

## Release process

Before a release, run the applicable preflight and security checks, generate a deterministic release manifest, review the diff and release notes, and record the validated commit. Publishing, signing, and uploading release artifacts remain explicit operations.
