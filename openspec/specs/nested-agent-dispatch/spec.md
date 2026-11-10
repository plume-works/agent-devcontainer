# Nested agent dispatch Specification

## Purpose

Defines Claude Code's subagent nesting limit in the devcontainer and the
standalone runtime, so a dispatched agent can dispatch another. OpenCode's limit
is a managed value of [Devcontainer OpenCode
policy](../devcontainer-opencode-policy/spec.md).

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

## Rationale

### Why the limit is raised, and what each harness needs

A workflow whose catalog agents are all leaves runs on both harnesses unchanged;
one in which a dispatched agent dispatches another depends on per-harness
settings. Measured on Claude Code 2.1.316 and OpenCode 2.1.2, to recheck on a
version bump:

- **Claude Code nests by default** when the agent's `tools:` includes `Agent` or
  is omitted. `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` sets the limit; unset, a
  server-side flag does, falling back to 3. The agent at the limit is not offered
  the `Agent` tool, and nothing reports an error. Each subagent transcript's
  `.meta.json` records `spawnDepth` and `parentAgentId`.
- **OpenCode does not nest by default.** At the default
  `experimental.subagent_depth` of `1`, a nested `task` call fails with
  "Subagent depth limit reached (1)". The key is experimental, so a design that
  needs it depends on a setting OpenCode may rename or drop.

The procedure that measures this is in
[Skill rehearsal runs](../../../docs/guides/skill-rehearsal-runs.md).
