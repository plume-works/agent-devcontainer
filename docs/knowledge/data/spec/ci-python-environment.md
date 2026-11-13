---
type: spec
description: How a GitHub Actions job outside the development image gets its Python environment — provisioned and synced against the lock file by one composite action, never activated, and reached only through uv run.
sources:
- resource: .github/actions/setup-python-venv/action.yml
- resource: .github/workflows/validate-agent-files.yml
- resource: .github/workflows/validate-knowledge-base.yml
- resource: .github/workflows/ci.yml
- resource: .github/renovate.json
---

# CI Python environment

## Purpose

Defines how a workflow job that runs on a bare GitHub runner, rather than inside
the `agentdev-devcontainer` image, provisions the project's Python environment
and invokes its tools, so CI follows the same `uv run` contract as the Dev
Container.

## Requirements

### Requirement: one action provisions the environment and activates nothing

A runner job that needs the project's Python environment SHALL get it from
`.github/actions/setup-python-venv`, which SHALL install Python with
`actions/setup-python`, install uv with `astral-sh/setup-uv` at a pinned version
with uv's package cache enabled, and run
`uv sync --locked --all-groups --all-extras` with
`UV_PYTHON_PREFERENCE=only-system`. The action SHALL NOT create a virtualenv
itself, export `VIRTUAL_ENV`, add the environment to `GITHUB_PATH`, or cache the
environment directory.

#### Scenario: the lock file is out of date

- **WHEN** `pyproject.toml` declares a dependency `uv.lock` does not hold
- **THEN** the sync step fails, and no later step installs the dependency

#### Scenario: the runner has another Python on PATH

- **WHEN** the runner carries a Python besides the one `actions/setup-python`
  installed
- **THEN** uv syncs against the interpreter `actions/setup-python` installed,
  and downloads none of its own

### Requirement: CI invokes Python tools through uv run

Every step that runs a project Python tool after `setup-python-venv` SHALL
invoke it as `uv run <tool>`. The in-tree `.venv` uv creates on a runner SHALL
NOT be referenced by name.

#### Scenario: agent files are validated

- **WHEN** `validate-agent-files.yml` runs its tests and the validator
- **THEN** each runs as `uv run pytest …` or `uv run validate_agent_files …`
  against the environment the action synced

## Rationale

### Provision, never activate

CI and the Dev Container provision differently — an ephemeral runner here, a
persistent volume there — but both reach the environment only through `uv run`,
so a step runs the same way in either. uv owns environment creation, so caching
its package cache stays correct across interpreter and lock-file changes where a
cached environment directory would not. `--locked` makes lock-file drift fail at
provisioning; `only-system` makes the interpreter choice explicit rather than a
side effect of what is on `PATH`.

Rejected:

- **Activating a hand-made virtualenv** through `VIRTUAL_ENV` and `GITHUB_PATH`.
  A step would then run tools without `uv run`, unlike the Dev Container.
- **`uv sync --frozen`.** It skips the lock-file currency check, so a dependency
  missing from `uv.lock` would be installed later by a bare `uv run` mid-job.

### The action keeps the name `setup-python-venv`

`uv sync` still creates an in-tree `.venv` on a runner, so the name stays
accurate, and the action's path is template surface consumers customize and call
from their own workflows.

Rejected:

- **Renaming the action to match the `uv run` contract.** It churns every
  consumer's workflows and still leaves the contract to be documented.
