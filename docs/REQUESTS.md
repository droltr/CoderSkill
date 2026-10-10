# Requests

Status: ✅ done · 🔄 in progress · ⏳ planned · ❓ needs a decision · ⛔ dropped

See `skills/professional-coding/references/work-records.md` for the format.

## 2026-10-10

| # | Request | Status | How it was met | Where |
|---|---|---|---|---|
| 1 | Add the agent failure-prevention rules to CoderSkill | ✅ | Checklist moved into the `verified-agent-rules` skill references; missing rules (self-belief, retraction, tool and probe discipline, proof levels, experimental separation, staged-diff review) added to the skill body | #74, `skills/verified-agent-rules/` |
| 2 | Explain how agent hooks work and where they help | ✅ | Researched the official Claude Code, Codex and Gemini CLI hook documentation and source | `docs/research/2026-10-10-agent-hooks.md` |
| 3 | Load CoderSkill at session start for every agent | ✅ | `SessionStart` and `SubagentStart` hook for Claude Code and Codex; Gemini CLI session start through the installer | #74, `hooks/`, `scripts/install-hooks` |
| 4 | Plan hooks for the mandatory rules | ✅ | Graded enforcement: deny merges, pushes to `main`, staged secrets and bad names; ask before hardware writes; block once on unlabelled hedging | #74, `hooks/coderskill_hook.py` |
| 5 | Define how research, requests, sessions, done and remaining work are recorded, and map it to Git | ✅ | Mandatory work order and record locations; requests logged and transcripts copied by hooks | #75, `skills/professional-coding/references/work-records.md` |
| 6 | Keep agent session files in the project folder | ✅ | `SessionEnd` hook copies transcripts to the git-ignored `.agent-sessions/transcripts/` | #75 |
| 7 | Trigger claude.ai routines from local machine events through hooks | ⏳ | Design discussed; routine API trigger needs a token created in the web UI | — |
