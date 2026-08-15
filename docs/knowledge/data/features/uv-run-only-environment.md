---
type: feature
stage: implemented
description: Reach the devcontainer's Python environment exclusively through `uv run`, with no in-tree .venv symlink and a fixed out-of-tree path.
generated:
  by: claude-code/opus-5
  at: 2026-08-15T00:00:00Z
sources:
- .devcontainer/devcontainer.json
- .devcontainer/scripts/uv-sync.sh
- .agents/plugins/agentdev/bin/python-lint-check.sh
---

# uv-run-only environment

## Purpose

The repository's stated convention, in `AGENTS.md` and throughout `README.md`,
is to run project commands through `uv run`. An in-tree `.venv` symlink,
recreated on every postCreate and postAttach as a compatibility shim, was the
one affordance contradicting it — a second way to reach the environment that
tooling could quietly prefer.

Nothing was broken: `uv run` resolved the symlink without complaint. This is a
simplification, judged on that basis rather than as a bug fix.

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

## Edge cases

- **Host and CI checkouts still produce a real `.venv`.** `.gitignore`,
  `.dockerignore`, `search.exclude`, and the `shellcheck-fix.sh` prune all keep
  their `.venv` entries. `.github/actions/setup-python-venv/action.yml` builds
  its own in-tree environment and is unaffected.
- **The lint script ships in a portable plugin.** A bare `uv run` would convert
  its PATH fallback into a hard failure outside a uv project. It resolves in
  three tiers instead — `uv run --project` → ruff on PATH → `uv tool run ruff` —
  with PATH ahead of `uv tool run` so the common case never pays a network
  fetch.
- **`find_up` survives without its only in-repo caller.** `venv_activate` is
  gone, since `find_up .venv` can no longer succeed, but `find_up` itself stays:
  the fish README advertises it as a standalone interactive helper, so grep
  cannot see its real usage.
