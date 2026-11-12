---
type: feature
stage: implemented
description: Agents in the devcontainer can dispatch subagents that dispatch further subagents, up to depth 5, on both Claude Code and OpenCode.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py
- resource: .devcontainer/docker-compose.yml
- resource: compose.opencode.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: docs/knowledge/data/archive/2.0.0/architecture/nested-subagent-dispatch.md
- resource: docs/knowledge/data/backlog/nested-catalog-agent-dispatch.md
---

# Nested agent dispatch

## Purpose

Catalog workflows need an agent to start a fresh-context agent of its own, such
as `iwe-shipper` dispatching `iwe-verifier`. Claude Code nests to depth 3 by
default, and OpenCode refuses any nesting at its default
`experimental.subagent_depth` of 1.

## Behaviour

The devcontainer and the standalone runtime container start with
`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` set to `5` in their environment, unless
the host sets another value. On every container start, `agentdev-runtime` sets
`experimental.subagent_depth` to `5` in OpenCode's `opencode.json`, preserving
every other setting and restoring a changed value.

## Edge cases

- The agent at depth 5 can no longer dispatch: Claude Code does not offer it a
  dispatch tool.
- On Claude Code an agent can dispatch only when its `tools:` list includes
  `Agent` or omits `tools:`.
- A server-side Claude Code flag changes only the default limit; the variable
  overrides it.
- OpenCode's key is experimental and may be renamed.

## Open questions

None open.
