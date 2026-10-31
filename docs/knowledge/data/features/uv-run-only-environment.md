---
type: feature
stage: implemented
description: Reach the Python environment exclusively through `uv run` — in the devcontainer, where each checkout owns an in-tree .venv and no symlink points elsewhere, and in CI, which provisions without activating.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T21:10:00Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: .agents/plugins/agentdev/bin/python_lint_check.py
- resource: .github/actions/setup-python-venv/action.yml
- resource: .github/workflows/validate-agent-files.yml
---

# uv-run-only environment

## Purpose

The repository's stated convention, in `AGENTS.md` and throughout `README.md`,
is to run project commands through `uv run`. Two affordances contradicted it,
one on each side of the repository.

In the devcontainer, an in-tree `.venv` symlink recreated on every postCreate
and postAttach as a compatibility shim — a second way to reach the environment
that tooling could quietly prefer. Nothing was broken there: `uv run` resolved
the symlink without complaint, so removing it is a simplification rather than a
bug fix.

In CI, the setup action built its own virtualenv, activated it, and exported
`VIRTUAL_ENV`/`GITHUB_PATH` so callers could invoke bare tools. Removing that is
not merely tidying: it came with `uv sync --frozen`, which skips the lockfile
currency check entirely, so a dependency present in `pyproject.toml` but absent
from `uv.lock` passed provisioning and was installed mid-job by a later
`uv run`. `--locked` moves that failure to provisioning, where it is legible.

## Behaviour

Each checkout's environment is its own in-tree `.venv`, reached only through
`uv run`. Consumers split in two:

- **Anything expressible as a command** runs through `uv run` — the lint script,
  the documented ruff invocations, the skills that described the old layout.
- **The four VS Code settings that need a filesystem path** —
  `python.defaultInterpreterPath` and the three `ansible.*` paths — name
  `${workspaceFolder}/.venv/bin/...`.

See [uv environment location](../architecture/uv-environment-location.md) for
why each checkout owns its environment rather than sharing one on the `/uv`
volume.

`agentdev-runtime project sync` keeps a narrow migration cleanup: it removes
`$workspace/.venv` only when it is a symlink *and* its target is under
`/uv/venvs/`, so a checkout sheds a link to the retired shared environment on
the next attach, and a real or deliberately-placed `.venv` is never touched.

CI follows the same invocation contract, by a different mechanism. The two
provisioning styles stay distinct — a persistent volume in the devcontainer, an
ephemeral runner in Actions — but neither activates anything:

- `.github/actions/setup-python-venv` provisions Python, uv, and a synced
  environment, and stops there. It no longer creates a virtualenv by hand,
  exports `VIRTUAL_ENV`/`GITHUB_PATH`, or caches the environment directory;
  `setup-uv`'s own package cache replaces that last one.
- Provisioning syncs with `--locked`, so lockfile drift fails there rather than
  being installed mid-job by a later `uv run`. `--frozen` skips the currency
  check entirely and cannot serve this role.
- `UV_PYTHON_PREFERENCE: only-system` binds uv to the interpreter
  `actions/setup-python` installed. Without it uv's default `managed` preference
  selects that interpreter only incidentally, by finding a matching system
  Python on `PATH`.
- Callers invoke tools through `uv run` — the three steps in
  `validate-agent-files.yml`, matching what `ci.yml` already did inside the
  container.

## Edge cases

- **Every checkout produces a real `.venv`.** `.gitignore`, `.dockerignore`,
  `search.exclude`, and the `shellcheck_fix.py` prune all keep their `.venv`
  entries. `.github/actions/setup-python-venv/action.yml` lets uv create one
  in-tree, since `UV_PROJECT_ENVIRONMENT` is unset on a runner; it is never
  referenced by name and dies with the runner.
- **The lint script ships in a portable plugin.** A bare `uv run` would convert
  its fallback into a hard failure outside a uv project. It resolves in three
  tiers instead — `uv run --no-sync --project` → an in-tree `.venv/bin/ruff` →
  ruff on PATH. `--no-sync` is what keeps a *check* from installing packages
  when a developer's `pyproject.toml` is mid-edit.
- **`find_up` survives without its only in-repo caller.** `venv_activate` is
  gone, since `find_up .venv` can no longer succeed, but `find_up` itself stays:
  the fish README advertises it as a standalone interactive helper, so grep
  cannot see its real usage.

## Open questions

None — every design question this feature raised is settled.

## References

- Plan: [Drop the .venv symlink](../plans/20260814-drop-venv-symlink.md)
