---
type: spec
description: Every startup path submits a background CBM index request for the workspace instead of a blocking index, and CBM installation keeps its Codex hooks in hooks.json, recovering an orphaned hooks block in config.toml only when it is exactly CBM's own.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-28T02:36:16Z
sources:
- resource: .devcontainer/scripts/codebase-memory-mcp-index.sh
- resource: .devcontainer/scripts/codebase-memory-mcp-install.sh
- resource: .devcontainer/scripts/codebase-memory-mcp-start.sh
- resource: .devcontainer/scripts/postAttachCommand.sh
- resource: .devcontainer/scripts/runtime-cbm.sh
- resource: .devcontainer/scripts/repair-codex-cbm-hooks-block.py
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

### Requirement: CBM's Codex hooks have one representation

CBM installation SHALL keep its Codex hooks in `$CODEX_HOME/hooks.json`, created
as an empty object when absent, so that `config.toml` holds no CBM hook tables.
Before installing, it SHALL remove an orphaned CBM hooks block only when every
claimed table is exactly CBM's own, preserving all other content, newline style,
and file mode, and SHALL otherwise leave the file unchanged and fail naming the
foreign table.

#### Scenario: Codex wrote tables around a lone closing marker

- **WHEN** `config.toml` holds CBM's exact hook tables and a closing marker with
  no opener, among Codex's own tables
- **THEN** installation removes that block, writes the hooks to `hooks.json`,
  keeps every Codex table, and a second installation changes neither file.

#### Scenario: the orphaned block was edited

- **WHEN** a hook table inside an orphaned block differs from CBM's canonical
  content
- **THEN** installation leaves `config.toml` byte-identical and fails naming
  that table.

#### Scenario: Codex has not run yet

- **WHEN** installation runs before any `$CODEX_HOME` exists
- **THEN** CBM registers its Codex hooks in a new `hooks.json`.
