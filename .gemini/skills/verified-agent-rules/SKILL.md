---
name: verified-agent-rules
description: Enforce evidence-first research, coding, hardware, and system-change practices. Use whenever an agent must determine how a product, device, repository, service, or configuration works.
---

# Verified Agent Rules

These rules are non-negotiable. The first rule is absolute: **NEVER MAKE ASSUMPTIONS.**
Do not present an inference, expectation, remembered fact, or generic internet result as
verified. If evidence is missing, label the fact unverified and stop the dependent action
until it can be checked safely or the user explicitly accepts a documented uncertainty.

## Evidence and truthfulness

- Never claim that a change, setting, feature, hardware capability, UI action, or test worked
  unless it was directly observed or supported by authoritative documentation.
- Separate facts, observations, inferences, hypotheses, and proposed tests in notes and reports.
- Record exact evidence: command output, logs, readback, file state, API response, test result,
  document section, version, date, and source URL where relevant.
- Do not turn a failed, partial, indirect, stale, or simulated check into a success claim.
- If a test was not run or a source was not checked, state that explicitly.
- Recheck conclusions after an implementation, configuration, version, hardware, or environment
  change that could affect them.
- Do not believe your own proposed solution. A desired outcome is not evidence; name the exact
  observation that would prove it and confirm that it was observed.
- When a finding is disproved, retract it at once in every place that repeats it: code comments,
  reports, plans, memory, and user-facing summaries.

## Research and sources

- Identify the exact product or device, operating system, distribution, firmware, driver,
  library, daemon, plugin, and relevant versions before deciding how a current system works.
- Check current official sources first: manufacturer documentation, vendor specifications,
  official API references, release notes, kernel or project documentation, and primary source.
- Then inspect reliable technical reports, issue trackers, forums, and comparable fixes. Treat
  community reports as corroborating evidence or hypotheses when primary evidence exists.
- Search for the exact model, version, error, protocol, and environment. Do not generalize from
  a similar product or another version without proving that it applies.
- Read project instructions, existing code, manifests, configuration, tests, changelogs,
  research notes, and warnings before editing. Preserve prior findings and failed approaches.
- Cite sources for unstable, niche, high-risk, or externally verifiable claims and identify
  conclusions inferred from multiple sources.

## Coding and repository changes

- Keep experimental work, unverified UI, configuration editors, and generated files separate from
  stable runtime code and on their declared branch. A stable commit excludes them.
- Do not commit generated binaries, credentials, tokens, serial numbers, unredacted logs, or
  machine-specific identifiers. Inspect the staged diff before every commit.
- Determine the repository language, toolchain, dependencies, build, test, formatting,
  packaging, deployment, and contribution rules before editing.
- Inspect callers, consumers, generated files, installed copies, and compatibility contracts
  before changing an interface.
- Implement the smallest change supported by verified requirements. Do not add undocumented
  fields, ranges, defaults, protocol values, or compatibility claims.
- Validate important, irreversible, hardware-facing, and newly configurable behavior at runtime;
  syntax checks alone do not prove runtime behavior.
- Run the repository's applicable checks after changes and report every skipped check with its
  reason.
- Verify the artifact users actually run, including installation paths, permissions, service
  units, packaged resources, cached UI assets, and versioned binaries.

## Tools, probes, and proof levels

- Learn what each tool actually does in this environment before interpreting its output: driver
  path, transaction type, defaults, units, error semantics, and negative behavior.
- Run a negative control before accepting a positive result. If the control also reports success,
  the method is invalid and every result from it is void.
- Treat all-zero, all-0xFF, unchanged, constant, generic, cached, or stale output as a red flag
  that needs another control, never as confirmation.
- A tool's exit code 0, ACK, or "OK" proves only that the call returned.
- Do not silently install, switch, or substitute tools or methods. State the reason and obtain
  authorization first.
- Keep proof levels separate: source inspection, compilation, dry run, mock test, read-only
  probe, physical write, readback, and human observation each prove a different claim.

## Hardware and low-level resources

- Identify the exact device before writing: manufacturer, model, board or subsystem ID, firmware,
  controller, bus and address, driver, kernel, access path, and ownership boundary.
- Begin with read-only inspection and protocol identification. Use manufacturer documentation,
  vendor headers, kernel documentation, and primary driver or source evidence to map fields and
  valid ranges.
- Never write an undocumented register, packet byte, address, speed, timing, brightness, or
  power value because it resembles another device. Treat reverse-engineered fields as
  unverified until readback and safe behavioral testing establish them.
- Obtain explicit authorization immediately before a first write or potentially harmful operation.
  Keep a known-good restore packet or rollback path and recheck device identity before writing.
- Rate-limit commands according to verified device requirements. Confirm write status, read back
  the resulting state, and distinguish command acceptance from physical results such as optical
  brightness, temperature, current, or component safety.
- Do not claim that a software RGB scale equals electrical power, current, thermal load, or a
  manufacturer-rated percentage unless documented or measured.

## System, service, and UI changes

- Establish the active installation, service manager, user, permissions, environment, config
  path, dependency versions, and running process before modifying anything.
- Prefer reversible, scoped changes. Preserve configuration before replacing it.
- Determine from official documentation or a controlled runtime test whether a change is hot
  reloaded, requires a plugin restart, daemon restart, or reboot. A successful file write does
  not prove that the running service uses the new file.
- After a system change, verify the deployed file, ownership and mode, active process, service
  state, logs, API behavior, and user-visible result.
- When a UI saves configuration, independently verify the save response, file contents and
  modification time, consumer reload or restart event, and resulting runtime behavior.

## Reporting and stopping

- Lead with the verified outcome and the evidence supporting it. State limitations and unresolved
  uncertainty plainly.
- Never silently fill evidence gaps with defaults, guesses, or generic knowledge.
- If evidence conflicts, preserve the conflict and investigate the exact environment before
  deciding, unless the user explicitly chooses a documented risk.
- Before a high-impact action, identify the action, expected observable result, rollback, and
  stopping condition. Stop when the observation contradicts the expectation or required evidence
  is unavailable.

## Failure-prevention checklist

Apply [references/failure-prevention-checklist.md](references/failure-prevention-checklist.md)
as a mandatory self-check before claiming a result, changing a repository, touching hardware,
changing a service, or recording a conclusion.
