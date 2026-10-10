# project-bootstrap

Source: [`skills/project-bootstrap/SKILL.md`](../../skills/project-bootstrap/SKILL.md)

## Purpose

Prepare or resume a local-first project safely: find the right local folder, check how it relates to
GitHub, check the tools it needs, research the implementation language, and write down what the
project is for, before anything is built.

## When it is used

Project start or resume, or an environment-readiness question. It does not implement features or
publish anything unless that is asked separately.

## How it works

The skill is read-only. It uses the detailed workflows of `professional-coding` when they are
installed:

- [`environment-bootstrap.md`](../../skills/professional-coding/references/environment-bootstrap.md):
  system context, repository root, required software, installation plan, Git and GitHub
  configuration, commit signing, readiness gate.
- [`project-lifecycle.md`](../../skills/professional-coding/references/project-lifecycle.md):
  discovery, synchronization, project definition, language research, local work, publication,
  privacy review.

Without them (a standalone install), it applies the minimum rules below.

## Rules and why they exist

- **Search only user-supplied or configured roots.** Never crawl personal storage. *Why:* privacy and
  speed.
- **Ask when several local clones match.** *Why:* editing the wrong copy loses work.
- **Preserve uncommitted and untracked work.** *Why:* the local folder may hold the only copy.
- **Verify local and remote identity and classify synchronization before editing** (equal, local
  ahead, remote ahead, diverged, no upstream, offline). *Why:* editing a stale or diverged copy
  creates conflicts.
- **Check only the tools this project needs.** *Why:* installing every supported tool is noise and
  risk.
- **Research language choices from primary sources** and record the evidence and trade-offs in
  English. *Why:* the choice is hard to reverse.
- **Document purpose, problem, scope, non-goals, platform, validation, privacy, safety and rollback.**
  *Why:* a project without a written purpose drifts.
- **No install, authentication, clone, repository creation or publication without explicit
  authorization.**
- **Never publish credentials, personal paths, user or host names, addresses, serials or other stable
  identifiers.**

## Relationships

- Called from [professional-coding](professional-coding.md) at project start; reuses its references.
- Claims follow [verified-agent-rules](verified-agent-rules.md).

## Outputs

A readiness result: selected project, redacted location, synchronization state, required tools,
language decision status, blockers and next actions.

## Limits

It plans and reports; installation and publication happen later under `professional-coding` with
authorization.
