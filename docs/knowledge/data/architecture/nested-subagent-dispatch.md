---
type: architecture
description: Whether a dispatched subagent can dispatch another one on Claude Code and OpenCode — what each harness allows by default, what gates it, and what a fresh-context dispatch has to specify on each.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T20:58:33Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
---

# Nested subagent dispatch

A workflow that keeps every catalog agent a leaf — only the user's session or a
coordinator dispatches — runs on both harnesses unchanged. A workflow in which a
dispatched agent dispatches another depends on per-harness settings below.

## Host behavior

These hold for Claude Code 2.1.306 and OpenCode 2.1.2. A version bump is the
point at which to recheck them.

| Harness     | Nests by default | What gates it                                                                          | Depth observed            |
| ----------- | ---------------- | -------------------------------------------------------------------------------------- | ------------------------- |
| Claude Code | Yes              | The agent's `tools:` list must include `Agent`, or be omitted so the agent inherits it | 3                         |
| OpenCode    | No               | `experimental.subagent_depth` in `opencode.json`, default `1`                          | 2 with the setting at `2` |

- **Claude Code.** An agent whose `tools:` omits `Agent` reports it has no way
  to dispatch. That is why `iwe-shipper`, whose list is
  `Bash, Read, Edit, Write, Grep, Glob, Skill`, cannot start a fresh-context
  agent of its own. Each subagent transcript's `.meta.json` records `spawnDepth`
  and `parentAgentId`.
- **OpenCode.** At the default depth a nested `task` call fails with "Subagent
  depth limit reached (1). Increase "experimental.subagent_depth" to allow
  nested subagents." The key is experimental, so a design that needs it takes on
  a setting OpenCode may rename or drop.

## Fixture

A scratch git repository holding two agents per harness. `inner` answers with a
marker; `outer` lists its tools, dispatches `inner`, and replies
`NESTED: <answer>` or `NO-DISPATCH: <reason>`. A third Claude agent, `deep`,
dispatches `outer-explicit` to reach depth 3, and `outer-noagent` is the control
with `tools: Read`.

``` markdown
---
name: inner
description: Reports the inner marker. Dispatched only by the spike prompts.
tools: Read
---

Reply with exactly INNER-MARKER-7310 and nothing else. Use no tools.
```

``` markdown
---
name: outer-explicit
description: Dispatches the inner agent and relays its answer. Dispatched only by the spike prompts.
tools: Agent, Read
---

List the names of every tool you have, on one line prefixed TOOLS:.
Then try to dispatch the subagent named "inner" with the prompt "Give your marker."
If it ran, reply NESTED: <its exact answer>. If you have no tool that can
dispatch a subagent, or the dispatch fails, reply NO-DISPATCH: <the reason or error verbatim>.
```

`outer` is the same file without `tools:`. OpenCode takes the same bodies in
`.opencode/agent/<name>.md` with `mode: subagent` and no `name` or `tools`.

The marker alone does not prove a nested run, because `outer` can read `inner`'s
file. The evidence is each harness's record of the nested dispatch: the
transcript metadata named above, or `opencode session export <id>` of the
`outer` session showing a `task` call whose input names `inner`.

``` bash
claude -p 'Use the Agent tool with subagent_type "outer-explicit" and prompt "Give your marker." Relay its final answer verbatim and nothing else.' \
  --model haiku --allowedTools "Agent,Read" --output-format stream-json --verbose </dev/null
opencode run -m openai/gpt-6.1-sol --format json \
  'Use the task tool to dispatch the subagent "outer" with prompt "Give your marker." Relay its final answer verbatim and nothing else.' </dev/null
```

Run the OpenCode command once without and once with
`{"experimental": {"subagent_depth": 2}}` in the fixture's `opencode.json`. Use
`openai/gpt-6.1-sol`: `openai/gpt-6-luna` answered without dispatching at all.
