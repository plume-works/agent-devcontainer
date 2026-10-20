---
type: spec
description: The agentdev OpenCode bridge registers the active Git workspace with the shared codebase-memory daemon in the background, without blocking catalog use or changing MCP configuration.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T15:00:00Z
sources:
- resource: .agents/plugins/agentdev/.opencode-plugin/workspace-index.ts
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .agents/plugins/agentdev/tests/opencode/workspace-index.test.ts
- resource: .agents/plugins/agentdev/tests/opencode/bridge.test.ts
- resource: .agents/plugins/agentdev/tests/opencode/verify-workspace-host.ts
---

# OpenCode workspace CBM indexing

How the agentdev OpenCode bridge makes the repository opened in OpenCode
available to codebase-memory. The catalog requirements in [OpenCode catalog
bridge](opencode-catalog-bridge.md) still apply; the design is in [OpenCode
catalog bridge](../architecture/opencode-catalog-bridge.md).

## Requirements

### Requirement: register the active Git workspace

The bridge SHALL resolve OpenCode's active directory to its canonical Git
worktree root and register an absent root with the shared CBM daemon only when
the configured codebase-memory MCP is local and enabled. On OpenCode v1 it SHALL
do this from the config hook; on OpenCode v2, from the bridge's v2 setup for
each directory OpenCode opens. A local entry counts as enabled unless v1's
`enabled` is `false` or v2's `disabled` is `true`. It SHALL use the configured
command and environment without broadening allowed roots or changing MCP
configuration, and SHALL retain existing indexed projects.

#### Scenario: a second repository opens in the container

- **WHEN** OpenCode initializes in an unindexed Git repository with local CBM
  enabled
- **THEN** it submits background indexing for that repository, independently of
  the catalog location and DEV_WORKSPACE_FOLDER, retaining other projects.

#### Scenario: OpenCode v2 opens an unindexed repository

- **WHEN** OpenCode v2 opens a directory in an unindexed Git repository with
  local CBM enabled
- **THEN** the bridge submits background indexing for that repository's
  canonical root.

#### Scenario: a registered root is found on a later project page

- **WHEN** any page of the project list contains the canonical active root
- **THEN** the bridge submits no indexing request for it.

#### Scenario: a subdirectory or linked worktree opens

- **WHEN** OpenCode initializes in a repository subdirectory, symlink, or linked
  worktree
- **THEN** the bridge uses the canonical worktree root and treats separate
  worktree roots as distinct repositories.

#### Scenario: automatic indexing does not apply

- **WHEN** the directory is not a Git worktree or CBM config is absent,
  disabled, or remote
- **THEN** the bridge skips automatic registration without changing
  configuration.

### Requirement: registration does not block catalog use

The bridge SHALL keep catalog initialization independent of indexing completion,
deduplicate in-flight registration for a root, and handle failed or timed-out
commands with bounded resource use and a warning in OpenCode's log, written
through the logging client on v1 and through the host's logger on v2.

#### Scenario: indexing is pending

- **WHEN** a registration request or background index remains pending
- **THEN** catalog skills, commands, agents, and skill-name rewriting remain
  available.

#### Scenario: CBM lookup or submission fails

- **WHEN** a command cannot start, exceeds ten seconds or the output limit,
  returns invalid data or an MCP error, or rejects the root
- **THEN** the bridge logs a diagnostic without an unhandled rejection or config
  failure, submits no index after a failed lookup, and permits another attempt
  on a later workspace initialization.

#### Scenario: multiple initializations target the same root

- **WHEN** registration overlaps for one canonical root
- **THEN** in-process requests share the attempt and daemon requests join
  existing indexing instead of starting competing jobs.
