# CoderSkill

CoderSkill is a cross-tool professional development skill for Codex, Claude Code, Gemini CLI, and other tools that support the Agent Skills format.

## Purpose

AI coding tools use different instruction files, discovery paths, permission systems, and automation mechanisms. CoderSkill provides one maintainable policy source for consistent local-first development across those tools.

It is designed to solve four recurring problems:

- Inconsistent engineering behavior between AI coding tools.
- Unsafe handling of credentials, personal data, diagnostics, and device identifiers.
- Untracked or poorly reviewed Git and GitHub changes.
- Environment, dependency, synchronization, and validation steps that are easy to skip.

## Scope

The current repository contains the initial implementation plan and a canonical `professional-coding` skill. The skill covers:

- Environment readiness and safe software-installation planning.
- Local repository discovery and GitHub synchronization audits.
- Evidence-based programming-language and toolchain selection.
- English-only repository artifacts and selectable user communication language (English by default; system language suggested).
- Issue, branch, commit, and pull-request governance.
- Secret, personal-data, and stable-identifier protection.
- External dependency provenance and private archival mirrors.
- Conditional hardware-safety controls for device-specific projects.

## Current status

The initial implementation is available on `main`. It includes the read-only environment doctor, adapter generation and drift checks, passive security audit, project-profile and lesson validation, governance templates, least-privilege CI, and deterministic tests. Full GitHub lifecycle mutation remains deliberately review-gated; prompt instructions alone are never a security boundary.

See [PLAN.md](PLAN.md) for the architecture, delivery phases, and validation strategy. The canonical skill is [skills/professional-coding/SKILL.md](skills/professional-coding/SKILL.md).
See [RELEASE_NOTES.md](RELEASE_NOTES.md) for versioned changes and durable workflow/security decisions.

## Execution status

The assistant uses a visible status marker at the start of every progress or final message:

```text
[STATUS: IN_PROGRESS]
[STATUS: WAITING_FOR_USER]
[STATUS: BLOCKED]
[STATUS: COMPLETE]
[STATUS: FAILED]
```

`IN_PROGRESS` means work is continuing. `WAITING_FOR_USER` names the exact answer or approval required. `BLOCKED` is reserved for a verified blocker after safe alternatives were checked. `COMPLETE` is used only after the requested scope and validation are finished.

For an authorized in-scope workflow, the assistant continues through routine implementation phases without pausing for unnecessary confirmation. It pauses only for material scope changes, destructive or irreversible actions, credentials, physical hardware writes, security-sensitive external mutations, or decisions that cannot be inferred safely.

## Usage

## Installation

Clone CoderSkill once outside product repositories and install its adapters for the terminal tools you use:

```bash
git clone https://github.com/droltr/CoderSkill.git
cd CoderSkill
scripts/coderskill install
```

The installer writes only to the user skill directories and user command directory. It does not copy CoderSkill into a target project and does not overwrite existing skills unless `--update` is supplied:

```bash
scripts/coderskill install --update
```

## Start or resume a project

Inside a project directory, tell the active AI coding tool:

```text
execute order 66
```

`projeye başla` remains an equivalent Turkish trigger. The phrase is only a mnemonic for the safe workflow and never authorizes destructive actions, credential use, security bypasses, or hardware writes.

The `professional-coding` skill then classifies the directory, reads its scope and local rules, selects only applicable focused skills, validates the environment and synchronization, and continues through issue, branch, implementation, tests, security checks, and pull-request preparation. It pauses only for a missing material decision, credentials, physical hardware writes, or irreversible security remediation.

For a read-only terminal preview of this start process:

```bash
scripts/coderskill-start
```

To run a selected terminal agent from any project directory:

```bash
coderskill start execute order 66 --agent codex --run
```

You may provide the real GitHub target explicitly:

```bash
coderskill start execute order 66 \\
  --agent codex \\
  --github https://github.com/droltr/your-real-repository \\
  --confirm-account \\
  --run
```

If `--github` is omitted, the local `origin` URL is used. Placeholder targets such as `droltr/your-project` are rejected. Before `--run`, CoderSkill displays the active GitHub account and target repository; review them and pass `--confirm-account` only when they are correct. A mismatch stops the operation.

For an empty directory, enter it and run the same command. The agent first learns the purpose, scope, platform, constraints, and communication-language preference before creating project files. It then creates or references an issue, selects only applicable skills, and continues on a topic branch. CoderSkill remains outside the project directory.

The focused skills are designed to be invoked by name after they have been installed or linked into the active tool's documented skill directory. Use the smallest skill that matches the request:

```text
Security and privacy:       security-audit
GitHub compatibility:       github-readiness
Code quality:               code-quality-review
Project startup/readiness:  project-bootstrap
End-to-end implementation:  professional-coding
```

Example requests:

```text
Use security-audit to inspect this repository for secrets, personal-data leaks, and exploitable vulnerabilities. Do not modify files.

Use github-readiness to check whether this repository is ready for a droltr GitHub pull request. Do not push or change remote settings.

Use code-quality-review to assess this diff for correctness, maintainability, tests, and professional English. Do not implement fixes.

Use project-bootstrap to locate the local project, check synchronization, audit required tools, and recommend an implementation language.

Use professional-coding to implement issue #123 locally, validate the changes, and prepare a draft pull request when explicitly authorized.
```

Tool invocation examples:

- Claude Code: invoke a user-facing skill with `/security-audit`, `/github-readiness`, `/code-quality-review`, `/project-bootstrap`, or `/professional-coding` after installing the corresponding folders under `.claude/skills/<name>/`.
- Gemini CLI: install or link the skill using the CLI's Agent Skills workflow, then invoke the matching skill name. Workspace installation uses `.gemini/skills/<name>/` or the supported `.agents/skills/<name>/` alias.
- Codex and other Agent Skills tools: install or link the matching `skills/<name>/` directory using that tool's documented skill directory, then invoke the skill by its name (for example, `security-audit`).

For a check-only request, explicitly say “do not modify files, commit, push, or change remote state.” Focused skills are read-only by design. The `professional-coding` skill is intended only when implementation or a multi-phase workflow is requested.

## Current command availability

The following deterministic commands are available:

```bash
scripts/doctor
scripts/bootstrap plan
scripts/build-adapters --check
scripts/github-flow plan --issue 123 --kind feature
scripts/security-audit --format json --root .
scripts/preflight --scope branch
scripts/validate-project-profile .coderskill/project.yml.example
scripts/validate-lesson knowledge/lesson.example.yml
```

Mutation subcommands for `bootstrap` and `github-flow` remain intentionally unavailable until an explicit reviewed operation is authorized. The test suite can be run with:

```bash
python3 -m unittest discover -s tests -v
```

## Privacy

This repository must not contain credentials, real usernames, machine-specific paths, hostnames, network addresses, device serials, customer data, or unredacted diagnostics. Use neutral placeholders and synthetic test data.
