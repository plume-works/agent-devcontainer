---
type: plan
created: 2026-08-14
description: Remove the in-tree .venv symlink, pin the uv environment to a fixed /uv path, and route every remaining consumer through `uv run`.
generated:
  by: claude-code/opus-5
  at: 2026-08-14T00:00:00Z
sources:
- resource: .devcontainer/scripts/uv-sync.sh
- resource: .devcontainer/devcontainer.json
- resource: .agents/plugins/agentdev/bin/python-lint-check.sh
stage: done
completed: 2026-08-15
---

# Drop the .venv symlink

## Context

`uv-sync.sh` recreates `/workspaces/<ws>/.venv` as a symlink to
`$UV_PROJECT_ENVIRONMENT` on every postCreate *and* postAttach, purely as a
compatibility shim for tooling that expects the conventional in-tree path. The
repository's own convention, stated in `AGENTS.md` and used throughout
`README.md`, is to run project commands through `uv run` — the symlink is the
one affordance contradicting it.

Nothing is broken today: `uv run` resolves the symlink and emits no
`VIRTUAL_ENV does not match` warning. This is a simplification, not a bug fix,
and should be judged on that basis.

The out-of-tree environment itself stays. `/uv/cache` and `/uv/venvs` are the
same mount (`/dev/vda1 /uv`), which is what lets uv hardlink packages out of its
cache into the environment. An in-tree `.venv` would land on the host bind mount
— a different filesystem — and uv would silently fall back to copying.
[Template boundary](../architecture/template-boundary.md) currently records only
the weaker "survives container rebuilds" reason; Task 6 fixes that.

## Approach

Keep `UV_PROJECT_ENVIRONMENT`, drop the symlink, and split the consumers in two:
everything expressible as a command becomes `uv run`; the four VS Code settings
that need a filesystem path get the absolute path instead.

Because the `agentdev-uv` volume is declared in `devcontainer.json` `mounts`
rather than pinned to a literal name in Compose (only `agentdev-agents-auth` is
pinned that way), it is Compose-project-scoped — one `/uv` per devcontainer
instance. So the path needs no `${localWorkspaceFolderBasename}` disambiguation
and can be a fixed string, `/uv/venvs/ws-project`. That matters: it reduces the
cost of hardcoding the path in five places from "a templated convention that
must stay in sync" to "a constant".

Verified as of 2026-08-15 (Task 1): `/uv/venvs/` now holds two entries, the
pre-existing `agent-devcontainer-wortree-2` and the new `ws-project`. These are
the old and new environment names within this one instance, not two workspaces
sharing a mount, so the Compose-project-scoping argument above is unaffected.
The stale `agent-devcontainer-wortree-2/` directory is left for the container
rebuild in `## Verification` to supersede; nothing reads it after Task 1.

Rejected: moving the environment back in-tree to remove the indirection
entirely. Simpler to explain, but it breaks cache-to-venv hardlinking as above.

## Implementation Steps

### Task 1: Pin the uv environment to a fixed path

**Files:** Modify: `.devcontainer/devcontainer.json`

- [x] `UV_PROJECT_ENVIRONMENT` → `/uv/venvs/ws-project` (drop the trailing
  slash; the settings below append `/bin/...`)
- [x] `python.defaultInterpreterPath` → `/uv/venvs/ws-project/bin/python3`
- [x] `ansible.ansible.path` → `/uv/venvs/ws-project/bin/ansible` (currently
  workspace-relative)
- [x] `ansible.python.interpreterPath` → `/uv/venvs/ws-project/bin/python3`
- [x] `ansible.validation.lint.path` → `/uv/venvs/ws-project/bin/ansible-lint`
- [x] Leave `search.exclude`'s `**/.venv` entry alone — host checkouts still
  produce a real one

### Task 2: Stop creating the symlink

**Files:** Modify: `.devcontainer/scripts/uv-sync.sh`,
`.devcontainer/scripts/postCreateCommand.sh`

- [x] Delete the `rm -rf`/`ln -s` blocks and the comment above them; the script
  becomes `cd "$workspace"` + `uv sync --all-groups --all-extras`
