# Environment Bootstrap and Repository Discovery

Use this workflow before the first coding task on a machine, when a required tool is missing, when the repository location is unknown, or when authentication or remote identity may have changed.

## Safety boundary

Start with read-only discovery. Package installation, package-manager metadata refresh, PATH or shell-profile edits, credential creation, authentication, directory creation outside the active workspace, cloning, remote creation, and repository configuration are state-changing operations. Explain the exact proposed change and obtain explicit user authorization before performing it.

Never request, print, store, or transmit a plaintext token, password, private key, recovery code, or browser session. Prefer OS credential storage, the provider's supported device/browser flow, SSH agents, and short-lived or fine-grained credentials. Redact usernames, hostnames, home paths, IP/MAC addresses, repository secrets, and stable device identifiers from reports.

## 1. Establish system context

Determine without mutation:

- Operating system, version, CPU architecture, shell, and whether the session is local, containerized, remote, or sandboxed.
- Available package managers and whether administrative privileges would be required.
- Network reachability only when needed; do not probe unrelated hosts.
- Current working directory, filesystem permissions, free space when relevant, and whether the path is already inside a Git worktree.
- Repository-local instruction files and the applicable AI tool's skill discovery path.

Do not infer the operating system from path syntax alone. Do not run an installer copied from the internet without verifying its official origin and reviewing the requested permissions.

## 2. Resolve the local repository root

Use this precedence order:

1. A path explicitly supplied by the user.
2. An existing Git worktree containing the current directory.
3. A project entry in the local repository registry.
4. A configured repository root.
5. A platform-appropriate proposed default, shown to the user before creation.

Do not hardcode a personal home path in a tracked file. Store machine-local preferences in an ignored configuration file such as `${XDG_CONFIG_HOME}/professional-coding/config.toml` on compatible systems or the platform's standard per-user configuration directory. A configuration may define `repository_root`, but must not contain credentials.

Maintain a local, untracked repository registry containing only:

- Logical project name.
- Canonical absolute local path.
- Expected GitHub owner and repository name.
- Remote URL without embedded credentials.
- Default branch.
- Last verified timestamp.

Before accepting a registry entry, canonicalize the path, reject symlink escapes when the task is sandboxed, confirm directory ownership/permissions, and verify that the Git remote identity matches the registry. Search only configured roots; do not crawl an entire home directory or mounted disks by default.

If multiple clones match, do not guess. Report redacted candidate paths and ask the user to choose before editing.

After resolving the repository, follow `project-lifecycle.md` to audit GitHub synchronization before editing.

## 3. Audit required software

Build the required-tool set from the task and project files. Do not install every supported AI CLI preemptively.

Core checks normally include:

- `git`: executable, version, repository support, local author identity, and credential helper behavior.
- `gh`: executable and version when GitHub operations are in scope; authenticated account, host, protocol, token scopes, and target repository access without revealing the token.
- The active AI CLI (`codex`, `claude`, `gemini`, or another declared tool): executable, version, skill discovery, and workspace trust state.
- Project toolchain discovered from lockfiles/manifests, such as Python, Node.js, Java, Rust, Go, compilers, build systems, linters, and test runners.
- Security tools required by policy, such as secret, dependency, license, and static-analysis scanners.

For every requirement record one of: `ready`, `missing`, `incompatible`, `unauthenticated`, `unauthorized`, or `not-applicable`. Capture versions and executable paths, but redact machine-specific path prefixes in any published report.

Distinguish command absence from execution failure, sandbox denial, network failure, invalid credentials, insufficient GitHub scope, and unsupported version. Do not treat one as another.

## 4. Plan installation

When something is missing or incompatible, prepare an installation plan containing:

- Tool and required version range, derived from a checked-in compatibility manifest or project lockfile when available.
- Official package/source and integrity verification method.
- Selected scope: project-local or isolated toolchain first, then per-user, then system-wide only when necessary.
- Exact directories and configuration files that will change.
- Required network domains and administrative privileges.
- Expected disk usage when material.
- Rollback/uninstall steps.
- License and supply-chain implications.

Prefer a project-local, pinned, reproducible installation over unpinned global latest versions. Do not replace a working system tool when an isolated compatible version can be used. Never pipe a remote script directly into a shell. Download to a unique temporary directory, verify origin/checksum/signature when published, inspect the artifact type, install after authorization, and clean up temporary files.

Package-manager choice must follow the detected platform and existing project convention. Do not enable third-party repositories, modify system trust stores, disable signature checks, or weaken security policy merely to make installation succeed.

## 5. Configure Git safely

- Check local repository configuration before global configuration.
- Do not overwrite the user's global name, email, signing, editor, credential helper, aliases, or default branch settings.
- Prefer a verified GitHub noreply address when privacy is desired; never invent an identity without disclosing it.
- Do not store credentials in remote URLs.
- Verify `origin` owner/name and fetch/push URLs before any push.
- For external source code, keep `origin` for the private `droltr` project and use clearly named remotes such as `upstream` or `mirror`; never silently repoint an existing remote.
- Check `.gitignore` and local excludes before creating machine-local configuration, diagnostics, build caches, or authentication artifacts.

## 6. Configure GitHub safely

- Verify the active `gh` account is exactly the intended account before mutation.
- Verify authorization scopes without printing the credential. Use the minimum scopes needed for the requested operation.
- Confirm repository owner, name, visibility, and default branch independently before creation or upload.
- New project repositories under `droltr` must be private. Treat repository creation, visibility changes, issue/PR creation, push, and settings changes as separate external mutations covered by the user's requested scope.
- If authentication is missing or invalid, use the supported interactive login flow. Do not ask the user to paste a token into chat or place it in a tracked file.
- Stop if the target name already exists until its ownership and intended reuse are confirmed.

## 7. Readiness gate

Begin implementation only when:

- The intended local repository path is resolved and writable within the authorized scope.
- Existing user changes have been identified and will be preserved.
- Required tool versions are ready.
- Project dependencies can be restored reproducibly.
- Git identity and remotes are valid for the intended local operation.
- GitHub authentication and access are valid when a GitHub action is requested.
- Required security scanners are available, or the user has explicitly chosen a documented limited fallback that does not weaken a mandatory gate.
- No secret, credential, personal-data, or unsafe hardware prerequisite remains unresolved.

If a nonessential integration is unavailable, continue only with work that does not depend on it and report the limitation. Fail closed before publishing, hardware access, or destructive action.

## 8. Readiness report

Return a concise report with:

- Resolved project and redacted local path.
- Repository state, branch, default branch, and verified remote identity.
- Required tools with status and version.
- Missing/incompatible components and proposed installation actions.
- Authentication/access status without credential values.
- Security/privacy findings.
- Actions performed, approvals used, skipped checks, and blockers.

Do not claim the environment is ready when a required check was skipped or only inferred.
