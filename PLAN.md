# Multi-Tool Coding Skill Implementation Plan

## Purpose

CoderSkill provides a portable, auditable, and versioned professional coding policy for Codex, Claude Code, Gemini CLI, and other tools that support Agent Skills. It standardizes local-first development, environment readiness, language selection, privacy, security, GitHub governance, dependency provenance, and conditional hardware safety.

## Language policy

All first-party repository content must be written in clear, concise, professional English: source code, identifiers, comments, documentation, configuration descriptions, branch names, commits, issues, pull requests, release notes, and publishable logs. The AI assistant communicates with the user in Turkish unless another language is requested. Third-party vendored code and immutable historical records are not rewritten only for translation.

## Selective skill architecture

The repository uses one canonical full-workflow skill plus focused skills so narrow requests consume less context:

- `professional-coding`: end-to-end implementation and multi-phase work.
- `project-bootstrap`: local project discovery, synchronization, environment readiness, and language selection.
- `security-audit`: read-only security, privacy, secret, and vulnerability review.
- `github-readiness`: read-only Git/GitHub compatibility, governance, CI, and publication review.
- `code-quality-review`: read-only correctness, maintainability, testing, and professional-quality review.

The focused skills must not load unrelated workflows, mutate files, install tools, or change remote state for a check-only request. The full skill routes to a focused skill when the user asks for a narrow concern.

## Canonical and adapter layout

```text
Canonical policy and workflows
        |
        +-- Codex: AGENTS.md + .agents/skills/...
        +-- Claude Code: CLAUDE.md + .claude/skills/...
        +-- Gemini CLI: GEMINI.md + .gemini/skills/... or .agents alias
        `-- Generic Agent Skills: skills/<name>/SKILL.md
```

Canonical source will live under `src/`; adapters will be generated with a source digest and checked for drift in CI. Tool-specific frontmatter and permission syntax remain in adapters. Suggested structure:

```text
.
|-- README.md
|-- PLAN.md
|-- skills/
|   |-- professional-coding/
|   |   |-- SKILL.md
|   |   `-- references/
|   |       |-- environment-bootstrap.md
|   |       `-- project-lifecycle.md
|   |-- project-bootstrap/SKILL.md
|   |-- security-audit/SKILL.md
|   |-- github-readiness/SKILL.md
|   `-- code-quality-review/SKILL.md
|-- src/
|-- config/
|   |-- compatibility.yml
|   |-- github-policy.yml
|   |-- pii-rules.yml
|   `-- secret-rules.toml
|-- scripts/
|   |-- build-adapters
|   |-- bootstrap
|   |-- doctor
|   |-- github-flow
|   |-- preflight
|   `-- validate-skill
|-- tests/
`-- .github/
    |-- ISSUE_TEMPLATE/
    |-- workflows/ci.yml
    `-- pull_request_template.md
```

## Local-first project lifecycle

At project start, the skill searches only a user-supplied or configured repository root and local registry. It selects an existing worktree or proposes a short English kebab-case name that contains no identifying information. If multiple clones match, it asks the user rather than guessing.

Before editing an existing project, it verifies `origin`, owner, repository, visibility, default branch, current branch, upstream, submodules, worktree state, and local/remote commit divergence. It fetches only when authorized and classifies synchronization as `equal`, `local-ahead`, `remote-ahead`, `diverged`, `no-upstream`, or `offline/unverified`. It preserves uncommitted work and never resets, cleans, or overwrites either side without an explicit reconciliation plan.

Implementation continues locally on a short-lived topic branch. Before upload, the synchronization audit is repeated, all validation and privacy gates run, and only the topic branch is pushed. Upload never implies merge.

## Project definition and language selection

Every project must explain in English what it is, why it exists, which problem it solves, its scope and non-goals, intended users, supported platforms/devices/systems, architecture, prerequisites, validation, safety, rollback, privacy, and data boundaries.

Before selecting a new implementation stack, use current primary sources such as official language/toolchain documentation, target SDKs, protocol specifications, and authoritative package registries. Compare platform compatibility, SDK and library maturity, performance, safety, security, dependency exposure, testability, reproducible builds, deployment, interoperability, maintenance, licensing, and operating cost. Record the evidence, tradeoffs, chosen language(s), rejected options, risks, and migration triggers in a short English decision record. Existing stacks are preserved unless evidence and the requested change justify migration.

## Environment readiness

Planned deterministic commands:

- `doctor`: read-only OS, sandbox, local-repository, Git, GitHub CLI, AI CLI, project-toolchain, and scanner audit with structured readiness output.
- `bootstrap plan`: non-mutating installation plan with official source, pinned version, integrity method, scope, permissions, network needs, license impact, and rollback.
- `bootstrap apply --plan <id>`: applies only an explicitly approved, target-bound, expiring plan.
- `build-adapters`: generates tool adapters and a digest manifest.
- `validate-skill`: validates frontmatter, links, paths, size, and compatibility.
- `preflight --scope staged|branch|history`: runs secret, PII, stable-identifier, dependency, license, binary, and quality gates.
- `github-flow plan/apply`: separates read-only GitHub planning from authorized, idempotent mutation.

