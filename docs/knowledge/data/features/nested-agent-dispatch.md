---
type: feature
stage: accepted
description: Agents in the devcontainer can dispatch subagents that dispatch further subagents, up to depth 5, on both Claude Code and OpenCode.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-03T06:00:00Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/claude_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: docs/knowledge/data/architecture/nested-subagent-dispatch.md
- resource: docs/knowledge/data/someday/nested-catalog-agent-dispatch.md
---

# Nested agent dispatch

## Purpose

Catalog workflows need an agent to start a fresh-context agent of its own, such
as `iwe-shipper` dispatching `iwe-verifier`. Claude Code nests to depth 3 by
default, and OpenCode refuses any nesting at its default
`experimental.subagent_depth` of 1.

## Behaviour

On every container start, `agentdev-runtime` sets
`env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` to `5` in `~/.claude/settings.json`
and `experimental.subagent_depth` to `5` in OpenCode's `opencode.json`. Every
other setting in both files is preserved, and a changed value is restored.

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
