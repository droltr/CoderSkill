# Commands

All commands are in `scripts/` and use only the Python standard library, except
`validate-project-profile` and `validate-lesson`, which need PyYAML. Checks are read-only unless the
table says otherwise.

## Install and use

| Command | What it does | Writes |
|---|---|---|
| `scripts/coderskill install [--update] [--force] [--agents a,b] [--worktree]` | Installs the skills from the signed `origin/main` (see [installation](installation.md)). `--worktree`: owner only, installs the working tree. | Skill folders, receipt, command copy, hook runtime |
| `coderskill request "<title>" --details "<text>"` | Records a skill change request in the clone's local `.private/change-requests/`. | That file |
| `coderskill start execute order 66 [--agent a] [--github url] [--confirm-account] [--run]` | Prints the identity and target and the start prompt; with `--run`, starts the agent. Also `projeye başla`. | Nothing |
| `scripts/coderskill-start` | Read-only preview of the start steps for the current folder. | Nothing |
| `scripts/install-hooks claude codex gemini git [--dry-run] [--force]` | Installs the agent and git hooks (see [hooks](hooks.md)). `--force` replaces another global `core.hooksPath`. | Agent settings (with backups), git hooks, global ignore |

## Checks

| Command | What it checks |
|---|---|
| `scripts/doctor` | System, repository and tool (Git, GitHub CLI, Python) readiness, as JSON. |
| `scripts/preflight --scope staged\|branch\|history [--base main]` | Secret and identifier audit of the scope, tests, adapter drift and `git diff --check`. `history` scans every added line in every reachable commit for secrets and private keys. |
| `scripts/security-audit [--root .] [--path p] [--format json\|sarif] [--all-files]` | Secrets, private keys, personal e-mail addresses, home paths, IPv4 and MAC addresses in publishable files; `--all-files` includes ignored files. Findings carry a redacted fingerprint, never the value. |
| `scripts/github-settings-check [--repo owner/name] [--expect-visibility public\|private]` | Default branch `main`, its protection (required CI, no force pushes, no deletion), secret scanning, push protection, Dependabot security updates, and optionally the visibility. |
| `scripts/identity-gate check` / `confirm` | Compares the authenticated GitHub account, the repository and the `origin` URL with the local record (`.coderskill/local/identity.json`); `confirm` writes the record. Exit codes: 0 match, 3 missing, 4 mismatch. |
| `scripts/build-adapters [--check]` | Generates `.claude/`, `.agents/` and `.gemini/` copies of `skills/` and `adapters/manifest.json`; `--check` only reports drift (used in CI). |
| `scripts/validate-project-profile <file>` | Validates `.coderskill/project.yml` (see `.coderskill/project.yml.example`). |
| `scripts/validate-lesson <file>` | Validates a durable project lesson and rejects sensitive or local data (see `knowledge/lesson.example.yml`). |
| `python3 ~/.config/coderskill/scripts/update_channel.py status --agent <a>` | Update state of one agent's installed skills, as JSON. |

## Planning helpers

| Command | What it does |
|---|---|
| `scripts/bootstrap plan` | Prints a non-mutating environment setup plan. `apply --confirm` only checks for explicit authorization; it installs nothing. |
| `scripts/github-flow plan --issue N --kind feature` | Prints the issue-to-pull-request steps for an issue. `apply` checks authorization and changes nothing. |
| `scripts/release-manifest --output <file>` | Writes release metadata and an SPDX 2.3 file inventory with checksums. |
| `scripts/release-verify <file>` | Verifies a release manifest's checksums. |

## Tests

```bash
python3 -m unittest discover -s tests -v
```

CI (`.github/workflows/validate.yml`) runs the tests, adapter drift, shell syntax of every wrapper,
`py_compile`, the profile and lesson validators, and the security audit. CodeQL runs separately.
