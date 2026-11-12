---
type: spec
description: Claude Code in the devcontainer and the standalone runtime nests subagent dispatch to depth 5 unless the host sets another limit, and a catalog agent that dispatches lists the Agent tool.
sources:
- resource: .devcontainer/docker-compose.yml
- resource: compose.opencode.yml
- resource: docker/deploy/runtime.env.example
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py
---

# Nested agent dispatch

## Purpose

Defines Claude Code's subagent nesting limit in the devcontainer and the
standalone runtime, so a dispatched agent can dispatch another. OpenCode's limit
is a managed value of [Devcontainer OpenCode
policy](devcontainer-opencode-policy.md).

## Requirements

### Requirement: Claude Code nests subagent dispatch to depth 5

The `devcontainer` service in `.devcontainer/docker-compose.yml` and the
`opencode` service in `compose.opencode.yml` SHALL set
`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` in the container environment to the
host's value when it is set, and to `5` otherwise.

#### Scenario: the host overrides the depth

- **WHEN** the host, or for the standalone runtime `runtime.env`, sets
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`
- **THEN** the container's Claude Code uses that value.

### Requirement: a catalog agent that dispatches lists `Agent`

A catalog agent that runs as a dispatched subagent and dispatches another agent
SHALL list `Agent` in its `tools:` frontmatter, because Claude Code offers a
subagent the `Agent` tool only when its `tools:` list names it or is omitted. A
rulebook followed in place dispatches with the session's own tools and needs no
such entry.

#### Scenario: the shipper dispatches the verifier

- **WHEN** `iwe-shipper` runs as a subagent and reaches its Verify gate
- **THEN** it has the `Agent` tool and dispatches `iwe-verifier`.

## Rationale

### Both harnesses nest to depth 5

The devcontainer and the standalone runtime raise Claude Code's and OpenCode's
subagent nesting limits to 5, so a dispatched catalog agent can dispatch another
on either harness. OpenCode's limit lives under `experimental`, a key OpenCode
may rename or drop; that is the accepted cost.

Rejected:

- **The harness defaults.** OpenCode's default depth of 1 refuses every nested
  `task` call, and with no variable set Claude Code's limit comes from a
  server-side flag rather than from the container.

### Claude Code's depth is set in the compose environment

The repository owner wanted the value stated where the container is defined, so
it sits in the compose services' `environment:` blocks. The depth is raised only
in the devcontainer and the standalone runtime; a native host such as macOS
keeps Claude Code's own limit.

Rejected:

- **`env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` in Claude Code's `settings.json`,
  written by `agentdev-runtime state agent-policy`.** The owner chose the
  container definition as the value's one place.
- **An image-build write of `~/.claude/settings.json` from the Ansible
  `agentic_tools` role.** The home is a volume, which hides the image's file
  once the volume holds one.
