---
name: code-quality-review
description: Perform a focused, read-only professional code-quality review for correctness, clarity, maintainability, architecture fit, tests, and documentation. Use when the user asks whether code is professionally written or requests a code review; do not run full security or GitHub governance workflows unless requested.
---

# Code Quality Review

Review the requested code or diff without modifying it. A request to check, review, or assess does not authorize fixes, dependency installation, commits, pushes, or remote changes.

All first-party code, identifiers, comments, documentation, and publishable review artifacts must use clear, concise, professional English. Communicate directly with the user in Turkish unless another language is requested.

## Review criteria

- Correctness, edge cases, error handling, resource lifetime, concurrency, and data integrity.
- Fit with existing architecture and established project conventions.
- Simplicity, naming, cohesion, coupling, duplication, and unnecessary abstraction.
- API clarity, compatibility, configuration behavior, observability, and failure diagnostics.
- Test value, coverage of meaningful behavior, determinism, isolation, and missing regressions.
- Documentation accuracy, project purpose, platform/device constraints, safety, and rollback guidance.
- Performance only where evidence or task constraints make it material.

Do not turn style preference into a defect. Prioritize concrete behavioral and maintenance impact. Mention security only when a visible defect is relevant; route a systematic security review to `security-audit`.

## Output

Lead with actionable findings ordered by impact. Include file/line evidence, consequence, and a focused recommendation. Then provide assumptions, validation gaps, and a short overall assessment. If no finding is present, state what was reviewed and what remains unverified.
