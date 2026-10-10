# Troubleshooting

## Install and updates

**`refusing to install … commits without a trusted signature`**
A commit on `main` since your installed version is not signed by GitHub's web-flow key or an allowed
SSH signer, often after a "Rebase and merge" or a direct push. Check it with
`git log --show-signature <commit>`. Fix it on `main` through a pull request, or, as the owner,
install deliberately with `scripts/coderskill install --update --worktree` after reviewing the code.

**`cannot verify signatures: … does not have the pinned GitHub fingerprint`**
GitHub may have rotated its web-flow key. Compare the key at `https://github.com/web-flow.gpg` with
GitHub's documentation, then update the pinned fingerprint in `scripts/update_channel.py` through a
pull request.

**`stopped <agent>/<skill>: it was changed after installation`**
The installed copy differs from what CoderSkill installed. Keep your change by recording it with
`coderskill request`, then run `coderskill install --update --force`; the old copy goes to
`~/.local/share/coderskill/backups/`.

**`No CoderSkill clone recorded`**
Run `scripts/coderskill install` once from the clone.

**The session start says "fetch failed"**
The machine is offline or the remote is unreachable. The last fetched state is used; the next session
start tries again.

## Hooks

**"installed CoderSkill skills and hook files are read-only for agents"**
The agent tried to edit an installed copy. Change the source in the CoderSkill repository through a
pull request, or record the request with `coderskill request`.

**"never push to main"** or the `pre-push` refusal
Push a topic branch and open a pull request. For a deliberate owner push, run the command yourself
with `CODERSKILL_ALLOW_PROTECTED_PUSH=1`.

**"the commit would contain a …"**
A token or private key is staged. Remove it from the files and the index, and rotate it if it was
ever pushed.

**"new name … is not GitHub-compatible"**
Use ASCII letters, digits, `.`, `-` and `_`, with no spaces, no trailing dot and no Windows reserved
names.

**A hook does not seem to run**
Check that `~/.claude/settings.json` (or `~/.codex/hooks.json`) contains commands with
`coderskill_hook.py`, and run `scripts/install-hooks claude codex git --dry-run` to compare.

## Signing

**Commits are not "Verified" on GitHub**
Check `git config commit.gpgsign`, `gpg.format` and `user.signingkey`, test with `git verify-commit`,
and make sure the public key is registered on GitHub as a *signing* key. See the commit-signing
section of [`environment-bootstrap.md`](../skills/professional-coding/references/environment-bootstrap.md).
