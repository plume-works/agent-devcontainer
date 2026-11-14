---
type: adr
stage: accepted
description: Each formatter and linter has one owner, a pre-commit hook, and the CI pre-commit job runs the same hooks in the pinned agentdev-devcontainer image.
---

# The pre-commit hooks own each formatter and the CI check

Two tools that both format a file change the output of each other. For this
reason, each formatter and linter has one owner, a pre-commit hook. The CI
`pre-commit` job runs the same hooks in the pinned `agentdev-devcontainer`
image. CI and a commit then use tools from the same version owners, so no second
version can be different.

## Considered Options

- Super-Linter as the CI check. Rejected: its image has a copy of each hook with
  its own tool versions, and Renovate cannot keep them the same.
- `gitleaks/gitleaks-action`. Rejected: it needs a licence key for an
  organization, it sees only the first 30 commits of a pull request, and it
  downloads a second gitleaks.
- Run the job in the image that the pull request builds. Rejected: lint then
  waits for the full image build, and the pinned image already has each binary.
- Remote hook repositories. Rejected: each installs a second copy of a tool next
  to `uv.lock` or the image.

## Consequences

- A range that changes a version owner checks all files, because a version
  change can change the output for files that did not change.
- A new hook that runs an image binary needs two pull requests. The first adds
  the tool to the image. The second adds the hook after the digest update.
