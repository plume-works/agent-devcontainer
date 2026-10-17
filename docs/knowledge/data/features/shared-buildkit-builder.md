---
type: feature
stage: accepted
description: Every Dev Container in a Coder workspace builds through one shared BuildKit daemon running in a dedicated Coder workspace, so workspaces share one build cache, and falls back to its local builder when the shared one is unreachable.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-16T12:00:00Z
sources:
- resource: docs/knowledge/data/plans/20261013-shared-buildkit-workspace.md
---

# Shared BuildKit builder

## Purpose

Each Coder workspace's Dev Container engine keeps its own BuildKit cache, so
workspaces that build the same images store and rebuild the same layers. One
shared builder holds one cache for all of them.

## Behaviour

**One builder for every workspace.** A `buildkitd` runs in a dedicated,
always-on Coder workspace with its state on a persistent volume.

**`docker build` uses it by default.** Each Dev Container's agent start
registers that daemon as a buildx builder named `shared`, which loads its
results into the local engine, and makes it the default builder when it answers.
`docker build --builder default` still builds locally.

## Edge cases

- **The shared builder is unreachable at agent start.** The local `default`
  builder is selected instead.
- **The shared builder becomes unreachable mid-session.** The build fails;
  building with `--builder default` works locally.
- **The Dev Container image itself.** The devcontainer CLI builds it on the
  workspace engine, which keeps its own builder.

## Open questions

How a Dev Container reaches the builder workspace, how the endpoint is
authenticated, and which Coder template runs the builder are settled by the
plan's first task.

## References

- Plan: [Share one BuildKit builder across Coder
  workspaces](../plans/20261013-shared-buildkit-workspace.md)
