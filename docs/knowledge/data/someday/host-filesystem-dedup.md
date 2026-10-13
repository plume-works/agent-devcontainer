---
type: someday
description: Reformat the Coder Docker host's data disk with a deduplicating filesystem so identical image layers across workspace and Dev Container engines are stored once.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-13T00:00:00Z
---

# Deduplicate Docker storage at the host filesystem

Every Coder workspace stores the same images more than once: in its workspace
engine and in its Dev Container engine, and again in every other workspace.
Docker daemons cannot share one store, but the host filesystem can store
identical blocks once.

Two candidates:

- **btrfs** with offline or background deduplication (`duperemove`, bees). It
  works on existing data without changing any Docker configuration.
- **ZFS** with `dedup=on`. It deduplicates as data is written, but its dedup
  table needs a lot of RAM.

Either one means reformatting the host's Docker data disk. Neither one changes
the Coder template or this repository.

Open questions:

- How the overlayfs snapshotter, and Sysbox's mounts under `/var/lib/sysbox`,
  behave on each filesystem.
- How much space it would actually save. Pruning unused images and capping the
  build cache already remove most of the waste: [Cap Docker storage with
  automatic garbage collection](../plans/20261013-docker-storage-gc.md).
