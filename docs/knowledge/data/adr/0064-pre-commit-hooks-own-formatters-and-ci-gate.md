---
type: adr
stage: accepted
description: Each formatter and linter has one owner, a pre-commit hook, and the CI pre-commit job runs the same hooks in the pinned agentdev-devcontainer image.
---

# The pre-commit hooks own each formatter and the CI check

Two tools that both claim a file rewrite each other's output, so the diff
depends on which one ran last. For this reason, each formatter and linter has
one owner, a pre-commit hook. The CI `pre-commit` job runs the same hooks in the
pinned `agentdev-devcontainer` image. CI and a commit then use tools from the
same version owners, so there is no second version to drift from and nothing to
keep in parity by hand. A version owner is the one place that pins the version
of a hook tool, such as `uv.lock` or the image.

## Considered Options

- Super-Linter as the CI check. Rejected: its image duplicates each hook and
  pins its own tool versions, so every version bump is a manual sync that
  Renovate cannot do.
- `gitleaks/gitleaks-action`. Rejected: it needs a licence key for an
  organization, it lists only the first 30 commits of a pull request, and it
  downloads its own gitleaks beside the pinned one.
- Run the job in the image that the pull request builds. Rejected: lint then
  waits for the full image build, while the pinned image already carries every
  binary hook.
- Remote hook repositories. Rejected: each installs its own copy of a tool
  beside `uv.lock` or the image, which is the drift that one owner per tool
  removes.

## Consequences

- The gitleaks hook examines commits and not only the tree. As a result, the
  hook finds a secret that a pull request adds and then removes.
- A range that changes a version owner checks all files, because a version
  change can change the output for files that did not change.
- A new hook that runs an image binary needs two pull requests. The first adds
  the tool to the image. The second adds the hook after the digest update.
