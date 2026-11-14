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

- Each hook tool has one version owner, and Renovate updates the tool only
  there. `uv.lock` owns the Python tools, which a hook runs through `uv run`.
  `dev_tools_pinned_tools` in `ansible/roles/dev_tools/defaults/main.yml` owns
  the image binaries. A `bunx <package>@<version>` entry in the hook owns the
  Bun tools.
- Each hook is `language: system` in a `repo: local` block, so
  `pre-commit install-hooks` makes no hook environment and no tool has a second
  copy.
- The gitleaks hook examines commits and not only the tree. It uses
  `GITLEAKS_LOG_OPTS` when it is set, which CI does for each event, then the
  push range that pre-commit gives, and if neither is available, the staged
  change. As a result, the hook finds a secret that a pull request adds and then
  removes.
- A hook outside the Dev Container needs the same binaries on `PATH`.
- A range that changes a version owner checks all files, because a version
  change can change the output for files that did not change.
- A new hook that runs an image binary needs two pull requests. The first adds
  the tool to the image. The second adds the hook after the digest update.
