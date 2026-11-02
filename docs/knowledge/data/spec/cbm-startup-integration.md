---
type: spec
description: Every startup path submits a background CBM index request for the workspace instead of a blocking index.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T03:25:00Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/cbm.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
---

# CBM startup integration

How the devcontainer hooks and the standalone runtime start codebase-memory-mcp
(CBM) for the workspace. The daemon's lifecycle is [CBM daemon
lifecycle](../architecture/cbm-daemon-lifecycle.md).

## Requirements

### Requirement: startup requests workspace indexing in the background

Every startup path SHALL submit an asynchronous CBM `index_repository` request
for the main workspace and SHALL continue once CBM accepts it, without waiting
for the index. No startup path SHALL run a blocking index.

#### Scenario: a large workspace starts

- **WHEN** the devcontainer hooks or the standalone runtime start on a workspace
  whose index takes minutes
- **THEN** startup finishes while the CBM daemon indexes in the background.

#### Scenario: an index job is already running

- **WHEN** a startup request targets a workspace CBM is already indexing
- **THEN** the request joins that job and startup continues.
