# Agent hooks for CoderSkill

- Date: 2026-10-10
- Question: How can CoderSkill load its rules at session start and enforce mandatory rules in Claude Code, Codex and Gemini CLI?
- Related: #74, #75

## Verified findings

### Claude Code

- Hook events include `SessionStart`, `SubagentStart`, `UserPromptSubmit`, `PreToolUse`, `Stop`, `StopFailure` and `SessionEnd` (source: https://code.claude.com/docs/en/hooks.md, accessed 2026-10-10).
- `SessionStart` adds plain stdout or `hookSpecificOutput.additionalContext` to the conversation; output over 10,000 characters is replaced by a file path and a preview (same source).
- `SubagentStart` cannot block a subagent but can inject `additionalContext` into it; hooks from settings files also run inside subagents (same source).
- `PreToolUse` returns `permissionDecision` `allow`, `deny`, `ask` or `defer`; with several hooks the most restrictive answer applies (source: https://code.claude.com/docs/en/hooks-guide.md).
- `Stop` input contains `stop_hook_active` and `last_assistant_message`; `decision: "block"` with a `reason` continues the turn (source: hooks.md, "Stop input").
- Settings files are watched and hook edits apply to running sessions without a restart (source: https://code.claude.com/docs/en/settings.md).
- A timed-out hook does not block the tool call unless `onFailure: "block"` is set; a project can set `disableAllHooks` over user settings (source: hooks.md, hooks-guide.md).
- Transcripts are deleted after `cleanupPeriodDays`, default 30, without a message (source: https://code.claude.com/docs/en/settings-reference.md).

### Codex (0.162.1)

- User hooks are read from `~/.codex/hooks.json` with the same `{"hooks": {"<Event>": [{"matcher", "hooks": [{"type": "command", ...}]}]}}` shape (source: openai/codex, tag `rust-v0.162.1`, `codex-rs/config/src/hook_config.rs`).
- Events: `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`, `Interrupt` (same file).
- `SessionStart` and `SubagentStart` accept `hookSpecificOutput.additionalContext` or plain stdout (source: `codex-rs/hooks/schema/generated/session-start.command.output.schema.json`, `codex-rs/hooks/src/events/session_start.rs`).
- Input fields: `UserPromptSubmit` has `prompt`; `SessionEnd` has `transcript_path` and `reason`; `Stop` has `last_assistant_message` and `stop_hook_active` (source: `codex-rs/hooks/schema/generated/*.command.input.schema.json`).

### Gemini CLI (v0.63.0)

- Hooks are configured under `hooks` in `settings.json`; `timeout` is in milliseconds (source: google-gemini/gemini-cli, tag `v0.63.0`, `docs/hooks/index.md`).
- `SessionStart` (`source`: `startup`, `resume`, `clear`) uses `hookSpecificOutput.additionalContext` (source: `docs/hooks/reference.md` on the default branch).

## Unverified

- > **⚠️ UNVERIFIED:** Codex asks the user to trust newly added user-level hooks before running them (`trusted_hash` exists in its hook state). To verify: start Codex after installing and observe the prompt.
- > **⚠️ UNVERIFIED:** the Gemini CLI `SessionStart` output format is unchanged in v0.63.0 (read from the default branch). To verify: read `docs/hooks/reference.md` at the tag, or run Gemini CLI.
- > **⚠️ UNVERIFIED:** Codex `PreToolUse` tool names for shell commands; Codex is therefore installed without `PreToolUse`. To verify: read the Codex tool-name mapping and test.

## Rejected leads

- Enforcing rules only through skill text: agents load skills by choice, so nothing guarantees the rules are read.
- Using `http` hooks to call routine endpoints directly: the hook input JSON is not the request body the routine API expects.
