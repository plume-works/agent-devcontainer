## Why

The repository provisions its Python environment into a Docker volume via
`UV_PROJECT_ENVIRONMENT`, then symlinks `.venv` at the workspace root back to it
"for tooling that expects the conventional in-tree path". No such generic tooling
exists: the symlink serves four VS Code settings that already know the real path,
one fish convenience function, and one lint script. In exchange it introduces a
second spelling for the same directory, which surfaces as a `VIRTUAL_ENV` /
`UV_PROJECT_ENVIRONMENT` mismatch, and it turns every pre-existing worktree into a
stale-toolchain trap whenever the target path changes.

CI compounds this by carrying two provisioning styles for one repository:
`ci.yml` runs `uv sync` + `uv run` inside the devcontainer, while
`.github/actions/setup-python-venv` builds a separate in-tree virtualenv, activates
it, and exports `VIRTUAL_ENV`/`GITHUB_PATH` so its callers can invoke bare
`pytest` and `validate_agent_files`.

## What Changes

### Devcontainer

- `UV_PROJECT_ENVIRONMENT` becomes the fixed literal `/uv/venvs/ws-project/`. The
  `agentdev-uv` volume has no explicit `name:` in `docker-compose.yml`, so Compose
  prefixes it per project and it is already isolated per worktree; the
  `${localWorkspaceFolderBasename}` segment was redundant namespacing inside an
  already-isolated volume.
- **BREAKING**: `.devcontainer/scripts/uv-sync.sh` stops creating the `.venv`
  symlink. It keeps removing a `.venv` _symlink_ so existing worktrees self-heal on
  the next sync, but no longer removes a real `.venv` directory, which a consuming
  project may legitimately own.
- The four VS Code settings that referenced `.venv` point at
  `/uv/venvs/ws-project/...` instead. They become substitution-free literals, so
  they no longer depend on `${workspaceFolder}` or the editor's working directory.

### CI

- **BREAKING**: `.github/actions/setup-python-venv` stops exporting `VIRTUAL_ENV`
  and `GITHUB_PATH`. Callers must invoke project tools through `uv run`. The action
  keeps its name — `uv sync` still creates an in-tree `.venv` on a runner — but its
  contract changes from "hands you an activated environment" to "provisions Python,
  uv, and a synced project environment".
- Python provisioning stays with `actions/setup-python`. `UV_PYTHON_PREFERENCE:
only-system` is added so uv binds to that interpreter instead of resolving or
  downloading its own, making GitHub Actions the single provisioner by enforcement
  rather than by coincidence.
- Caching moves from the `.venv` directory to uv's package cache via `setup-uv`'s
  `enable-cache`.
- Provisioning syncs with `--locked` rather than `--frozen`, so lockfile drift
  fails there. `--frozen` skips the currency check entirely and lets drift through.
- `validate-agent-files.yml` invokes its three steps through `uv run`.

### Repository tooling

- **BREAKING**: `python-lint-check.sh` resolves ruff through `uv run --no-sync`
  first, then falls back to an in-tree `.venv` and to `PATH`. Without this the
  script hard-fails in the devcontainer: ruff is not on `PATH` in the image, so
  removing the symlink removes its only source of ruff.
- **BREAKING**: the `venv_activate` fish helper is removed. `find_up` is retained
  as an unrelated general-purpose utility.

## Capabilities

### New Capabilities

- `python-environment`: where the project's Python environment lives, how project
  tools are invoked, and what the CI provisioning action guarantees to its callers.

### Modified Capabilities

None — `openspec/specs/` currently has no capabilities.

## Impact

Affected code:

- `.devcontainer/devcontainer.json` — `UV_PROJECT_ENVIRONMENT` and four VS Code settings
- `.devcontainer/scripts/uv-sync.sh` — symlink creation removed, removal narrowed
- `.github/actions/setup-python-venv/action.yml` — activation and PATH export removed
- `.github/workflows/validate-agent-files.yml` — three steps move to `uv run`
- `.github/workflows/ci.yml` — sync flags aligned; the "checked before `uv sync`"
  ordering note becomes obsolete once no step activates an environment
- `.agents/plugins/agentdev/bin/python-lint-check.sh` — ruff resolution order
- `ansible/roles/fish_setup/templates/dev.fish.j2` — `venv_activate` removed

Documentation asserting the old model:

- `docs/knowledge/data/architecture/template-boundary.md` — the action's consumer contract
- `ansible/roles/fish_setup/README.md` — lists the removed helper
- `.agents/plugins/agentdev/skills/microvm-sandbox/SKILL.md`
- `.agents/plugins/agentdev/skills/python-format-lint/SKILL.md`

Not affected:

- pre-commit — every hook provisions its own environment except `zizmor` (on `PATH`)
  and `validate-agent-files` (already `uv run`).
- `reformat.yml`, `validate-knowledge-base.yml`, `primary-checks.yml`,
  `delete-old-containers.yml` — no Python. Super-Linter runs ruff inside its own
  image; `validate-super-linter-tool-versions.sh` is pure bash.
- `.gitignore`, `.dockerignore`, `search.exclude`, and the shellcheck/Super-Linter
  `.venv` exclusions are retained; they still serve non-devcontainer checkouts.
