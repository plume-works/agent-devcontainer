---
type: adr
stage: accepted
description: The setup-python-venv action provisions the project environment with uv sync --locked and does not activate it, so each step uses it through uv run.
---

# CI provisions the Python environment and never activates it

CI and the Dev Container provision the environment in different ways. Both use
it only through `uv run`, so a step runs the same way in both. For this reason,
the `setup-python-venv` action runs `uv sync --locked` and does not put the
environment on `PATH`.

## Considered Options

- Activate a virtualenv through `VIRTUAL_ENV` and `GITHUB_PATH`. Rejected: a
  step could then run a tool without `uv run`, which is different from the Dev
  Container.
- `uv sync --frozen`. Rejected: it does not make sure that `uv.lock` is current.
  A later `uv run` can then install a dependency that `uv.lock` does not have,
  in the middle of a job.

## Consequences

- uv creates the environment, so the action caches the uv package cache and not
  the environment directory.
- `UV_PYTHON_PREFERENCE=only-system` makes uv use the interpreter that
  `actions/setup-python` installed.
