# Work Records

Use this reference for every task that changes a project or produces findings worth keeping.
It defines the mandatory work order and where each record lives, so another agent or a later
session can see what was asked, what was found, what was done, how it was verified, and what
is left.

## Mandatory work order

Do not start a step until the previous one has its evidence. If a step is skipped, record why.

| Step | Required output | Where it is recorded |
|---|---|---|
| 1. Request | The request in one line, its status | `docs/REQUESTS.md`; an issue when it needs code |
| 2. Research | Sources, access date, verified and unverified findings | `docs/research/` |
| 3. Plan | Steps and acceptance criteria | Issue body (checklist) |
| 4. Decision | Options, evidence, choice, rejected alternatives | `docs/decisions/` |
| 5. Implement | Commits on `<type>/<issue>-<slug>` that reference the issue | Git history |
| 6. Verify it works | The real command, run, or observation proving the behavior | Pull request, `Verification` section |
| 7. Test | Automated tests with negative controls; CI result | `tests/`, pull request |
| 8. Record | Request status, how it was met, remaining work | `docs/REQUESTS.md`, session record |
| 9. Pull request | `Closes #<issue>`; the user merges | GitHub |

Step 6 comes before step 7: a test suite that passes does not prove the feature works for the
user. Verify the artifact the user actually runs first, then lock the behavior in with tests.

## Tracked records

Tracked records must pass the privacy rules of the project: no credentials, personal data,
home-directory paths, hostnames, serial numbers, or unredacted logs.

### `docs/REQUESTS.md`

One table per date. Every user request gets a row, including questions answered without code.

```markdown
# Requests

Status: ✅ done · 🔄 in progress · ⏳ planned · ❓ needs a decision · ⛔ dropped

## 2026-10-10

| # | Request | Status | How it was met | Where |
|---|---|---|---|---|
| 1 | Load the rules at session start | ✅ | SessionStart hook injects `hooks/session-context.md` | #41, `hooks/` |
| 2 | Trigger cloud routines from local events | ⏳ | Design agreed, not built | #42 |
```

- `How it was met` states the approach and the evidence in one line, not "done".
- Keep a row when the request is dropped or replaced; set ⛔ and say why.
- Numbers continue across dates so that `#n` stays unique within the file.

### `docs/research/YYYY-MM-DD-<topic>.md`

```markdown
# <Topic>

- Date: 2026-10-10
- Question: <what had to be found out>
- Related: #74

## Verified findings
- <finding> (source: <URL or document section>, accessed 2026-10-10)
- <finding> (source: `<command>` output)

## Unverified
- > **⚠️ UNVERIFIED:** <claim>. To verify: <method>.

## Rejected leads
- <lead> — <why it does not apply>
```

### `docs/decisions/NNNN-<title>.md`

A short architecture decision record: context, options with evidence, decision, consequences,
and the condition that would reopen it. Number decisions sequentially and never rewrite an
accepted one; supersede it with a new record instead.

## Local records (never committed)

`.agent-sessions/` is created by the CoderSkill hook with its own `.gitignore` containing `*`.

| Path | Written by | Content |
|---|---|---|
| `.agent-sessions/requests.jsonl` | `UserPromptSubmit` hook | Every user prompt with time, agent, and session id |
| `.agent-sessions/transcripts/` | `SessionEnd` hook | Copy of the raw agent transcript |
| `.agent-sessions/records/YYYY-MM-DD-<slug>.md` | The agent | Cleaned session record |

Claude Code deletes its own transcripts after `cleanupPeriodDays` (default 30 days; see
https://code.claude.com/docs/en/settings-reference.md). The project copy is the durable one.

Session record format:

```markdown
# Session <date> — <topic>

## Requests
| # | Request | Result | How |
|---|---|---|---|

## Done
- <change> — evidence: <test, command, PR>

## Left
- <item> — next step, owner

## Unverified
- <claim> — to verify: <method>
```

## Completion check

Before reporting a task as finished:

1. Every request of the session has a row in `docs/REQUESTS.md` with a status and how it was met.
2. Research used for decisions is in `docs/research/` with sources.
3. The session record lists done, left, and unverified items.
4. The pull request contains the verification evidence and test results.
