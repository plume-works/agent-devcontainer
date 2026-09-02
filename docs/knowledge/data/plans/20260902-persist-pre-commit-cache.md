---
created: 2026-09-02
type: plan
description: Persist the pre-commit hook cache on the agentdev-cache volume so only the first devcontainer create per worktree pays the cold install cost.
generated:
  by: claude-code/opus-5
  at: 2026-09-02T03:05:00Z
---

# Persist the pre-commit hook cache on the agentdev-cache volume

## Context

`setup-pre-commit.sh` runs `pre-commit install --install-hooks` on every
container start. With `PRE_COMMIT_HOME` unset, pre-commit installs its hook
environments into the default `$HOME/.cache/pre-commit`, i.e.
`/root/.cache/pre-commit`. That path is **overlay (container filesystem), not a
volume** — verified with `findmnt`: `/root/.cache` is `overlay`, while
`/root/.claude`, `/root/.codex`, `/uv`, and `/workspaces/<base>/.cache` are all
`ext4` volume mounts. So the entire hook cache is discarded on every rebuild and
the cold install is paid again.

Measured cost of that cold install in this image (11 remote hooks, empty cache):
**~33–35s wall**, producing a **~935 MB** cache. A fully warm re-run of the same
command is **~0.15s**. The saving per rebuild is therefore roughly the full cold
time.

Baking the cache into the base image was considered and rejected: it adds ~935
MB (~17%) to an already ~5.4 GB image for a one-time-per-rebuild saving, and the
base image is pulled and stored on every machine and runner. Persisting the
cache on the already-mounted `agentdev-cache` volume achieves the same
warm-start benefit with **zero image-size cost** and **no new volume** —
`agentdev-cache` is Compose-project-scoped (per worktree), so the cache is
naturally isolated per worktree, which is the desired scope. First create per
worktree pays ~33s; every rebuild after starts warm.

The behavior that makes this correct — and the one constraint that governs the
implementation — is that pre-commit's store keys each hook environment by
`(repo, ref)` in `db.db` and records an **absolute path** for it, which it
trusts blindly on lookup (`SELECT path FROM repos WHERE repo=? AND ref=?`,
returned without an existence check). Two consequences, both verified
empirically:

- A cache is usable only at the **exact absolute path it was installed to**.
  Pointing `PRE_COMMIT_HOME` at a *copy* of a cache whose `db.db` was written
  for a different path fails with `InvalidManifestError` — it does not re-clone.
  The cache must be **installed fresh into the volume path**, never copied in.
  Since the mount target is a fixed path constant across rebuilds of a worktree,
  a fresh install records the volume path and every later run hits.
- Config drift degrades gracefully: bumping one hook's `rev` reinstalls only
  that hook (~seconds) and leaves the rest as cache hits. A worktree whose
  `.pre-commit-config.yaml` has moved past the cached revs pays only for the
  changed hooks, never a full cold rebuild.

Concurrency is not a concern at this scope (one worktree = one
`agentdev-cache`), and pre-commit's store is `flock`-guarded with atomic
per-repo installs even when shared.

Firewall interaction (allowlisting the hook source hosts for the one-time cold
fill under `ENABLE_FIREWALL=true`) is explicitly out of scope for this plan.

## Approach

Set `PRE_COMMIT_HOME` in `devcontainer.json`'s `containerEnv` to a subfolder of
the existing `agentdev-cache` volume:
`/workspaces/${localWorkspaceFolderBasename}/.cache/pre-commit`. This is the
same volume and the same per-worktree scope that already holds
`codebase-memory-mcp` under `CBM_CACHE_DIR`.

No lifecycle-script logic changes are required: `setup-pre-commit.sh` already
runs `install --install-hooks`, which will install into the volume path on first
create and hit it on every rebuild. Ownership is already handled — the
postCreate chown loop recurses over `$workspace/.cache`, so the new
`pre-commit/` subdir is covered for free.

Two accuracy fixes ride along, because moving `PRE_COMMIT_HOME` invalidates a
hardcoded reference and stales two comments:

- The failure branch in `setup-pre-commit.sh` tails
  `"$HOME/.cache/pre-commit/pre-commit.log"`, which will no longer be where the
  log lives once `PRE_COMMIT_HOME` moves. Point it at `${PRE_COMMIT_HOME}` (with
  the `$HOME/.cache/pre-commit` default preserved for callers that leave the env
  var unset, e.g. a bare `container:` job).
- The `CBM_CACHE_DIR` and `agentdev-cache` mount comments in `devcontainer.json`
  describe the volume as codebase-memory-mcp's; note that pre-commit now shares
  it.

