---
type: feature
stage: implemented
description: Reach the Python environment exclusively through `uv run` — in the devcontainer, with no in-tree .venv symlink and a fixed out-of-tree path, and in CI, which provisions without activating.
generated:
  by: claude-code/opus-5
  at: 2026-08-15T00:00:00Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/scripts/uv-sync.sh
- resource: .agents/plugins/agentdev/bin/python-lint-check.sh
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

The environment lives at the fixed path `/uv/venvs/ws-project` and is reached
only through `uv run`. Consumers split in two:

- **Anything expressible as a command** runs through `uv run` — the lint script,
  the documented ruff invocations, the skills that described the old layout.
- **The four VS Code settings that need a filesystem path** —
  `python.defaultInterpreterPath` and the three `ansible.*` paths — carry the
  absolute path instead.

The path is a constant rather than a template because the `agentdev-uv` volume
is declared in `devcontainer.json` `mounts` rather than pinned to a literal name
in Compose, making it Compose-project-scoped: one `/uv` per devcontainer
instance, with nothing to disambiguate. See
[uv environment location](../architecture/uv-environment-location.md) for why
the environment stays out of tree at all — cache and environment must share a
filesystem for uv to hardlink instead of copy.

`uv-sync.sh` keeps a narrow migration cleanup: it removes `$workspace/.venv`
only when it is a symlink *and* its target matches the prefix earlier revisions
created, so existing containers shed the stale link on the next postAttach
without a rebuild, and a real or deliberately-placed `.venv` is never touched.

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

- **Host and CI checkouts still produce a real `.venv`.** `.gitignore`,
  `.dockerignore`, `search.exclude`, and the `shellcheck-fix.sh` prune all keep
  their `.venv` entries. `.github/actions/setup-python-venv/action.yml` lets uv
  create one in-tree, since `UV_PROJECT_ENVIRONMENT` is unset on a runner; it is
  never referenced by name and dies with the runner.
- **The lint script ships in a portable plugin.** A bare `uv run` would convert
  its fallback into a hard failure outside a uv project. It resolves in three
  tiers instead — `uv run --no-sync --project` → an in-tree `.venv/bin/ruff` →
  ruff on PATH. `--no-sync` is what keeps a *check* from installing packages
  when a developer's `pyproject.toml` is mid-edit.
- **`find_up` survives without its only in-repo caller.** `venv_activate` is
  gone, since `find_up .venv` can no longer succeed, but `find_up` itself stays:
  the fish README advertises it as a standalone interactive helper, so grep
  cannot see its real usage.