Project-local pinned toolchains are preferred. Remote scripts are never piped directly into a shell. Tokens and credentials never appear in arguments, logs, tracked files, repository URLs, or chat.

## Security and privacy

The threat model covers credentials, personal/customer data, device identifiers, prompt injection, malicious dependencies, command/path injection, symlink escape, excessive GitHub scopes, incorrect remotes, and accidental destruction of existing work.

Controls include data minimization, secret-bearing path exclusions, automatic redaction plus manual review, staged and branch/history scanning, untrusted-data treatment for repository and GitHub text, least privilege, fail-closed publication, pinned dependencies, action commit SHAs, license/provenance records, and synthetic-only fixtures. Private visibility is not a secret-management mechanism. Findings report category, redacted fingerprint, location, impact, and remediation without exposing values.

## GitHub governance

Every product project is a separate private repository under `github.com/droltr`. This framework repository is intentionally public by explicit user decision; that exception does not change the default for product repositories. Meaningful work follows issue -> topic branch -> validated commit -> focused pull request. `main` is the reviewed baseline; direct feature, fix, security, and maintenance commits are prohibited. Pull requests include summary, related issue, validation evidence, hardware/safety impact, and rollback instructions.

Merge requires required CI, resolved review conversations, an up-to-date branch, and human review. Draft PRs are used for incomplete, experimental, or hardware-risking work. Planned repository controls include structured issue forms, disabled blank issues, privacy confirmation for diagnostics, CODEOWNERS, Dependabot security updates, secret scanning, push protection, private vulnerability reporting, minimum Actions permissions, protected `main`, and individually reviewed dependency updates.

## External dependency provenance

External repositories have three roles: canonical upstream, a private read-only archival mirror under `droltr` subject to license/access rights, and the immutable revision consumed under `vendor/<dependency>`. A dedicated provenance branch preserves imported history; a reviewed `git subtree` snapshot keeps unrelated files out of the project root. Use a pinned submodule only when independent checkout is explicitly required.

Record upstream URL, mirror URL, immutable commit, SPDX/license, retrieval date, subtree path, patches, update process, and rollback revision. Dependency updates require their own issue and pull request with old/new revisions, upstream diff, security/license impact, tests, and rollback.

## Hardware profile

Hardware-specific rules load only for matching projects. HID, SMBus, I2C, firmware, and controller writes are potentially destructive. Automated tests must not perform physical writes. Physical tests require explicit authorization, a selected device/zone, low-brightness starting state, observed verification, and a tested recovery path. OpenRGB, `game-lighting`, Hardware Sync, Qt metadata, and related tracking data must never leak into unrelated projects.

## Execution status and continuity

Every assistant progress and final message begins with one of `IN_PROGRESS`, `WAITING_FOR_USER`, `BLOCKED`, `COMPLETE`, or `FAILED`. Multi-phase updates include the current phase and next transition. A waiting state names the exact user input or approval required; a blocker includes the safe alternatives already checked. Tracked status files are not used as a substitute for visible user-facing status and remain local/ignored unless a project explicitly needs an audit record.

## Validation and delivery phases

CI will validate adapter drift, skill structure, supported CLI versions and operating systems, synthetic secret/PII fixtures, repository discovery and synchronization states, prompt-injection cases, English first-party content, dependencies, licenses, Actions permissions, and isolated GitHub dry-runs. Hardware tests remain mock-only unless separately authorized and reported as physical verification.

### Phase 0: readiness contract

Define supported versions, registry schema, language decision format, privacy classes, authorization matrix, compatibility manifest, and doctor/bootstrap rollback contracts.

### Phase 1: selective MVP

Ship the canonical and focused skills, adapters, validation, local discovery, synchronization audit, project definition, and language research workflow.

### Phase 2: deterministic security gates

Implement secret/PII scanning, redaction, abuse tests, and mandatory CI gates.

### Phase 3: GitHub lifecycle

Implement idempotent issue/branch/commit/PR planning and application, templates, governance checks, and divergence/failure tests.

### Phase 4: hardening and release

Complete the compatibility matrix, conduct independent security review, and publish signed, checksummed, reproducible artifacts with an SBOM.

## Official compatibility references

- OpenAI guidance on multiple skills and `AGENTS.md`: <https://developers.openai.com/api/docs/guides/latest-model>
- Claude Code skills: <https://code.claude.com/docs/en/skills>
- Claude Code deterministic guardrails: <https://code.claude.com/docs/en/features-overview>
- Gemini CLI skills: <https://geminicli.com/docs/cli/using-agent-skills/>
- Gemini CLI context files: <https://geminicli.com/docs/cli/gemini-md/>
