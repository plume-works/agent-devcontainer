---
type: someday
description: Let a dispatched catalog agent dispatch another catalog agent, which every IWE workflow avoids today by keeping agents as leaves, if a workflow appears that a leaf design cannot express.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T21:01:06Z
sources:
- resource: .agents/plugins/agentdev/agents
- resource: docs/knowledge/data/architecture/nested-subagent-dispatch.md
---

# Nested dispatch from catalog agents

Every IWE workflow keeps catalog agents as leaves. The user's session or a
coordinator dispatches; `iwe-implementer`, `iwe-verifier`,
`iwe-revision-evaluator`, and `iwe-shipper` never do ([Autonomous Implement
loop](../architecture/autonomous-implement-loop.md), [Fresh-context
Verify](../architecture/fresh-context-verify.md)). That is why each workflow
runs on Claude Code and OpenCode unchanged.

Letting an agent dispatch another would allow a self-contained `iwe-shipper`
that starts its own fresh-context Verify, and coordinators that delegate a whole
plan's loop to one agent. [Nested subagent
dispatch](../architecture/nested-subagent-dispatch.md) records what it costs per
harness: an `Agent` entry in the agent's Claude Code `tools:` list and
OpenCode's `experimental.subagent_depth`, an experimental key OpenCode may
rename or drop.

## Promotion criteria

Promote to a backlog task when a workflow needs an agent to dispatch and a
coordinator in the user's session cannot do the dispatch instead, or when
OpenCode makes nested depth a stable setting.
