# Security Policy

## Supported versions

Only the latest commit on `main` is actively supported. Older revisions may contain known or unaddressed issues.

## Reporting a vulnerability

Please use GitHub private vulnerability reporting or a private security advisory for suspected vulnerabilities, exposed credentials, or personal-data leaks. Do not disclose exploitable details in a public issue.

Include a concise impact description, affected revision or file, safe reproduction steps, and any recommended mitigation. Redact secrets and unique identifiers from all evidence.

If a secret was committed, stop distribution, rotate it when applicable, and report the incident privately. Repository history cleanup does not remove copies held by existing clones, forks, or caches.

## Scope

The project includes policy files, adapters, validation scripts, and documentation. It does not perform physical hardware writes.

## Security review record

The independent review for the v0.2 hardening milestone was completed on 2026-09-15. The scope covered repository scripts, authorization gates, workflow permissions, dependency metadata, secret and identifier scanning, path handling, and privacy documentation.

Results: no confirmed vulnerabilities or exposed secrets were found by the local audit, CodeQL, or required CI checks. Residual risks are tracked separately: GitHub Actions currently use version tags rather than immutable commit references, and optional provider-validity secret checks remain disabled by repository policy. These are defense-in-depth improvements, not confirmed exploits.

Review evidence is limited to redacted, reproducible command results; no credentials, host data, serial numbers, or exploit details are published.
