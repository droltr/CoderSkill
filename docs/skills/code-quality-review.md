# code-quality-review

Source: [`skills/code-quality-review/SKILL.md`](../../skills/code-quality-review/SKILL.md)

## Purpose

A focused, read-only review of whether code is professionally written: correct, clear, maintainable,
well tested and accurately documented.

## When it is used

A code review, or "is this code professional?". It does not run the full security or GitHub
governance workflows unless asked.

## How it works

The reviewer reads the requested code or diff and checks:

- correctness, edge cases, error handling, resource lifetime, concurrency and data integrity;
- fit with the existing architecture and conventions;
- simplicity, naming, cohesion, coupling, duplication and unnecessary abstraction;
- API clarity, compatibility, configuration behaviour, observability and failure diagnostics;
- test value: meaningful behaviour, determinism, isolation and missing regressions;
- documentation accuracy, purpose, platform constraints, safety and rollback guidance;
- performance, only where evidence or the task makes it material.

## Rules and why they exist

- **Read-only.** A request to review is not a request to fix, install, commit or push.
- **Style preference is not a defect.** Findings must have a concrete behavioural or maintenance
  impact. *Why:* noise hides the findings that matter.
- **Security only when a visible defect is relevant;** a systematic security review goes to
  `security-audit`.

## Relationships

- Hands security reviews to [security-audit](security-audit.md).
- Fixes are made under [professional-coding](professional-coding.md).
- Claims follow [verified-agent-rules](verified-agent-rules.md).

## Outputs

Actionable findings by impact, with file and line, consequence and a focused recommendation; then
assumptions, validation gaps and a short assessment. With no finding, it states what was reviewed
and what remains unverified.
