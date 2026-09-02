---
type: feature
stage: implemented
description: The pre-commit hook cache lives on the per-worktree agentdev-cache volume via PRE_COMMIT_HOME, so only the first devcontainer create per worktree pays the cold hook-install cost and every rebuild after starts warm.
generated:
  by: claude-code/opus-5
  at: 2026-09-02T00:00:00Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/scripts/setup-pre-commit.sh
---

# Persist the pre-commit hook cache

## Purpose

`setup-pre-commit.sh` runs `pre-commit install --install-hooks` on every
container start. With `PRE_COMMIT_HOME` unset, pre-commit installs its hook
environments into `$HOME/.cache/pre-commit` on the container overlay filesystem,
which is discarded on every rebuild — so the cold install (~33s, ~935 MB for the
repository's hook set) is paid again each time. Persisting the cache on the
already-mounted `agentdev-cache` volume gives the same warm-start benefit at
zero image-size cost and with no new volume.

## Behaviour

**`PRE_COMMIT_HOME` points at the agentdev-cache volume.** `devcontainer.json`'s
`containerEnv` sets `PRE_COMMIT_HOME` to
`/workspaces/${localWorkspaceFolderBasename}/.cache/pre-commit`, a subfolder of
the `agentdev-cache` volume that already holds `codebase-memory-mcp` under
`CBM_CACHE_DIR`. The first create per worktree installs the hook environments
fresh into that volume path; every rebuild after reuses them and completes in
well under a second.

**The cache is installed fresh, never copied.** pre-commit's store keys each
hook environment by `(repo, ref)` and records an absolute path it trusts blindly
on lookup, so a cache is usable only at the exact path it was installed to. The
mount target is a fixed path across rebuilds of a worktree, so a fresh install
records the volume path and every later run hits it. Config drift degrades
gracefully — bumping one hook's `rev` reinstalls only that hook and leaves the
rest as cache hits.

**The failure-log path follows `PRE_COMMIT_HOME`.** The error branch in
`setup-pre-commit.sh` tails
`${PRE_COMMIT_HOME:-$HOME/.cache/pre-commit}/pre-commit.log`, reporting the log
where it actually lives whether or not `PRE_COMMIT_HOME` is set.

## Scope

Per-worktree scope is intended: `agentdev-cache` is Compose-project-scoped, so
each worktree's cache is naturally isolated and the first create per worktree
pays the cold cost. No lifecycle-script logic changed —
`install --install-hooks` already installs into the volume path, and the
postCreate chown loop over `$workspace/.cache` covers the new subdir for free.
Firewall allowlisting for the one-time cold fill under `ENABLE_FIREWALL=true` is
out of scope.

A global shared volume (warm across all worktrees after the first-ever create)
and a dedicated `agentdev-precommit` volume were both rejected in favour of
reusing the existing per-worktree volume; the shared variant can be revisited if
first-create-per-worktree cost becomes a pain.

## References

- Plan:
  [Persist the pre-commit hook cache on the agentdev-cache volume](../plans/20260902-persist-pre-commit-cache.md)
