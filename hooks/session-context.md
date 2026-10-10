# CoderSkill rules (loaded by the CoderSkill session hook)

These rules apply to this session and to every subagent. They are mandatory.

1. Before any code, repository, research, hardware, or system change, load the
   `professional-coding` and `verified-agent-rules` skills and follow them. Read
   `.coderskill/project.yml` when present.
2. Work in this order and do not skip a step without saying so: research, plan, implement,
   verify that it works in the real environment, test, record, pull request.
3. Never make assumptions. Every claim is verified (cite the source or the command output) or
   explicitly labelled UNVERIFIED or ASSUMPTION with what would verify it. Never act on an
   unverified finding.
4. Run a negative control before trusting a positive result. A tool's exit code 0 is not proof.
5. Keep records in the local, git-ignored `.private/` folder (see the `work-records` reference
   of `professional-coding`). It is never pushed; GitHub holds only the public code, issues,
   pull requests, and documentation:
   - every user request in `.private/requests.md`, with status and how it was met;
   - research in `.private/research/`, plans and decisions in `.private/plans/`;
   - a cleaned session record in `.private/sessions/`.
   Public issues, pull requests, and commits must not contain private details, local paths,
   or personal data.
6. The user performs every merge. Never merge a pull request and never push to `main`.
7. Ask immediately before every hardware write. Never commit credentials or identifiers.
8. When the user says stop, make no further tool calls on the target and report the state.