- [x] Replace the deleted comment with the real rationale: the environment lives
  on the `/uv` volume so uv can hardlink from `UV_CACHE_DIR` on the same
  filesystem
- [x] Keep a narrow migration cleanup: remove `$workspace/.venv` only when it is
  a symlink, guarding on `-L` and using a plain `rm`, never `rm -rf`, so a real
  host-created `.venv` is never touched. This lets existing containers shed the
  stale link on the next postAttach without a rebuild, and is removable once
  every active worktree has re-synced
- [x] Also verify the link *target* before removing it, so the cleanup only
  claims links this repository created and never a deliberate one pointing
  somewhere else
- [x] Update the postCreate comment, which says the sync targets "the
  container's `.venv` directory"

### Task 3: Route the lint script through `uv run`

**Files:** Modify: `.agents/plugins/agentdev/bin/python-lint-check.sh`

- [x] Replace the `source .venv/bin/activate` branch with `uv run`. Note that it
  resolves the project from the cwd while the script works from `$root_dir`
  supplied by `__utils.sh` — use `uv run --project "$root_dir"` or an explicit
  `cd`
- [x] Decide the fallback contract deliberately. The script ships inside the
  portable `agentdev` plugin, and today its PATH fallback lets it work in repos
  with no synced environment. Bare `uv run` converts that into a hard failure
  outside a uv project — keep a PATH fallback for when `uv` or a project
  manifest is absent
- [x] Update the header comment, which still explains the `.venv` preference
- [x] `shellcheck` clean (pre-commit)

Deviation (2026-08-15): a two-tier `uv run` → PATH fallback still regressed the
portable case. The old activate branch put ruff on PATH *by activating*, so in a
non-uv repo with no ruff installed the new script hard-failed where the old one
worked. Verified by running it in a standalone git repo with no
`pyproject.toml`. Resolved with a third tier — `uv run --project` → ruff on PATH
→ `uv tool run ruff` — which restores and widens the original reach. PATH is
ordered ahead of `uv tool run` so the common case never pays a network fetch.

### Task 4: Remove `venv_activate` from the fish helpers

**Files:** Modify: `ansible/roles/fish_setup/templates/dev.fish.j2`,
`ansible/roles/fish_setup/README.md`

- [x] Delete `venv_activate` — with no in-tree `.venv`, `find_up .venv` can
  never succeed
- [x] **Keep `find_up`** unless the maintainer says otherwise. It has no
  remaining in-repo caller, but the README advertises it as a standalone
  interactive helper, so grep cannot see its real usage
- [x] Drop `venv_activate` from the README's helper list

### Task 5: Update the docs that describe the symlink

**Files:** Modify:
`.agents/plugins/agentdev/skills/python-format-lint/SKILL.md`,
`.agents/plugins/agentdev/skills/microvm-sandbox/SKILL.md`,
`docs/knowledge/data/architecture/template-boundary.md`

- [x] `python-format-lint` SKILL.md: the two `.venv/bin/ruff` invocations become
  `uv run ruff`; fix the two troubleshooting rows that name `.venv`
- [x] `microvm-sandbox` SKILL.md: drop "links `.venv` to the cached environment"
- [x] `template-boundary.md`: the `uv-sync.sh` row no longer links anything
- [x] Leave `template-boundary.md`'s generated-state list as is — `.venv` still
  belongs there for host and CI checkouts

### Task 6: Record the environment-location decision

**Files:** Create:
`docs/knowledge/data/architecture/uv-environment-location.md`; Modify:
`docs/knowledge/data/architecture.md`, `docs/knowledge/data/index.md`

- [x] Why the environment is out of tree: hardlinking from `UV_CACHE_DIR`
  requires cache and environment on one filesystem
- [x] Why the path is a fixed string: `agentdev-uv` is Compose-project-scoped,
  so there is one `/uv` per instance and nothing to disambiguate
- [x] Rejected alternatives: in-tree `.venv` (breaks hardlinking), and keeping
  the symlink (contradicts the `uv run` convention for no remaining benefit)