Rejected alternative — a dedicated new volume (`agentdev-precommit`) at
`/root/.cache/pre-commit`: cleaner separation and lets it match pre-commit's
default path with no env var, but adds a volume declaration for no benefit over
reusing the volume that already exists and is already chowned. Rejected
alternative — a global literal-named shared volume (like `agentdev-agents-auth`)
so the cache is warm across all worktrees after the first-ever create: sound and
concurrency-safe, but the user chose per-worktree scope; the shared variant can
be revisited if first-create-per-worktree cost becomes a pain.

## Implementation Steps

### Task 1: Point PRE_COMMIT_HOME at the agentdev-cache subfolder

**Files:** Modify: `.devcontainer/devcontainer.json`

- [x] Add
  `"PRE_COMMIT_HOME": "/workspaces/${localWorkspaceFolderBasename}/.cache/pre-commit"`
  to the `containerEnv` block, next to `CBM_CACHE_DIR` which already points into
  the same volume.
  - **Evidence:** `.devcontainer/devcontainer.json` `containerEnv` now sets
    `PRE_COMMIT_HOME` to the agentdev-cache subfolder; commit `aa092bf`.
- [x] Update the `CBM_CACHE_DIR` comment and the `agentdev-cache` mount comment
  so they state the volume now also persists the pre-commit hook cache, not only
  codebase-memory-mcp.
  - **Evidence:** both comments in `.devcontainer/devcontainer.json` (above
    `CBM_CACHE_DIR` and above the `agentdev-cache` mount) now name the
    pre-commit hook cache as a co-tenant of the volume; commit `aa092bf`.

### Task 2: Fix the failure-log path in setup-pre-commit.sh

**Files:** Modify: `.devcontainer/scripts/setup-pre-commit.sh`

- [x] Change the error-branch log tail from
  `"$HOME/.cache/pre-commit/pre-commit.log"` to
  `"${PRE_COMMIT_HOME:-$HOME/.cache/pre-commit}/pre-commit.log"` so a failing
  install reports the log where it actually lives, whether or not
  `PRE_COMMIT_HOME` is set.
  - **Evidence:** `.devcontainer/scripts/setup-pre-commit.sh:20` failure branch
    now tails `${PRE_COMMIT_HOME:-$HOME/.cache/pre-commit}/pre-commit.log`;
    shellcheck passed in the pre-commit run for commit `a53276a`.

## Spec changes

None — no behavioral change. This is a cache-location change: the hooks
installed, the commands run, and the validation results are identical. The only
observable difference is startup latency on rebuild (warm instead of cold) and
where the cache and its failure log reside.

## Key references

Verified anchor points (line numbers as of 2026-09-02):

- `.devcontainer/devcontainer.json:17` — `containerEnv` block (insertion point)
- `.devcontainer/devcontainer.json:33` — `CBM_CACHE_DIR`, existing consumer of
  the same volume
- `.devcontainer/devcontainer.json:59-60` — `agentdev-cache` volume mounted at
  `workspace/.cache`
- `.devcontainer/scripts/setup-pre-commit.sh:20` —
  `pre-commit install --install-hooks`; hardcoded
  `$HOME/.cache/pre-commit/pre-commit.log` in the failure branch
- `.devcontainer/scripts/postCreateCommand.sh:45` — chown loop over
  `$workspace/.cache` (covers the new subdir for free)

## Verification

- [ ] Rebuild the devcontainer. On first create, `setup-pre-commit.sh` performs
  a cold install (~33s) and `/workspaces/<base>/.cache/pre-commit/` is populated
  on the `agentdev-cache` volume (`db.db` plus `repo*` env dirs).
- [ ] `db.db` stores volume paths:
  `python3 -c "import sqlite3;print(next(sqlite3.connect('/workspaces/<base>/.cache/pre-commit/db.db').execute('select path from repos'))[0])"`
  prints a path under `/workspaces/<base>/.cache/pre-commit/`, not
  `/root/.cache`.
- [ ] Rebuild again (container fs discarded, volume persists).
  `setup-pre-commit.sh` completes in well under a second with zero
  `Initializing environment` lines — the warm-start goal.
- [ ] `git commit` in the rebuilt container fires the hooks and they run
  normally (the hook scripts in `.git/hooks` still resolve their environments
  from the volume cache).

## Verification results

Config confirmed statically from inside the current (pre-rebuild) container:

- `agentdev-cache` is mounted at
  `/workspaces/agent-devcontainer-wortree-2/.cache` as an **ext4 volume**
  (`findmnt`), so the new `PRE_COMMIT_HOME` subfolder persists across rebuilds.
- Before this change, `PRE_COMMIT_HOME` is unset and `db.db` records an overlay
  path (`/root/.cache/pre-commit/repo…`) — the exact discarded-on-rebuild state
  the plan targets. The new `containerEnv` value redirects fresh installs into
  the volume path.

The four checks above each require a **devcontainer rebuild** to observe (a cold
create populating the volume, then a warm rebuild proving sub-second startup),
which cannot be run from inside the running container. They remain unchecked
pending a rebuild by the user.
