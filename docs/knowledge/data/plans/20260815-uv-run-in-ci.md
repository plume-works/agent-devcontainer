---
type: plan
created: 2026-08-15
description: Finish the uv-run-only migration in CI — stop activating the environment, enforce the interpreter, and fail on lockfile drift at provisioning.
generated:
  by: claude-code/opus-5
  at: 2026-08-15T00:00:00Z
sources:
- .github/actions/setup-python-venv/action.yml
- .github/workflows/validate-agent-files.yml
- .github/workflows/ci.yml
- .agents/plugins/agentdev/bin/python-lint-check.sh
---

# Finish uv-run-only in CI

## Context

[Drop the .venv symlink](20260814-drop-venv-symlink.md) removed environment
activation from the devcontainer and routed every consumer through `uv run`. It
left CI alone. The result is a repository that states one convention and
practices two:

- `AGENTS.md` and
  [uv environment location](../architecture/uv-environment-location.md) say
  project commands run through `uv run`.
- `.github/actions/setup-python-venv` still builds an in-tree virtualenv,
  activates it, and exports `VIRTUAL_ENV` and `GITHUB_PATH` so its callers can
  invoke bare tools.
- `validate-agent-files.yml:70-76` duly calls bare `pytest` and bare
  `validate_agent_files`, which work *only* because of that activation.

