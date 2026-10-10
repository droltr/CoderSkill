# Work Records

Use this reference for every task that changes a project or produces findings worth keeping.
It defines the mandatory work order and where each record lives, so another agent or a later
session can see what was asked, what was found, what was done, how it was verified, and what
is left.

## Two layers

| Layer | Where | Visibility | Content |
|---|---|---|---|
| Public tracking | GitHub repository | As the repository (often public) | Code, tests, README, CHANGELOG, issues, pull requests, merges |
| Private records | `.private/` in the project folder | Local only, never pushed | Requests, research, plans, decisions, session records, personal notes |

- Create the GitHub repository as soon as the project starts, so that issues, pull requests,
  and merges are tracked from the first change. Visibility is set per repository: every
  branch, file, and past commit of a public repository is public.
- `.private/` is never added to any Git remote. Exclude it in the project `.gitignore` and in
  the global ignore file; the CoderSkill git `pre-commit` hook also rejects it.
- Synchronize `.private/` between computers with a file synchronization tool. Synchronize the
  code only through GitHub (`git push` / `git pull`); do not let a synchronization tool copy
  `.git/` directories.
- Write public issues, pull requests, commit messages, and documentation without private
  details: no local paths, hostnames, addresses, serial numbers, credentials, or personal data.
  Put those details in `.private/` and refer to the issue number.

```
my-project/
├── src/  tests/  README.md  CHANGELOG.md   tracked, pushed to GitHub
├── .gitignore                               contains .private/ and .agent-sessions/
├── .private/                                local only
│   ├── requests.md                          every request, status, how it was met
│   ├── research/YYYY-MM-DD-<topic>.md       sources and findings
│   ├── plans/                               plans and decision records
│   ├── sessions/YYYY-MM-DD-<slug>.md        cleaned session records
│   └── notes/                               personal notes
└── .agent-sessions/                         written by hooks, local only
    ├── requests.jsonl                       every prompt (UserPromptSubmit hook)
    └── transcripts/                         raw agent transcripts (SessionEnd hook)
```

## Mandatory work order

Do not start a step until the previous one has its evidence. If a step is skipped, record why.

| Step | Required output | Where it is recorded |
|---|---|---|
| 1. Request | The request in one line, its status | `.private/requests.md`; a public issue when it needs code |
| 2. Research | Sources, access date, verified and unverified findings | `.private/research/` |
| 2b. Clarify | Open questions answered until the requirement is unambiguous | Issue body; `.private/requests.md` |
| 3. Plan | Steps and acceptance criteria | Issue checklist (public part), `.private/plans/` (details) |
| 4. Decision | Options, evidence, choice, rejected alternatives | `.private/plans/NNNN-<title>.md` |
| 5. Implement | Commits on `<type>/<issue>-<slug>` that reference the issue | Git history |
| 6. Verify it works | The real command, run, or observation proving the behavior | Pull request, `Verification` section |
| 7. Test | Automated tests with negative controls; CI result | `tests/`, pull request |
| 8. Record | Request status, how it was met, remaining work | `.private/requests.md`, session record, CHANGELOG |
| 9. Pull request | `Closes #<issue>`; the user merges | GitHub |

Step 2b (clarify): before planning, list what the request leaves open (users, inputs, limits,
error cases, success criterion). Answer what the code, documents, or research can answer; ask
the user only the questions whose answer changes what gets built, all at once and each with a
recommended default. Do not ask again later for decisions already answered.

Step 6 comes before step 7: a test suite that passes does not prove the feature works for the
user. Verify the artifact the user actually runs first, then lock the behavior in with tests.

## Formats

### `.private/requests.md`

One table per date. Every user request gets a row, including questions answered without code.

```markdown
# Requests

Status: ✅ done · 🔄 in progress · ⏳ planned · ❓ needs a decision · ⛔ dropped

## 2026-10-10

| # | Request | Status | How it was met | Where |
|---|---|---|---|---|
| 1 | Load the rules at session start | ✅ | SessionStart hook injects the rule file | #41, `hooks/` |
| 2 | Trigger cloud routines from local events | ⏳ | Design agreed, not built | #42 |
```

- `How it was met` states the approach and the evidence in one line, not "done".
- Keep a row when the request is dropped or replaced; set ⛔ and say why.
- Numbers continue across dates so that `#n` stays unique within the file.

### `.private/research/YYYY-MM-DD-<topic>.md`

```markdown
# <Topic>

- Date: 2026-10-10
- Question: <what had to be found out>
- Related: #41

## Verified findings
- <finding> (source: <URL or document section>, accessed 2026-10-10)
- <finding> (source: `<command>` output)

## Unverified
- > **⚠️ UNVERIFIED:** <claim>. To verify: <method>.

## Rejected leads
- <lead> — <why it does not apply>
```

Read the existing research notes before researching a topic again.

### `.private/plans/NNNN-<title>.md` (decisions)

A short architecture decision record: context, options with evidence, decision, consequences,
and the condition that would reopen it. Number decisions sequentially and never rewrite an
accepted one; supersede it with a new record instead.

### `.private/sessions/YYYY-MM-DD-<slug>.md`

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

Raw transcripts stay in `.agent-sessions/transcripts/`. Claude Code deletes its own copies
after `cleanupPeriodDays` (default 30 days; https://code.claude.com/docs/en/settings-reference.md),
so the project copy is the durable one. They may contain command output and secrets: never
publish them.

## Local and GitHub state

At session start the CoderSkill hook reports uncommitted changes, unpushed commits, branches
without a remote copy, branches behind or gone upstream, and a missing remote, based on the
last `git fetch`. Resolve them before new work: commit or stash, push topic branches, delete
merged local branches, and fast-forward `main`.

## Completion check

Before reporting a task as finished:

1. Every request of the session has a row in `.private/requests.md` with a status and how it
   was met.
2. Research used for decisions is in `.private/research/` with sources.
3. The session record lists done, left, and unverified items.
4. The pull request contains the verification evidence and test results, without private
   details.
5. Local work is pushed: no unpushed commits on topic branches.
