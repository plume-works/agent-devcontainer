---
type: bug
stage: done
description: With CBM_CACHE_DIR inside a bind-mounted checkout another UID owns, every boot-time CBM start exits with "could not load saved runtime settings", and the supervisor stops the Dev Container.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T12:00:00Z
sources:
- resource: https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/cli/runtime_settings.c
- resource: https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/daemon/ipc.c
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/scripts/devcontainer-created.sh
- resource: .devcontainer/scripts/runtime-cbm.sh
---

# Bug: CBM cache under a checkout another UID owns stops the Dev Container

## Symptom

After a container restart the supervised `cbm` program exits within milliseconds
on every attempt:

``` text
codebase-memory-mcp: could not load saved runtime settings
runtime-cbm: daemon start failed with exit code 1
runtime-supervisor: cbm: cbm exhausted 3 recovery attempts
runtime-supervisor: exiting: cbm: cbm exhausted 3 recovery attempts
```

The runtime then stops every service and the container exits.

## Reproduction

As root, with `CBM_RUNTIME_DIR` pointing at a private scratch directory:

1. Create `<ws>/.cache/cbm` with mode `0700`, and `chown 1000:1000 <ws>`.
2. `CBM_CACHE_DIR=<ws>/.cache/cbm codebase-memory-mcp daemon start` prints the
   message above and exits `1`. With `<ws>` owned by root it starts.

## Root cause

Before reading `_config.db`, CBM validates the cache directory as a private
directory: every ancestor must be owned by root or the effective UID, and must
not be world-writable. A violation exits through the generic "could not load
saved runtime settings" message.

`CBM_CACHE_DIR` lived on the `agentdev-cache` volume at
`/workspaces/<name>/.cache`, so the bind-mounted checkout root was one of its
ancestors, and its owner is the host's user. Only the create phase
(`devcontainer-created.sh`, `claim_ancestors`) changes that owner to the
container user, and it never runs on a restart. The supervisor starts CBM at
boot, before any lifecycle hook, so CBM sees whatever owner the host left.

## Fix

`CBM_CACHE_DIR` is `/root/.cache/codebase-memory-mcp`, on its own per-worktree
`agentdev-cbm` volume. No ancestor of that path belongs to the host checkout.
See [CBM daemon lifecycle](../architecture/cbm-daemon-lifecycle.md).

## Key references

Verified anchor points (line numbers as of 2026-10-30):

- `.devcontainer/devcontainer.json:39` — `CBM_CACHE_DIR`
- `.devcontainer/devcontainer.json:73` — the `agentdev-cbm` mount
- `.devcontainer/scripts/devcontainer-created.sh:16` — `claim_ancestors`, which
  runs only at create
- CBM v0.12.1 `src/cli/runtime_settings.c` (`canonical_cache_path`) and
  `src/daemon/ipc.c` (`private_directory_tree_open`).
