---
name: systematic-debugging
description: Find and fix the root cause of a defect, failing test, crash, regression, or unexplained behavior with evidence instead of guesses. Use whenever something does not work as expected; do not use for new features or reviews.
---

# Systematic Debugging

Fix causes, not symptoms. Every step produces evidence; a change made "to see if it helps"
without a hypothesis is not debugging. Follow `verified-agent-rules` for all claims.

## 1. Reproduce

- Write down the expected and the actual behavior, with the exact input, command, version,
  platform, and configuration.
- Reproduce the failure yourself. If it does not reproduce, collect more data (logs, versions,
  environment differences) before changing code; never claim a fix for a failure you could
  not observe.
- Capture the reproduction as a failing automated test or a minimal script when the project
  allows it. This test is the success criterion.

## 2. Isolate

- Narrow the failing path: smallest input, last known good revision (`git bisect` when history
  is available), a single component, a single configuration change.
- Read the code and documentation on that path before forming a theory. Check recent changes,
  dependency versions, and environment differences.
- Use a negative control: confirm that the probe distinguishes the failing case from a working
  one.

## 3. Explain

- State one hypothesis about the root cause and the observation that would confirm or refute
  it. Test it. Keep a short log of hypotheses tried and their results.
- Stop changing code when two hypotheses in a row fail; return to step 2 and gather more
  evidence instead of stacking fixes.
- The root cause is found only when it explains every observed symptom.

## 4. Fix

- Make the smallest change that removes the root cause. Do not mix refactoring or unrelated
  cleanup into the fix.
- Run the reproduction test: it must now pass, and it must fail again when the fix is reverted.
- Run the project's full relevant test suite to check for regressions.

## 5. Record

- Keep the reproduction as a regression test.
- In the pull request and the session record, state the root cause, the evidence, the fix, and
  what remains unverified (for example hardware behavior that only mocks covered).
- If the defect has wider impact (data loss, security, other components), report it and open
  a separate issue instead of widening the fix silently.

## Hardware and system defects

Diagnose read-only first. A write to hardware, firmware, or a running service is not a probe:
it follows the hardware and system rules of `professional-coding` and needs authorization.
