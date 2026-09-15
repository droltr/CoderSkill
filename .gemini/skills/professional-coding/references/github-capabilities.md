# GitHub Capability Selection

Select only the GitHub capabilities required by the current project profile. Do not invoke unrelated checks or consume context for unused features.

## Capability map

| Capability | Use when | Default for this framework repository |
| --- | --- | --- |
| Agent | An authorized AI coding agent is asked to prepare a branch or pull request | Optional; terminal skills remain canonical |
| Actions | Tests, validation, security checks, or release automation must run on GitHub | Enabled |
| Projects | Work needs a visual board across multiple milestones or contributors | Optional; milestones and issues are sufficient for solo work |
| Security | Secrets, vulnerabilities, dependencies, privacy, or publication risk must be assessed | Enabled |
| Insights | Activity, traffic, dependency, or adoption trends need review | Informational; no workflow gate |

## Selection rules

- Read `.coderskill/project.yml` when present and use its `active_profiles` values.
- Load `security-audit` for security/privacy requests; do not load Agent, Projects, or Insights guidance unless requested.
- Load `github-readiness` for repository governance, Actions, Projects, milestone, or publication checks.
- Load `project-bootstrap` for local discovery and environment readiness.
- Load `professional-coding` for changes spanning implementation, validation, and delivery.
- Treat an Agent as an optional implementation participant, never as a bypass for tests, review, branch policy, or privacy gates.
- Keep Projects and Insights observational unless the user requests planning or reporting changes.
- Record project-specific selections in the profile and explain deviations in the project decision record.

## This repository

CoderSkill uses Actions, Security, Issues, and Milestones. Agent integration is optional, Projects are not required for the solo workflow, and Insights are observational only.
