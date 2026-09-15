# Contributing to CoderSkill

Thank you for helping improve CoderSkill. All repository artifacts must be written in clear, professional English.

## Workflow

1. Open or reference a focused GitHub issue.
2. Create a short-lived topic branch (`feature/`, `fix/`, `security/`, `docs/`, `test/`, or `chore/`).
3. Keep the change focused and preserve the verified behavior of `main`.
4. Run the applicable validation commands and inspect the diff for secrets and personal data.
5. Open a pull request using the repository template. Do not merge until required checks and review conversations are complete.

## Safety and privacy

Never commit credentials, private keys, local paths, usernames, hostnames, IP or MAC addresses, serial numbers, or unredacted diagnostics. Automated tests must not write to physical hardware.

## Validation

```bash
python3 -m unittest discover -s tests -v
scripts/build-adapters --check
scripts/validate-project-profile .coderskill/project.yml.example
scripts/validate-lesson knowledge/lesson.example.yml
git diff --check
```
