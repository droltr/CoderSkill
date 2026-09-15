---
name: project-bootstrap
description: Prepare or resume a local-first software project by locating its workspace, auditing GitHub synchronization, checking required tools, researching suitable implementation languages, and documenting purpose and constraints. Use for project startup or environment readiness; do not implement features or publish remotely unless separately requested.
---

# Project Bootstrap

Perform read-only discovery first. Communicate with the user in the project-selected language, defaulting to English and suggesting the system language when no choice is recorded. Write every repository artifact in clear professional English.

Use the detailed workflows in the `professional-coding` package when available:

- Environment and tool readiness: `../professional-coding/references/environment-bootstrap.md`
- Project discovery, synchronization, language research, local work, and publication: `../professional-coding/references/project-lifecycle.md`

If those references are unavailable in an installed standalone package, apply these minimum invariants:

- Search only user-supplied or configured repository roots; never broadly crawl personal storage.
- Resolve ambiguity between multiple local clones with the user.
- Preserve uncommitted and untracked work.
- Verify local/remote identity and classify synchronization before editing.
- Check only tools required by the detected project; do not install all supported AI CLIs.
- Research language choices from current primary sources and record evidence and tradeoffs in English.
- Explain purpose, problem, scope, non-goals, platform/device specificity, validation, privacy, safety, and rollback.
- Do not install, authenticate, create directories outside scope, clone, create a repository, or publish without explicit authorization.
- Never publish credentials, personal paths, usernames, hostnames, network addresses, serials, UUIDs, or other stable identifiers.

Return a concise readiness result with the selected project, redacted location, synchronization state, required tools, language decision status, blockers, and proposed next actions.
