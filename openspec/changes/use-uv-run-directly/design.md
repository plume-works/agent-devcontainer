## Context

See proposal.md — Why. The constraints that shape the approach, all verified in
the running devcontainer (uv 0.12.4):

- **The `/uv` volume is already per-worktree.** `docker-compose.yml` declares an
  explicit `name:` only for `agentdev-agents-auth`; `agentdev-uv` gets Compose's
  default per-project prefix. `/uv/venvs/` in this worktree contains exactly one
  entry.
- **No Python tooling is on `PATH` in the image.** `ruff`, `ansible-lint`,
  `pytest`, and `actionlint` all resolve to nothing; only `ansible`,
  `ansible-playbook`, `zizmor`, `shellcheck`, and `validate_agent_files` are
  present. So the symlink is `python-lint-check.sh`'s _only_ source of ruff, and
  removing it without changing that script is a hard failure, not a degradation.
- **uv warns on a `VIRTUAL_ENV` spelling mismatch.** With the symlink present uv
  resolves it and stays quiet; pointed at a path that no longer exists it prints
  `does not match the project environment path ... and will be ignored` on every
  invocation.
- **Both sides already run Python 3.12.** The container uses the image's system
  `/usr/bin/python3.12` (3.12.3) — uv has downloaded nothing, and
  `UV_PYTHON_INSTALL_DIR` is currently unused. CI's setup action defaults to
  `'3.12'`.
- **`.venv` still exists in CI.** On a plain runner `UV_PROJECT_ENVIRONMENT` is
  unset, so `uv sync` creates an in-tree `.venv`. Removing the symlink is a
  devcontainer-scoped change; it does not and cannot mean "`.venv` never exists".

## Goals / Non-Goals

**Goals:**

- One way to reach the project environment, in the devcontainer and in CI.
- No environment activation anywhere: no `source activate`, no `VIRTUAL_ENV`
  export, no `PATH` prepending.
- Configuration that keeps working for a consuming project that does own an
  in-tree `.venv`.

**Non-Goals:**

- Eliminating `.venv` from CI runners. It is uv's default location there, is
  never referenced by name, and is discarded with the runner.
- Unifying the devcontainer and CI provisioning mechanisms. They stay different —
  a persistent volume versus an ephemeral runner — and only the _invocation_
  contract is unified.
- Changing which Python version the project uses.

## Decisions

### Fixed literal `/uv/venvs/ws-project/` over a basename-derived path

The volume is already isolated per Compose project, so the basename segment adds
no isolation. Removing it makes the four editor settings substitution-free
literals, which is what lets them be copy-pasteable into a consuming project.

_Alternative considered:_ keep `${localWorkspaceFolderBasename}`. Rejected — it
forces every consumer of the path to reproduce the same substitution, and it was
the reason the editor settings could not simply name the real path.

_Alternative considered:_ `${containerEnv:UV_PROJECT_ENVIRONMENT}` in the editor
settings, to avoid repeating the literal. Rejected — it is not established that
substitution reaches inside `customizations.vscode.settings`, and the value
carries a trailing slash that would have to be handled. A repeated literal is
duller and certainly correct.

### Remove the symlink, keep a narrowed removal

Dropping only `ln -s` while retaining removal makes existing worktrees self-heal:
a leftover symlink otherwise points at a path that is no longer synced, which is
worse than a missing environment because a `.venv`-preferring tool would silently
use a stale toolchain. Narrowing the removal to symlinks only (never a directory)
keeps the script safe to run in a consuming project.

### `uv run --no-sync` at call sites, `uv sync --frozen` at provisioning

Provision once, loudly; then guarantee no call site mutates the environment.
Without `--no-sync`, each `uv run` re-resolves and may re-sync, which converts a
lockfile problem into a confusing failure inside an unrelated test step. This
applies identically to `python-lint-check.sh` — a _check_ script must not install
packages as a side effect.

### `python-lint-check.sh` keeps a fallback chain

Order: `uv run --no-sync` → in-tree `.venv` → `PATH`. The script ships to
consuming projects as part of the agentdev catalog, and some of those legitimately
have an in-tree environment or a system ruff. Making it uv-only would trade one
portability break for another.

### Python provisioning stays with `actions/setup-python`, enforced

Keeping the setup action is only meaningful if uv is prevented from provisioning
its own interpreter. uv's default preference is `managed`, so today it selects the
CI-installed Python incidentally — because it happens to be a matching system
interpreter on `PATH`. `UV_PYTHON_PREFERENCE: only-system` turns that coincidence
into an invariant and applies to every uv call in the job.

_Alternative considered:_ `--python ${{ steps.setup-python.outputs.python-path }}`
on the sync step. Equivalent for that one step, but it does not constrain later
`uv run` calls.

_Alternative considered:_ drop `actions/setup-python` and let uv provision. Fewer
steps, but it moves the version pin out of CI configuration and into uv's
resolution of `requires-python = ">=3.12"`, which floats upward.

### The provisioning action keeps its name

`uv sync` still creates an in-tree `.venv` on a runner, so `setup-python-venv`
remains literally accurate, and the path is classified consumer-facing in
`template-boundary.md`. What actually changes is its _contract_ — it no longer
hands back an activated environment — which must be documented whether or not the
directory is renamed. Renaming would add template-surface churn without removing
that documentation burden.

### Cache the package cache, not the environment directory

The current key caches the `.venv` directory, which is why `python -m venv` exists
as a step at all — to pre-create the restore target. With uv owning creation,
caching uv's package cache is the idiomatic equivalent and is resilient to
interpreter and lockfile churn. This reverses the action's own
`we just cache the venv-dir directly` comment, which should be removed with it.

## Risks / Trade-offs

- **A stale `.venv` symlink in a worktree that is never re-synced** → the narrowed
  removal in the sync script clears it on the next sync; the sync runs from
  `postCreateCommand`, so any rebuild heals it.
- **Cold CI runs get slower.** The package cache still requires uv to build the
  environment, where a restored `.venv` was ready to use → accepted; correctness
  across interpreter and lockfile changes is worth more than the delta on a
  workflow with three steps.
- **A consuming project that copied the editor settings inherits
  `/uv/venvs/ws-project/`,** which is only correct inside this devcontainer → the
  settings ship as part of `devcontainer.json`, which a consumer takes wholesale
  along with the matching `UV_PROJECT_ENVIRONMENT`; the two move together.
- **`only-system` fails the job outright if the CI setup action ever stops placing
  the interpreter on `PATH`** → that is the intended failure mode; a silent
  fallback to a downloaded interpreter is what this decision exists to prevent.
- **Contributors relying on `venv_activate` lose it** → they invoke tools through
  `uv run` from anywhere in the tree, which needs no activation and no helper.

## Migration Plan

1. Land the devcontainer and sync-script changes together, so the first sync after
   the merge both stops creating the symlink and removes the existing one.
2. Land the `python-lint-check.sh` change in the same commit or earlier — it is a
   hard dependency of the devcontainer change, not a follow-up.
3. CI changes are independent of the devcontainer changes and can land separately;
   the action and its single caller must change together.
4. Rollback is a revert. No persisted state migrates: the environment directory
   itself is unchanged in content, only in path, and is rebuilt by a sync.

Contributors with existing worktrees need no manual step. A rebuild, or any run of
the sync script, clears the stale symlink.