- [x] Inclusion link from `architecture.md`; update `index.md`

Note (2026-08-15): `index.md` needed no edit — it links hubs, not individual
documents, so the new doc is already reachable through the Architecture hub.
`template-boundary.md`'s `uv-sync.sh` row gained a cross-reference to the new
doc. The "survives container rebuilds" wording the Context attributes to
`template-boundary.md` was actually in the `uv-sync.sh` comment, replaced in
Task 2.

## Spec changes

None. `data/spec/template-consumption.md` references `uv-sync.sh` and
`uv sync --all-groups --all-extras` at several points, and states that
post-create depends on `uv-sync.sh` — all still true after this change. No spec
document mentions the symlink, and no specified behavior changes.

## Verification

- `.devcontainer/scripts/uv-sync.sh` exits 0, then `test ! -e .venv` passes
- `uv run python -c "import sys; print(sys.prefix)"` prints
  `/uv/venvs/ws-project`
- `.agents/plugins/agentdev/bin/python-lint-check.sh` exits 0 with no arguments
  and with an explicit path argument
- `uv run pytest` — both suites green (no test covers the lint script today, so
  this is a regression guard only)
- `uv run ansible-lint ansible` succeeds, as a proxy for the rewritten Ansible
  extension paths
- **Rebuild the container**, then in a fresh VS Code terminal confirm
  `command -v ruff pytest` resolve under `/uv/venvs/ws-project/bin`. This is the
  behavior most likely to regress quietly: the extension's terminal PATH
  injection is driven by `python.defaultInterpreterPath`, so it should follow
  the new path — verify rather than assume
- `uv run pre-commit run --all-files` (shellcheck, prettier, ruff)
- `iwe normalize` then `iwe schema validate` for Tasks 5–6

## Out of scope

- `.github/actions/setup-python-venv/action.yml` — CI builds its own real
  in-tree `.venv` with `python -m venv` + `uv sync --active`. Unaffected here.
  Unifying CI onto `uv run` is a separate, larger change
- `.gitignore`, `.dockerignore`, `search.exclude`, and the `shellcheck-fix.sh`
  prune — all kept; host checkouts and plugin consumers still create a real
  `.venv`
- Moving `UV_PROJECT_ENVIRONMENT` in-tree (rejected above)
- Renaming or re-scoping the `agentdev-uv` volume

## Key references

Verified anchor points (line numbers as of 2026-08-14):

- `.devcontainer/devcontainer.json:37` — `UV_PROJECT_ENVIRONMENT`
- `.devcontainer/devcontainer.json:51` — `agentdev-uv` volume mount
- `.devcontainer/devcontainer.json:140` — `python.defaultInterpreterPath`
- `.devcontainer/devcontainer.json:155-157` — the three `ansible.*` paths
- `.devcontainer/scripts/uv-sync.sh:8-19` — comment, `rm -rf`, `uv sync`,
  `ln -s`
- `.devcontainer/scripts/postCreateCommand.sh:66-68` — stale `.venv` comment and
  the `uv-sync.sh` call
- `.devcontainer/scripts/postAttachCommand.sh:10` — second `uv-sync.sh` call
- `.devcontainer/docker-compose.yml:103-109` — the `volumes:` block that pins
  only `agentdev-agents-auth` to a literal name
- `.agents/plugins/agentdev/bin/python-lint-check.sh:31-44` — activate branch,
  PATH fallback, the two `ruff` invocations
- `ansible/roles/fish_setup/templates/dev.fish.j2:1` — `find_up`
- `ansible/roles/fish_setup/templates/dev.fish.j2:21-30` — `venv_activate`
- `ansible/roles/fish_setup/README.md:5-6` — advertised helper list
- `.agents/plugins/agentdev/skills/python-format-lint/SKILL.md:57-58,79-80`
- `.agents/plugins/agentdev/skills/microvm-sandbox/SKILL.md:34`
- `docs/knowledge/data/architecture/template-boundary.md:76` — `uv-sync.sh` row
- `docs/knowledge/data/architecture/template-boundary.md:215` — generated-state
  list (unchanged)
