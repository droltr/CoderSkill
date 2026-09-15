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
- English-only repository artifacts and Turkish user communication.
- Issue, branch, commit, and pull-request governance.
- Secret, personal-data, and stable-identifier protection.
- External dependency provenance and private archival mirrors.
- Conditional hardware-safety controls for device-specific projects.

## Current status

This is an early planning and policy baseline. Deterministic `doctor`, `bootstrap`, `preflight`, adapter-generation, and GitHub lifecycle scripts are planned but not yet implemented. Do not treat prompt instructions alone as a security boundary.

See [PLAN.md](PLAN.md) for the architecture, delivery phases, and validation strategy. The canonical skill is [skills/professional-coding/SKILL.md](skills/professional-coding/SKILL.md).

## Usage

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

The repository currently contains policy files and skill definitions. These deterministic commands are planned, not yet available:

```bash
doctor
bootstrap plan
preflight --scope staged
github-flow plan
```

Do not run those commands until the implementation phase adds their scripts. The currently available structural validation is:

```bash
python3 path/to/quick_validate.py skills/security-audit
python3 path/to/quick_validate.py skills/github-readiness
python3 path/to/quick_validate.py skills/code-quality-review
python3 path/to/quick_validate.py skills/project-bootstrap
python3 path/to/quick_validate.py skills/professional-coding
```

## Privacy

This repository must not contain credentials, real usernames, machine-specific paths, hostnames, network addresses, device serials, customer data, or unredacted diagnostics. Use neutral placeholders and synthetic test data.
