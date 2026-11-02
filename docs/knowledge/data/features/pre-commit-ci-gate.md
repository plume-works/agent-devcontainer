---
type: feature
stage: implemented
description: pre-commit is the lint and format gate in CI as well as locally, with every hook running a uv-locked or image-provisioned tool, and Super-Linter is removed from the repository.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T06:44:52Z
sources:
- resource: .pre-commit-config.yaml
- resource: .github/workflows/primary-checks.yml
- resource: .github/workflows/reformat.yml
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: pyproject.toml
- resource: .github/renovate.json
---

# pre-commit is the CI gate

## Purpose

One tool, one configuration, and one version owner per tool for formatting and
linting, locally and in CI. The local hooks and the CI gate run the same
binaries at the same versions, so a clean commit means a green lint check.

## Behaviour

**Every hook is native.** `.pre-commit-config.yaml` has no remote hook
repositories. A hook runs either `uv run <tool>`, with the version in `uv.lock`
(ruff, ruff-format, ansible-lint, clang-format, and the pre-commit-hooks
fixers), or a binary the image provides, with the version in the `dev_tools`
role's `dev_tools_pinned_tools` (hadolint, shellcheck, gitleaks, actionlint,
zizmor, iwe). Prettier and the Renovate config validator keep their
`bunx <package>@<version>` pins. `pre-commit install-hooks` builds nothing.

**CI runs pre-commit.** Primary checks runs a pre-commit job inside the
digest-pinned `agentdev-devcontainer` image, with `uv sync`,
`pre-commit install-hooks`, and `pre-commit run` as separate steps so each is
timed. It checks the files the event's commit range changed, and every file when
the change moves a tool-version owner. The `ci` job waits for it.

**gitleaks scans history, not only the tree.** In CI and at pre-push it scans
every commit in the range; at commit time it scans the staged change.

**Super-Linter is gone.** `reformat.yml`, its formatter commits, the
Super-Linter version-sync script, and the `local-reformat` and
`sync-super-linter-tool-versions` catalog skills are removed. Renovate bumps
every tool through its version owner.

## Edge cases

- **A push to `main`.** `no-commit-to-branch` is skipped; it guards commits, not
  CI.
- **A `workflow_dispatch` run.** It checks every file and scans the full
  history.
- **A push that creates a ref** (a zero `before` SHA, as for a tag). It checks
  every file and scans the pushed commit.
- **A binary bump.** CI runs the new binary only once the image digest bump
  merges; that pull request changes a tool-version owner, so it checks every
  file.
- **Hooks bypassed locally.** A commit made with `--no-verify` or without the
  hooks installed is caught by the CI job.

## Open questions

None — every design question this feature raised is settled.
