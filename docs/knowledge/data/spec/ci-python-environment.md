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
