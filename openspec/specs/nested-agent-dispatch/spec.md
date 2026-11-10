# Nested agent dispatch Specification

## Purpose

Defines Claude Code's subagent nesting limit in the devcontainer and the
standalone runtime, so a dispatched agent can dispatch another. OpenCode's limit
is a managed value of [Devcontainer OpenCode
policy](../devcontainer-opencode-policy/spec.md). Host behavior: [Nested subagent
dispatch](#rationale).

## Requirements

### Requirement: Claude Code nests subagent dispatch to depth 5

The `devcontainer` service in `.devcontainer/docker-compose.yml` and the
`opencode` service in `compose.opencode.yml` SHALL set
`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` in the container environment to the
host's value when it is set, and to `5` otherwise.

#### Scenario: a container starts with no override

- **WHEN** either container starts and the host sets no
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`
- **THEN** Claude Code in the container nests subagent dispatch to depth 5.

#### Scenario: the host overrides the depth

- **WHEN** the host, or for the standalone runtime `runtime.env`, sets
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`
- **THEN** the container's Claude Code uses that value.
