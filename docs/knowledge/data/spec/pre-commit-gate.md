---
type: spec
description: The pre-commit hooks are the CI lint gate — the commit range they check, when every file is checked, and how gitleaks scans a range.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T12:00:00Z
sources:
- resource: .github/workflows/primary-checks.yml
- resource: scripts/pre-commit-ci-range.py
- resource: .pre-commit-config.yaml
- resource: devcontainer-compose-pins.yml
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
- **THEN** the job checks the files changed between `before` and `after` and
  skips `no-commit-to-branch`.

#### Scenario: a manual run

- **WHEN** Primary checks is started by `workflow_dispatch`
- **THEN** the job checks every file.

### Requirement: a tool-version change is checked against every file

When the commit range changes `uv.lock`, `pyproject.toml`,
`.pre-commit-config.yaml`, `ansible/roles/dev_tools/defaults/main.yml`, or
`devcontainer-compose-pins.yml`, the pre-commit job SHALL run every hook on
every file.

#### Scenario: Renovate bumps ruff

- **WHEN** a pull request moves ruff's version in `uv.lock`
- **THEN** the job runs every hook on every file, and fails if the new version
  would rewrite any of them.

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

#### Scenario: a push that creates a ref

- **WHEN** a push has an all-zero `before` SHA
- **THEN** the job checks every file and gitleaks scans the pushed commit.
