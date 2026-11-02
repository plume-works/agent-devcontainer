---
type: architecture
description: Every formatter has exactly one owner, every hook tool has exactly one version owner that Renovate bumps, and CI gates on the same pre-commit hooks inside the digest-pinned devcontainer image, so local runs cannot disagree with CI.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T04:31:05Z
sources:
- resource: .pre-commit-config.yaml
- resource: .github/workflows/primary-checks.yml
- resource: scripts/pre-commit-ci-range.py
- resource: pyproject.toml
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: https://github.com/gitleaks/gitleaks-action
- resource: https://github.com/Dr-QP/Dr.QP/pull/440
- resource: https://github.com/Dr-QP/Dr.QP/pull/447
---

# Formatter ownership

## Decision

Each formatter and linter has **one owner**: a pre-commit hook. The hooks run on
every commit, and the `pre-commit` job in Primary checks runs the same hooks as
the CI gate, inside the `agentdev-devcontainer` image pinned by the same tag and
digest as `devcontainer-compose-pins.yml`. `CI/CD` needs that job, so a failing
or rewriting hook blocks the merge through `CI/CD / CI finished`.

Every hook tool has **one version owner**, and Renovate bumps each through it:

| Owner                      | Tools                                                                        | How the hook runs it                                           |
| -------------------------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `uv.lock` (`dev` group)    | ruff, ruff-format, ansible-lint, clang-format, the `pre-commit-hooks` fixers | `language: system`, `entry: uv run <tool>`                     |
| `dev_tools_pinned_tools`   | hadolint, shellcheck, gitleaks, actionlint, zizmor, iwe                      | `language: system` image binary, under a `# renovate:` comment |
| `bunx <package>@<version>` | prettier, the Renovate config validator                                      | `language: system`                                             |

No hook names a remote repository, so `pre-commit install-hooks` builds no
environment and no tool has a second copy beside its owner.

## Why single ownership

Two tools that both claim a file rewrite each other's output. The result is not
a merge conflict but a churn: one formatter rewrites, the other reverts, and the
diff depends on which ran last. Naming one owner per language removes the
ambiguity.

## Why the gate is the hooks themselves

Same tool, different version, different output — neither side misconfigured, and
no local signal that they disagree. When CI runs the very hooks a commit ran,
against tools from the same owners, there is no second version to drift from,
and nothing to keep in parity by hand.

A version bump still changes output underneath unchanged files. The job checks
only the files its commit range changed, except when the range touches a
tool-version owner (`uv.lock`, `pyproject.toml`, `.pre-commit-config.yaml`,
`ansible/roles/dev_tools/defaults/main.yml`, `devcontainer-compose-pins.yml`):
then it checks every file, so a formatter bump fails at the pull request that
made it.

## Secret scanning over commit ranges

The gitleaks hook scans history, not only the tree, in one of three modes:
`GITLEAKS_LOG_OPTS` when set (CI sets it for every event), the
`PRE_COMMIT_FROM_REF..PRE_COMMIT_TO_REF` range pre-commit exports at pre-push,
and the staged change otherwise. A range scan reads every commit's patch, so a
secret added and removed inside a pull request is still found. A push that
creates a ref scans its pushed commit; a manual run scans all history.

## Rejected alternatives

- **Super-Linter as the CI gate.** Its image duplicated every hook, pinned the
  tool versions, and made every bump a manual sync that Renovate could not do.
- **`gitleaks/gitleaks-action`.** It needs a licence key for an organization,
  lists only the first 30 commits of a pull request, and downloads its own
  gitleaks beside the pinned one.
- **Running the job on the image the pull request builds.** It puts lint behind
  the full image build; the pinned image already carries every binary hook.
- **Remote hook repositories.** Each installs its own copy of a tool beside
  `uv.lock` or the image, which is the drift this decision removes.

## Consequences

- A hook tool moves only through its owner; a Renovate pull request for it runs
  every hook on every file before it can merge.
- A tool a hook runs as an image binary reaches CI only after a digest bump of
  the pinned image, so adding one is two pull requests: the provisioning, then
  the hook.
- Hooks outside the devcontainer need the same binaries on `PATH`.
