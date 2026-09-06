---
type: task
stage: planned
priority: medium
created: 2026-09-06
description: Refresh the codebase map docs whose described content changed, so the staleness check ends green again.
generated:
  by: claude-code/opus-5
  at: 2026-09-06T00:00:00Z
---

# Refresh the map docs the Python port and prior drift left stale

`stale-map-docs.py` ends `RESULT=STALE_FOUND` on `iwe-for-consumers` with six
docs stale for content reasons, none of them maskable:

- `agents/plugins/agentdev`, `.../bin`, `.../skills`, `.../tests` and
  `docs/knowledge` describe trees the Python-port work changed — a new
  `bin/result_codes.py`, `stale-map-docs.sh` replaced by `stale-map-docs.py`,
  two new test modules, and an edited `docs/knowledge/AGENTS.md`.
- `flow-devcontainer-lifecycle` was already stale before that work and claims
  `.devcontainer`, `docker/desktop`, and `.agents/plugins/agentdev/hooks`.

Each needs the map skill's refresh mode: re-read the component, rewrite what no
longer holds, and re-stamp `verified` alongside `source_digest`. A mechanical
digest re-bump would assert the prose was re-read when it was not.

[Digest masks for map docs](../plans/20260905-digest-masks.md) deliberately left
this out — its Task 6 re-bumps only digests that moved because a mask began
applying, where the described code is unchanged.
