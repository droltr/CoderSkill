# Hooks

Skills are text, and an agent decides whether to read them. Hooks make the most important rules
independent of that decision: the agent's tool runs them at fixed points, and git runs its hooks on
every commit and push, whoever starts it.

All hook code is in `hooks/` and uses only the Python standard library. `scripts/install-hooks`
copies it to `~/.config/coderskill/`, so the installed hooks do not depend on the branch checked out
in the CoderSkill clone.

## Agent hooks

| Event | Claude Code | Codex | Gemini CLI | What CoderSkill does |
|---|:-:|:-:|:-:|---|
| `SessionStart` | ✓ | ✓ | ✓ | Injects the rules (`hooks/session-context.md`), the user communication language from the locale, the CoderSkill update state, the local and GitHub sync state, open requests, change requests and research notes from `.private/`. Saves a snapshot of the working tree. |
| `SubagentStart` | ✓ | ✓ | – | Injects the rules and the language into every subagent; reports updates installed during the session. |
| `UserPromptSubmit` | ✓ | ✓ | – | Logs the request to `.agent-sessions/requests.jsonl`; turns "stop"/"dur" into an instruction to stop; reports an important CoderSkill update, or skills installed by another session, once each. |
| `PreToolUse` | ✓ | – | – | Denies or asks before risky tool calls (table below). |
| `Stop` | ✓ | ✓ | – | Sends a final answer back once when it uses hedging words ("probably", "muhtemelen" …) without an UNVERIFIED/ASSUMPTION label; reminds when files changed but no record was updated. |
| `SessionEnd` | ✓ | ✓ | – | Copies the transcript (and subagent transcripts) to `.agent-sessions/transcripts/`, because agents delete old transcripts. |

Codex runs the same hook format from `~/.codex/hooks.json`; its tool names for `PreToolUse` are not
mapped yet. Gemini CLI runs the session-start hook from `~/.gemini/settings.json`.

### PreToolUse decisions (Claude Code)

| Situation | Decision |
|---|---|
| `gh pr merge` or the merge API | deny: the user merges |
| `git push` to `main` or `master`, including `HEAD`, `@`, `git -C`, `cd … &&`, wildcard refspecs, `--all`, `--mirror` | deny |
| `git merge` while on `main` or `master` | deny |
| `--no-verify`, `git commit -n`, `git -c core.hooksPath=…`, `GIT_CONFIG_*` or `GIT_DIR` overrides | deny: they switch off the git hooks |
| `CODERSKILL_ALLOW_PROTECTED_PUSH` set by the agent | deny: reserved for the user |
| A commit that would contain a secret or private key (staged files, or the work tree with `-a` or pathspecs) | deny |
| A new file or folder whose name is not GitHub-compatible | deny |
| Writes to installed CoderSkill skills or runtime folders (`Write`, `Edit`, `MultiEdit`, `NotebookEdit`, and shell commands such as `sed -i`, `cp`, `mv`, `rm`, redirections) | deny; reading is allowed, and other skills stay writable |
| `coderskill install --worktree` | deny: installs unreviewed code |
| Hardware writes (`i2cset`, `i2ctransfer`, `flashrom -w`, `nvflash`, `setpci …=`, `nvidia-smi -pl`, `liquidctl set`, `openrgb --color`, `ipmitool raw`, `ectool`, `dd of=/dev/…`), also inside `sudo`, `env`, `sh -c`, `eval` | ask |

The shell parser follows `cd`, unwraps `sudo`, `doas`, `env`, `nice`, `timeout`, `sh -c` and `eval`,
and ignores text inside heredocs. It is best effort; the git hooks and the agent's own permission
system remain the hard boundaries.

## Git hooks

`scripts/install-hooks git` sets the global `core.hooksPath` to `~/.config/coderskill/git-hooks` and
adds `.private/`, `.agent-sessions/` and `.coderskill/local/` to the global ignore file.

| Hook | Effect |
|---|---|
| `pre-commit` | Rejects `.private/`, `.agent-sessions/`, the local notes `PROJECT_SCOPE.md`, `PROJECT_STATUS_REPORT.md` and `PROJECT_TASKS.md`, and secrets in any commit; then runs the repository's own `pre-commit`. |
| `pre-push` | Refuses updates to `main` or `master` on any remote. Git passes every ref it is about to push, so every spelling of the command is covered. The owner can allow one deliberate push with `CODERSKILL_ALLOW_PROTECTED_PUSH=1 git push …`. Then runs the repository's own `pre-push`. |
| `post-merge` | In the CoderSkill clone on `main`, refreshes the update state after `git pull`; then runs the repository's own hook. |
| Other client hooks | Pass through to the repository's own hook of the same name. |

## Failure behaviour

- **Agent hooks fail open.** Every command ends in `|| true` and internal errors are swallowed, so a
  broken hook never blocks the agent. A hook only blocks through an explicit decision.
- **Git hooks fail closed.** If the check cannot run, git stops the commit or push.

## Local data the hooks write

| Path | Content | Protection |
|---|---|---|
| `<project>/.agent-sessions/` | Prompt log, transcripts, snapshots | Written only when the folder is real, git-ignored and untracked; a cloned repository cannot redirect the writes with symlinks or ignore rules. |
| `~/.local/state/coderskill/` | Update state, fetch timestamp, per-session notes, install lock | User-only state. |

## Install

```bash
scripts/install-hooks claude codex git --dry-run   # show the result
scripts/install-hooks claude codex git             # write it, with backups of changed files
```

Existing CoderSkill entries are replaced and other hooks are kept. `coderskill install` refreshes the
hooks that are already installed whenever it installs a new version.