A parallel branch (`no-venv-openspec`, PR #60) reached the same destination from
the other end — it rewrote CI and left richer analysis behind. This plan takes
the findings that survived review, and explicitly declines two that did not.

Three findings are worth stating up front, because they are the reason this is
more than a style cleanup:

**`--frozen` does not check lockfile currency.** The action syncs with
`uv sync --frozen`. `--frozen` skips the currency check entirely, so a
dependency added to `pyproject.toml` but never locked passes provisioning — and
is then silently installed by a later bare `uv run`, mid-job. `--locked` fails
at provisioning instead. Measured on uv 0.12.4 in the parallel branch's design
note: `--frozen` exits 0 with the dependency missing; `--locked` exits 1 with
``The lockfile at `uv.lock` needs to be updated``.

**Nothing pins CI to the interpreter `actions/setup-python` installed.** uv's
default `python-preference` is `managed`. It selects the CI interpreter today by
coincidence — that interpreter happens to be a matching system Python on `PATH`.
Keeping `actions/setup-python` is only meaningful if uv is prevented from
resolving or downloading its own, which `UV_PYTHON_PREFERENCE: only-system`
enforces.

**A check script must not install packages.** `python-lint-check.sh` resolves
ruff through `uv run` with no `--no-sync`. Nothing provisions before it and a
developer's `pyproject.toml` can legitimately be mid-edit, so a *check* can
mutate the environment as a side effect.

Verified against this branch while writing:
`.devcontainer/docker-compose.yml:108` pins a literal `name:` only for
`agentdev-agents-auth`, so the `agentdev-uv` volume is Compose-project-scoped
and the fixed `/uv/venvs/ws-project` path holds. `pyproject.toml` declares no
`[project.optional-dependencies]`, so `--all-extras` is a consistency flag
rather than a behavior change.

## Approach

Change the action's *contract*, then its single caller, in that order — they
must land together. Keep the action's name: `uv sync` still creates an in-tree
`.venv` on a runner, so `setup-python-venv` stays literally accurate, and the
path is classified consumer-facing in
[template boundary](../architecture/template-boundary.md). Renaming would add
template-surface churn without removing the documentation burden, since the
contract change has to be written down either way.

Two findings from the parallel branch are **rejected**, and the reasoning is
recorded here so it is not re-litigated:

- **Blunt `rm -f` of any `.venv` symlink** in `uv-sync.sh`. Commit `e1681bb`
  deliberately narrowed this to links whose target is under `/uv/venvs/` — the
  shape this repo created — reporting anything else and leaving it. The script
  ships to consuming projects through the agentdev catalog, where a developer's
  deliberate symlink is not ours to delete. Keep the narrow version.
- **A trailing slash on `UV_PROJECT_ENVIRONMENT`** (`/uv/venvs/ws-project/`).
  Cosmetic, and it introduces a second spelling of a path that four VS Code
  settings write without the slash. Keep it slashless.

Non-goals: eliminating `.venv` from CI runners — it is uv's default location
there, is never referenced by name, and dies with the runner. Unifying
devcontainer and CI *provisioning* — a persistent volume and an ephemeral runner
stay different; only the *invocation* contract is unified.

## Tasks

- [x] **1. Stop activating the environment in `setup-python-venv`.** Delete the
  `Restore venv cache`, `Create venv`, and `Activate venv` steps from
  `.github/actions/setup-python-venv/action.yml:26-45`, along with the
  `zizmor: ignore[github-env]` comment that only existed to permit the
  `VIRTUAL_ENV` export. Update `description:` to say the action provisions
  Python, uv, and a synced environment, and that callers must use `uv run`.
- [x] **2. Move caching from the environment to uv's package cache.** Set
  `enable-cache: true` on the `astral-sh/setup-uv` step and delete the
  `# we just cache the venv-dir directly` comment above it, which Task 1 makes
  false. With uv owning environment creation, caching its package cache is the
  idiomatic equivalent and survives interpreter and lockfile churn. Cold runs
  get slower — uv rebuilds where a restored `.venv` was ready — which is
  accepted for a three-step workflow.
- [x] **3. Sync with `--locked` and enforce the interpreter.** Replace
  `uv sync --frozen --active --all-groups --all-extras` with
  `uv sync --locked --all-groups --all-extras` (`--active` is meaningless once
  nothing is activated), and add `env: UV_PYTHON_PREFERENCE: only-system` to
  that step so every uv call in the job binds to the `actions/setup-python`
  interpreter. Note the intended failure mode: if the setup action ever stops
  putting the interpreter on `PATH`, the job fails outright rather than silently
  downloading one.
- [x] **4. Route `validate-agent-files.yml` through `uv run`.** Prefix the three
  steps at `.github/workflows/validate-agent-files.yml:70-76` — `pytest` ×2 and
  `validate_agent_files --recommend . --require-marketplace claude codex` — with
  `uv run`. Must land with Tasks 1–3; bare tools break the moment activation is
  gone.
- [x] **5. Align the in-container sync in `ci.yml`.** At
  `.github/workflows/ci.yml:272`, make it
  `uv sync --locked --all-groups --all-extras` to match Task 3. Then correct the
  comment at lines 265-267: it claims the `validate_agent_files` identity check
  must run *before* `uv sync` "so the project environment cannot mask a missing
  install". Nothing activates an environment any more, so the environment can no
  longer mask the image's copy — the ordering constraint it documents no longer
  exists, though the check itself stays.
- [x] **6. Make `python-lint-check.sh` non-mutating.** Add `--no-sync` to the
  `uv run` invocation in `.agents/plugins/agentdev/bin/python-lint-check.sh` so
  the check never installs as a side effect. Reorder the fallback chain to
  `uv run --no-sync` → in-tree `.venv/bin/ruff` → `PATH`: the script ships to
  consuming projects, some of which legitimately own an in-tree environment.
  Update the header comment to match. Note that call sites *other* than this one
  need no `--no-sync` — with `--locked` upstream from Task 3, `uv run`'s sync
  check is a no-op.
- [x] **7. Update the docs that describe CI provisioning.** Extend
  [uv environment location](../architecture/uv-environment-location.md) — its
  Consequences section currently says CI "builds their own in-tree environment",
  which stays true, but should record that CI no longer *activates* it. Add the
  CI half to [uv-run-only environment](../features/uv-run-only-environment.md).
- [x] **8. Verify.** Push and confirm `validate-agent-files.yml` and `ci.yml`
  both pass — CI is the only place these paths execute, so a green run is the
  test. Locally, check that `python-lint-check.sh` still resolves ruff in the
  devcontainer (where ruff is *not* on `PATH`, making `uv run` its only source)
  and that it installs nothing when `pyproject.toml` has an unlocked dependency.

## Verification results

Run locally on 2026-08-15, before pushing:

- `uv.lock` was already current — `uv sync --locked --all-groups --all-extras`
  exits 0, so the `--locked` switch surfaces no pre-existing drift.
- `python-lint-check.sh` resolves ruff and passes with a PATH scrubbed back to
  `/usr/local/bin:/usr/bin:/bin`, where ruff is absent. Worth noting for anyone
  reproducing this: ruff *is* on `PATH` in a normal devcontainer terminal,
  because the VS Code Python extension injects the environment's `bin/` — so the
  fallback rung under test is only exercised with an explicitly clean PATH.
- `--no-sync` holds. With `cowsay` added to `pyproject.toml` and left unlocked,
  the check still passes and installs nothing (`cowsay` absent from
  site-packages afterwards). `pyproject.toml` restored, `uv.lock` untouched.
- Gates: `actionlint`, `shellcheck`, `prettier`, `zizmor` (no findings),
  `iwe schema validate`, `validate_agent_files` 40/40, and
  `pytest py_packages .agents/plugins/agentdev/tests` 136 passed.
- Removing the `VIRTUAL_ENV` export also removed the only reason for the
  `zizmor: ignore[github-env]` suppression, which went with it.

CI itself is the remaining check: `validate-agent-files.yml` and `ci.yml` are
the only places the changed paths execute end to end.

## Risks

- **Tasks 1–4 are one atomic change.** The action and its only caller share a
  contract; splitting them across commits breaks `validate-agent-files.yml` in
  between. Task 5 onward is independent.
- **`only-system` is a hard failure by design.** It converts a silent fallback
  (uv downloads its own interpreter) into a loud one. That is the point, but it
  means a change to `actions/setup-python` behavior surfaces as a red job rather
  than a slow one.
- **`--locked` will fail immediately if `uv.lock` is currently stale.** That is
  the finding working as intended — but expect it to surface on the first run
  rather than later. Refresh the lock if so.
- **Rollback is a revert.** No persisted state migrates; runner environments are
  rebuilt from scratch every job.
