# Local-First Project Lifecycle

Use this workflow when creating a project, resuming an existing project, selecting its implementation technology, or preparing completed work for GitHub.

## 1. Discover or name the project

- Search only the configured repository root and local registry described in `environment-bootstrap.md`; do not crawl unrelated user directories or mounted volumes.
- Look for an existing local folder and Git worktree that match the requested project and verified `droltr/<repository>` remote.
- If multiple candidates exist, stop and ask the user to select one. Do not merge, delete, or rename candidates automatically.
- If no project exists, propose a short, descriptive English name. Use lowercase kebab-case for the repository and folder unless the ecosystem requires another convention.
- Check local sibling names and the `droltr` GitHub namespace before finalizing the name.
- Never include a username, hostname, device serial, physical location, local path fragment, customer name, or another personal or stable identifier in the project name.

## 2. Synchronize before editing

For an existing Git project, complete a read-only synchronization audit before changing files:

1. Record the current branch, upstream, remotes, worktree status, submodules, and local commits not present upstream.
2. Verify that `origin` points to the expected private `droltr/<repository>` target without embedded credentials.
3. Fetch remote refs and prune only stale remote-tracking refs when network access is authorized. Fetching must not modify the worktree.
4. Compare local and remote commits and classify the state as `equal`, `local-ahead`, `remote-ahead`, `diverged`, `no-upstream`, or `offline/unverified`.
5. Preserve all uncommitted and untracked user work. Do not stash, reset, clean, rebase, merge, or switch branches merely to synchronize.
6. If remote changes exist, inspect them for conflicts, repository instructions, security impact, dependency changes, and migrations before integrating them.
7. Fast-forward a clean local branch only when it is safe and within the user's requested workflow. Resolve divergence through an explicit plan; never discard either side.

Begin implementation only after the state is equal or after the chosen reconciliation is complete. If synchronization cannot be verified, continue only when work is safely isolated on a new local topic branch and report that remote state remains unverified.

## 3. Define the project before implementation

Create or update concise English project documentation that states:

- What the project is.
- Its intended users and operating context.
- The problem it solves and why it exists.
- Its scope, explicit non-goals, and main constraints.
- Supported platforms, devices, services, or systems.
- Whether it is specific to particular hardware, operating systems, protocols, or deployments.
- High-level architecture, setup requirements, validation method, safety considerations, and rollback approach.
- Privacy and data-handling boundaries.

Do not publish local filesystem layouts, real usernames, hostnames, serial numbers, account identifiers, network addresses, credentials, screenshots, or diagnostics that can identify the user or a device. Use neutral placeholders such as `<project-root>`, `<device>`, and `<host>`.

## 4. Research and select implementation languages

Research the appropriate language or languages before committing to a new project's architecture. For an existing project, preserve its established stack unless evidence and the requested change justify migration.

Use current primary sources: official language/toolchain documentation, target-platform or device SDK documentation, protocol specifications, package registries, and original benchmark or security material when performance or safety claims matter. Record source links and access dates without copying large passages.

Evaluate candidates against task-specific criteria:

- Target platform, device, runtime, browser, operating system, and deployment constraints.
- Required SDKs, hardware/protocol bindings, libraries, and ecosystem maturity.
- Memory, latency, throughput, startup, binary size, power, and real-time requirements.
- Type and memory safety, concurrency model, dependency/supply-chain exposure, and secure defaults.
- Testability, observability, debugging, tooling, cross-compilation, packaging, and reproducible builds.
- Team maintainability, interoperability with existing code, long-term support, license, and operational cost.

Produce a short English decision record containing the considered options, evidence, tradeoffs, chosen language(s), rejected alternatives, risks, and review triggers. Do not choose a language solely because it is popular or familiar. Use multiple languages only when component boundaries provide a clear benefit that outweighs integration and maintenance costs.

## 5. Work locally

- Create or select the GitHub issue for meaningful work, then use a short-lived topic branch.
- Implement and test locally. Keep experiments isolated from the verified baseline.
- Make focused commits only after applicable validation, secret/identifier scanning, and review of the staged diff.
- Record tested and approved changes in English with exact validation evidence. Clearly distinguish automated, mocked, simulated, and physical verification.
- Keep local-only configuration and repository registry files ignored and outside published artifacts.

## 6. Publish at a safe completion point

Before upload:

1. Re-fetch and compare the target branch because it may have changed during local development.
2. Reconcile remote changes without overwriting local or remote work.
3. Run all required project checks, secret/PII/device-identifier scans, dependency review, and staged/branch diff inspection.
4. Verify the target owner, private visibility, repository name, branch, issue, and pull-request base.
5. Confirm that project documentation accurately describes purpose, problem, scope, platform/device specificity, setup, validation, safety, and rollback.
6. Push only the topic branch and create or update a focused pull request. Use draft status for incomplete, experimental, or hardware-risking work.

Do not merge merely because upload succeeded. Required CI, human review, resolved conversations, and repository merge policy remain mandatory. Report issue, commit, branch, and pull-request links only after verifying them.

## 7. Privacy review

Before any commit or publication, inspect code, documentation, tests, fixtures, filenames, metadata, screenshots, generated artifacts, Git configuration, submodule URLs, and diagnostic output for identifying information. At minimum reject or redact:

- Credentials, tokens, passwords, private keys, cookies, and authentication material.
- Real usernames, personal names where unnecessary, email addresses, and account identifiers.
- Home directories, machine-specific paths, hostnames, IP/MAC addresses, and internal network topology.
- Device serials, UUIDs, hardware fingerprints, license keys, and stable device identifiers.
- Customer/user data, private repository URLs not required for the project, and unredacted logs.

Automated scanning is a gate, not a substitute for manual review. Do not publish a detected value in a finding; use its category, redacted fingerprint, and file location.
