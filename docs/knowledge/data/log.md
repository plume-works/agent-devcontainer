# Project Update Log

The history of this workspace, newest first. The `ship` skill appends a dated
group on every release; any skill that creates or retires a document adds a line
to the current day's group.

## 2026-08-15

- **Creation**: [Finish uv-run-only in CI](plans/20260815-uv-run-in-ci.md) — all
  nine tasks done, verified green in CI (PR #61). CI stops activating the
  environment, syncs with `--locked` so lockfile drift fails at provisioning,
  and pins uv to the `actions/setup-python` interpreter; `python-lint-check.sh`
  no longer installs as a side effect of a check. Harvested from the parallel
  `no-venv-openspec` branch (PR #60); two of its changes declined with reasoning
  recorded.
- **Update**: [Drop the .venv symlink](plans/20260814-drop-venv-symlink.md) done
  — the in-tree symlink is gone and every consumer reaches the environment
  through `uv run` or the fixed `/uv/venvs/ws-project` path.
- **Creation**: [uv-run-only environment](features/uv-run-only-environment.md)
  implemented, recorded in [unreleased](releases/unreleased.md).
- **Creation**: Proposed
  [Verification in the main loop](features/verification-in-the-main-loop.md) —
  ship's step 1 names the verify skill without invoking it, so verification at
  ship time is discretionary rather than compelled.

## 2026-08-01

- **Initialization**: Created the project workspace — [product](product.md) as
  the foundation, with [plans](plans.md), [backlog](backlog.md),
  [milestones](milestone.md), and [someday](someday.md) for work, and
  [features](features.md), [bugs](bugs.md), and [releases](releases.md) for
  delivery.
- **Creation**: Seeded the reference side — [spec](spec.md),
  [codebase](codebase.md), [architecture](architecture.md), and
  [concept](concept.md) — with example documents showing the shape of each type.
