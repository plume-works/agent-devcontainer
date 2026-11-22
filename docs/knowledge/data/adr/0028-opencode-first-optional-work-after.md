---
type: adr
stage: accepted
---

# OpenCode starts first, and optional work does not stop it

The standalone runtime starts OpenCode as soon as the core path completes, and
the core path holds only the steps that OpenCode needs. The other services, such
as `dockerd`, `xpra`, `config`, and `project`, are optional services. A failure
of an optional service degrades the runtime, and OpenCode continues.

## Considered Options

- Start OpenCode last, after all services. Rejected: a failed uv sync or nested
  Docker engine then makes the agent unavailable, and a large index makes each
  start slow.

## Consequences

- The `config` service registers the catalog before OpenCode starts, because
  OpenCode reads the catalog at start.
