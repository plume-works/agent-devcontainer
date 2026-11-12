---
type: spec
description: The pre-commit hooks are the CI lint gate and each hook tool has one version owner — the commit range they check, when every file is checked, and how gitleaks scans a range.
sources:
- resource: .github/workflows/primary-checks.yml
- resource: .github/workflows/ci.yml
- resource: scripts/pre-commit-ci-range.py
- resource: scripts/ci_runs.py
- resource: .pre-commit-config.yaml
- resource: devcontainer-compose-pins.yml
- resource: scripts/check-ship-records.py
- resource: pyproject.toml
- resource: ansible/roles/dev_tools/defaults/main.yml
---

# pre-commit gate

## Requirements

### Requirement: CI runs the pre-commit hooks as the lint gate

Primary checks SHALL run `pre-commit run` inside the `agentdev-devcontainer`
image pinned by the same tag and digest as `devcontainer-compose-pins.yml`, over
the files the event's commit range changed, and the `ci` job SHALL start only
after it succeeds.

#### Scenario: a pull request changes source files

- **WHEN** a pull request changes files a hook matches
- **THEN** the pre-commit job runs those hooks on the files changed between the
  base and head commits, and fails when any hook fails or rewrites a file.

#### Scenario: a push to main

- **WHEN** commits are pushed to `main`
- **THEN** the job checks the files changed between the head commit of Primary
  checks' last successful push run on `main` and `after`, and skips
  `no-commit-to-branch`.

#### Scenario: the last successful run cannot be found

- **WHEN** a push to `main` finds no successful Primary checks push run, or the
  lookup fails
- **THEN** the job warns and checks the files changed between `before` and
  `after`.

#### Scenario: a manual run

- **WHEN** Primary checks is started by `workflow_dispatch`
- **THEN** the job checks every file.

### Requirement: every hook runs a tool from one version owner

Every hook in `.pre-commit-config.yaml` SHALL be a `repo: local` hook with
`language: system`, and SHALL run its tool from one version owner:
`uv run <tool>` for a tool in `pyproject.toml`'s `dev` dependency group (ruff,
ruff-format, ansible-lint, clang-format, the `pre-commit-hooks` fixers), an
image binary pinned in `dev_tools_pinned_tools` under a `# renovate:` comment
(hadolint, shellcheck, gitleaks, actionlint, zizmor, iwe), or
`bunx <package>@<version>` (prettier, the Renovate config validator). No hook
SHALL name a remote repository.

#### Scenario: hooks are installed

- **WHEN** `pre-commit install-hooks` runs
- **THEN** it builds no hook environment, and each hook runs the copy of its
  tool that its owner pins

#### Scenario: a hook runs outside the devcontainer

- **WHEN** a hook whose tool is an image binary runs on a host
- **THEN** it runs whatever binary of that name is on `PATH`

### Requirement: a tool-version change is checked against every file

When the commit range changes `uv.lock`, `pyproject.toml`,
`.pre-commit-config.yaml`, `ansible/roles/dev_tools/defaults/main.yml`, or
`devcontainer-compose-pins.yml`, the pre-commit job SHALL run every hook on
every file.

#### Scenario: Renovate bumps ruff

- **WHEN** a pull request moves ruff's version in `uv.lock`
- **THEN** the job runs every hook on every file, and fails if the new version
  would rewrite any of them.

### Requirement: the rebuilt image passes every hook before promotion

When CI builds a candidate `agentdev-devcontainer` image, it SHALL run every
hook on every file inside that candidate, and SHALL NOT promote the image family
unless the run passes.

#### Scenario: Renovate bumps a tool the image provisions

- **WHEN** a pull request changes a version the image build installs, and the
  new version fails a hook on a file the pull request did not touch
- **THEN** the candidate pre-commit job fails, and no moving tag names the
  candidate.

#### Scenario: the image is not rebuilt

- **WHEN** the path filter skips the image build
- **THEN** only the pre-commit job in the pinned image runs.

### Requirement: gitleaks scans every commit in a range

The gitleaks hook SHALL scan each commit's patch in the range when one is given,
and the staged change otherwise.

#### Scenario: a secret added and removed inside a pull request

- **WHEN** one commit in a pull request adds a secret and a later commit removes
  it
- **THEN** the pre-commit job fails on the commit that added it.

#### Scenario: a push from a working copy

- **WHEN** `git push` runs the pre-push hooks
- **THEN** gitleaks scans every commit being pushed.

#### Scenario: a commit

- **WHEN** `git commit` runs the pre-commit hooks
- **THEN** gitleaks scans the staged change.

#### Scenario: a manual run scans all history

- **WHEN** Primary checks is started by `workflow_dispatch`
- **THEN** gitleaks scans every commit in the repository's history.

#### Scenario: a push that creates a ref

- **WHEN** a push has an all-zero `before` SHA
- **THEN** the job checks every file and gitleaks scans the pushed commit.

### Requirement: Ship records are gated in pre-commit

A pre-commit hook SHALL run a checker CLI over every bug and plan document
pre-commit passes it, at commit time, over a commit range, and with
`--all-files`. The CLI SHALL fail a bug at `stage: done` that has no `## Fix`
heading, and a plan whose `## Ship review` section differs from the fixed
structure, and SHALL report every violation with `path:line`.

#### Scenario: a done bug has no Fix

- **WHEN** a commit stages a bug document at `stage: done` with no `## Fix`
- **THEN** the hook fails and names the document.

#### Scenario: an open bug has no Fix

- **WHEN** a bug document at `stage: pending` or `stage: planned` has no
  `## Fix`
- **THEN** the hook passes it.

#### Scenario: a Ship review is malformed

- **WHEN** a plan's `## Ship review` misses an item, reorders the items, leaves
  one unticked, or marks the Verify, plan-stage, or hub-edit item `N/A`
- **THEN** the hook fails and names the line.

#### Scenario: CI checks every file

- **WHEN** CI runs pre-commit with `--all-files`
- **THEN** the hook checks every bug and plan document.

## Rationale

### The pre-commit hooks are the one owner of every formatter and the CI gate

Each formatter and linter has one owner, a pre-commit hook, and CI's gate is the
same hooks run inside the pinned `agentdev-devcontainer` image. Two tools that
both claim a file rewrite each other's output, so the diff depends on which ran
last; one owner per language removes that churn. When CI runs the very hooks a
commit ran, against tools from the same version owners, there is no second
version to drift from and nothing to keep in parity by hand. A version bump
still changes output under unchanged files, which is why a range touching a
version owner checks every file. The cost accepted: a tool a hook runs as an
image binary reaches CI only after a digest bump of the pinned image, so adding
one takes two pull requests, the provisioning and then the hook.

Rejected:

- **Super-Linter as the CI gate.** Its image duplicated every hook and pinned
  its own tool versions, so every bump was a manual sync Renovate could not do.
- **`gitleaks/gitleaks-action`.** It needs a licence key for an organization,
  lists only the first 30 commits of a pull request, and downloads its own
  gitleaks beside the pinned one.
- **Running the job on the image the pull request builds.** It puts lint behind
  the full image build, while the pinned image already carries every binary
  hook.
- **Remote hook repositories.** Each installs its own copy of a tool beside
  `uv.lock` or the image, which is the drift single ownership removes.
