---
type: feature
stage: implemented
description: Both Docker engines of a Coder workspace bound their storage — a 10 GB BuildKit cache limit in each daemon and a 72-hour unused-image prune on every agent start — so workspaces sharing one host disk do not fill it.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-16T12:00:00Z
sources:
- resource: docs/knowledge/data/plans/20261013-docker-storage-gc.md
- resource: ansible/roles/install_docker/tasks/main.yml
- resource: .devcontainer/scripts/coder-agent-start.sh
---

# Docker storage limits

## Purpose

A Coder workspace runs two Docker engines — the workspace engine and the nested
Dev Container engine — and every workspace shares one host disk. Unbounded build
caches and unused images fill it, and a full disk stops any workspace from
starting its Dev Container.

## Behaviour

**Build cache.** Each engine's `daemon.json` enables BuildKit garbage collection
and keeps at most 10 GB of cache. The Dev Container engine's limit comes from
the image, so it applies wherever the image runs.

**Images.** On every agent start, each engine removes images that no container
references and that were created more than 72 hours ago. The Dev Container
engine's prune runs from the Coder agent start, so it runs on Coder only.

The contract is [Devcontainer Docker
storage](../spec/devcontainer-docker-storage.md).

## Edge cases

- **An unused image pulled today but built long ago** is removed: the 72-hour
  window compares creation time, not last use.
- **An image a stopped container references** is kept.
- **The prune fails or is skipped.** The agent start does not fail.

## Open questions

None — the design is settled.

## References

- Plan: [Cap Docker storage with automatic garbage
  collection](../plans/20261013-docker-storage-gc.md)
