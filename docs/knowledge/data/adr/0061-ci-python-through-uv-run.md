---
type: adr
stage: accepted
description: The setup-python-venv action makes the project environment with uv sync --locked and does not activate it, so each step uses it through uv run.
---

# CI makes the Python environment and never activates it

CI and the Dev Container make the environment in different ways. Both use it
only through `uv run`, so a step runs the same way in both. For this reason, the
`setup-python-venv` action runs `uv sync --locked` and does not put the
environment on `PATH`.

## Considered Options

- Activate a virtualenv through `VIRTUAL_ENV` and `GITHUB_PATH`. Rejected: a
  step can then run a tool without `uv run`, which is different from the Dev
  Container.
- `uv sync --frozen`. Rejected: it does not make sure that `uv.lock` is current.
  A later `uv run` can then install a dependency that `uv.lock` does not have,
  in the middle of a job.
