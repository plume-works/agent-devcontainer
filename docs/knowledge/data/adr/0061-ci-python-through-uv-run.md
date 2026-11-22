---
type: adr
stage: accepted
---

# CI provisions the Python environment and never activates it

CI and the Dev Container provision the environment in different ways, an
ephemeral runner in CI and a persistent volume in the Dev Container. Both reach
it only through `uv run`, so a step runs the same way in both. For this reason,
the `setup-python-venv` action runs `uv sync --locked` and does not put the
environment on `PATH`.

## Considered Options

- Activate a hand-made virtualenv through `VIRTUAL_ENV` and `GITHUB_PATH`.
  Rejected: a step could then run a tool without `uv run`, unlike the Dev
  Container.
- `uv sync --frozen`. Rejected: it skips the check that `uv.lock` is current, so
  a later bare `uv run` would install a dependency missing from `uv.lock` in the
  middle of a job.
