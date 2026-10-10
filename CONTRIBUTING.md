# Contributing to CoderSkill

Thank you for helping improve CoderSkill. All repository artifacts must be written in clear, professional English.

## Workflow

1. Open or reference a focused GitHub issue.
2. Create a short-lived topic branch named `<prefix>/<issue>-<slug>` (`feature/`, `fix/`,
   `security/`, `docs/`, `test/` or `chore/`).
3. Edit the canonical skills in `skills/` only, then run `scripts/build-adapters` to regenerate the
   `.claude/`, `.agents/` and `.gemini/` copies.
4. Keep the change focused and preserve the verified behaviour of `main`. Every new rule or hook
   decision gets a test with a negative control.
5. Sign every commit (one signing key per machine; see the commit-signing section of
   `skills/professional-coding/references/environment-bootstrap.md`).
6. Run the validation commands below and inspect the diff for secrets and personal data.
7. Open a pull request using the repository template. The repository accepts squash merges only;
   GitHub signs the squash commit, which the update channel requires.
8. Update the documentation in `docs/` when behaviour changes; every skill has a page in
   `docs/skills/`.

Private working files (requests, research, plans, session notes) stay in the local, git-ignored
`.private/` folder and are never committed.

## Safety and privacy

Never commit credentials, private keys, local paths, usernames, hostnames, IP or MAC addresses, serial numbers, or unredacted diagnostics. Automated tests must not write to physical hardware.

## Validation

```bash
python3 -m unittest discover -s tests -v
scripts/build-adapters --check
scripts/security-audit
scripts/validate-project-profile .coderskill/project.yml.example
scripts/validate-lesson knowledge/lesson.example.yml
git diff --check
```
