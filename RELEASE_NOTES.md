# Release Notes

This file records user-visible changes and durable workflow or security decisions. Entries are written in English and must not contain credentials, personal data, local paths, or unique device identifiers.

## Unreleased

### Documentation

- New README and a `docs/` site: overview and architecture, installation and updates, workflow and
  records, hooks, security model, commands, troubleshooting, and one page per skill with its purpose,
  rules and their reasons, working logic and relationships.
- PLAN.md (out-of-date plan) and SESSION_RECORD.md (session record) removed; their valid content is in
  `docs/`.
- `github-readiness` checks the visibility recorded in the project profile instead of assuming a
  private repository.

### Signed skill updates

- `coderskill install` installs only the signed `origin/main` of the CoderSkill clone (GitHub web-flow key pinned, or the owner's SSH signers); every new commit must be signed. `--worktree` keeps the old behaviour for the owner.
- Installed skills are read-only, swapped in one step under a lock, and backed up outside the skill folders; skills removed from CoderSkill are uninstalled unless changed locally.
- Session start and prompt hooks report waiting and installed updates; the global `post-merge` hook refreshes the state in the CoderSkill clone.
- Agents cannot edit installed CoderSkill files; `coderskill request` records a change request in the clone's local `.private/change-requests/`.

### Agent hooks, records and policy cleanup

- Load the CoderSkill rules at every session and subagent start (Claude Code, Codex, Gemini CLI) and enforce mandatory rules through agent hooks and global git `pre-commit` and `pre-push` hooks.
- Keep requests, research, plans and session records in the local `.private/` folder; copy agent transcripts to the git-ignored `.agent-sessions/`.
- Require signed commits with one signing key per machine.
- Replace scattered pause conditions with one closed list of stop reasons; status markers only on the message that ends a turn.
- Confirm GitHub identity and target once per repository and record it locally.
- Talk to the user in the operating system's language, read from the locale at session start; repository content stays English. The profile fields `user_communication_language` and `system_language_suggestion` are no longer required and are ignored.
- Add the `systematic-debugging` skill, a completion gate, coding discipline rules and a requirement clarification step.
- Move OpenRGB and Mystic Light rules out of the generic skill into a conditional reference.

### v0.2 hardening

- Add scope-aware staged, branch, and history preflight checks.
- Add dependency component metadata and deterministic checksum verification for release manifests.
- Add `github-flow` and `bootstrap` planning commands; their `apply` modes only check authorization and do not mutate anything.
- Record the independent security review and its residual defense-in-depth risks.

### Security and identity

- Require an explicit confirmation of the active GitHub account and target repository before an AI agent starts implementation or performs remote mutation.
- Re-check the account session and `origin` before pushing or opening a pull request; stop and inform the user when either changes.
- Reject placeholder repository targets such as `droltr/your-project` and prefer the detected local remote when no valid target is supplied.

### Workflow

- Use `execute order 66` or `projeye başla` as the safe project-start trigger.
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
