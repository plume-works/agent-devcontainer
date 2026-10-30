---
type: feature
stage: implemented
description: The pre-commit hook cache lives on its own per-worktree agentdev-pre-commit volume via PRE_COMMIT_HOME, outside the checkout, so only the first devcontainer create per worktree pays the cold hook-install cost and every rebuild after starts warm.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T12:30:00Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/scripts/setup-pre-commit.sh
---

# Persist the pre-commit hook cache

## Purpose

`setup-pre-commit.sh` runs `pre-commit install --install-hooks` on every
container start. Without a volume, pre-commit installs its hook environments
into `$HOME/.cache/pre-commit` on the container overlay filesystem, which is
discarded on every rebuild — so the cold install (~33s, ~935 MB for the
repository's hook set) is paid again each time. A volume at that path keeps it
across rebuilds at zero image-size cost.

## Behaviour

**`PRE_COMMIT_HOME` points at the agentdev-pre-commit volume.**
`devcontainer.json` mounts the `agentdev-pre-commit` volume at
`/root/.cache/pre-commit` and sets `PRE_COMMIT_HOME` to that path. The first
create per worktree installs the hook environments fresh into the volume; every
rebuild after reuses them and completes in well under a second.

**The cache stays off the checkout.** No cache volume is mounted inside the
workspace, so the checkout carries no mount point and its owner or filesystem
never decides whether a cache works. The CBM cache follows the same rule (see
[CBM daemon lifecycle](../architecture/cbm-daemon-lifecycle.md)).

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

Per-worktree scope is intended: `agentdev-pre-commit` is Compose-project-scoped,
so each worktree's cache is naturally isolated and the first create per worktree
pays the cold cost. `install --install-hooks` installs into the volume path with
no lifecycle-script logic of its own. Firewall allowlisting for the one-time
cold fill under `ENABLE_FIREWALL=true` is out of scope.

A global shared volume (warm across all worktrees after the first-ever create)
was rejected in favour of a per-worktree one; it can be revisited if
first-create-per-worktree cost becomes a pain.

## Edge cases

- **The first create of a worktree.** The volume is empty, so that create pays
  the full cold install; only later rebuilds start warm.
- **One hook's `rev` is bumped.** Only that hook's environment is reinstalled;
  the rest stay cache hits.
- **`PRE_COMMIT_HOME` is unset.** Outside the devcontainer the install and the
  failure log both fall back to `$HOME/.cache/pre-commit`.

## Open questions

None — every design question this feature raised is settled.

## References

- Plan: [Persist the pre-commit hook cache on the agentdev-cache
  volume](../plans/20260902-persist-pre-commit-cache.md)
