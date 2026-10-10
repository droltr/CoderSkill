# OpenRGB, game-lighting, and Mystic Light Projects

Read this reference only when the current repository contains OpenRGB, `game-lighting`, MSI
Mystic Light, or the Hardware Sync plugin, or when one of them is explicitly in scope. These
rules moved here from the generic skill; they protect a specific hardware project and must
not be applied to unrelated projects. They should also be kept in that project's own
`AGENTS.md`.

## Compatibility and stability

- Perform upstream OpenRGB changes on an appropriate fork and topic branch.
- Keep `game-lighting` as a standalone repository included through a pinned Git submodule.
- Do not enable the Hardware Sync plugin until its Qt metadata compatibility problem is
  resolved and verified.

## Hardware safety

- Use the current verified upstream OpenRGB implementation.
- Do not enable `ENABLE_UNTESTED_MYSTIC_LIGHT`.
- Start physical testing with a static, low-brightness color.
- Keep the Hardware Sync plugin disabled while its runtime compatibility issue remains
  unresolved.

## Validation

- Run `python3 -m unittest discover -s game-lighting/tests -v` when the `game-lighting`
  submodule is present.

## Project tracking

For the repository whose history matches these records (verify the owner, name, and current
issue state first; never carry these numbers into another project):

- The governance and security baseline was implemented through issue #1 and pull request #2.
- The Hardware Sync plugin Qt metadata mismatch is tracked in issue #3.
- Future work on issue #3 uses a dedicated `fix/` branch and begins with a draft pull request.
- Dependabot updates are handled as separate pull requests and reviewed individually.
