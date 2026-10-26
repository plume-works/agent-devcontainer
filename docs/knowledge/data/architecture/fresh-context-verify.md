---
type: architecture
description: Why Verify's rulebook lives in the iwe-verifier catalog agent, which the iwe-verify skill dispatches with a conversation-free prompt and iwe-shipper follows in place, so every Verify run judges the code from a fresh context.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
---

# Fresh-context Verify

## Decision

Verify's rulebook is defined once, as the catalog agent `iwe-verifier` in
`.agents/plugins/agentdev/agents/`, the way the Ship and Implement rulebooks
live in `iwe-shipper` and `iwe-implementer` ([Explicit-only workflow
agents](explicit-only-workflow-agents.md)). The agent body is the rulebook on
all three harnesses: the Claude Code plugin loads it, the Codex installer
renders it into `agentdev-iwe-verifier.toml`, and the OpenCode bridge registers
it as a subagent.

Every Verify run starts from a fresh context, so its verdict rests on the code
and the graph, never on what a conversation asserted. `/agentdev:iwe-verify` is
a thin router with two routes:

- **From a session** — the skill builds a prompt carrying only the plan key (or
  audit mode) and the user's approvals quoted verbatim, dispatches
  `iwe-verifier` forwarding no conversation, and re-posts its report. An
  approval the verifier needs comes back as `Needs decision`, and the user
  re-runs the skill granting it.
- **From inside `iwe-shipper`** — the Shipper is already a fresh context and
  stays a leaf, so the skill tells it to read the `iwe-verifier` rulebook and
  follow it in place. The Shipper reaches the rulebook through the skill because
  a skill can link the agent file plugin-relatively on every harness, while an
  agent body rendered into a Codex TOML cannot.

`iwe-verifier`'s tools are `Bash, Read, Write, Grep, Glob, Skill`. `Write` makes
the Codex installer give it a `workspace-write` sandbox, which a
`## Verification` command that writes caches or a virtual environment needs.
Report-only is a rule of the rulebook, not a tool boundary.

A verification command whose effects reach beyond the working tree runs only
under a quoted approval that names it; otherwise Verify stops before it and
reports the exact command — the Shipper's rule, applied to both routes.

`/agentdev:iwe-verify` stays model-invocable: Verify mutates nothing, and a
workflow that wants a fresh-context verdict dispatches the agent, not the skill,
so an explicit-only gate would protect nothing.

## Rejected alternatives

- **Give `iwe-shipper` the Agent tool and nest the dispatch.** OpenCode refuses
  a nested dispatch at its default depth, and raising it takes an experimental
  key ([Nested subagent dispatch](nested-subagent-dispatch.md)).
- **Keep the rulebook in the skill behind a thin agent**, as the Durable
  Knowledge Auditor does with `iwe-audit`. The skill would then be both the
  rulebook and the entry point that must dispatch, so a session loading it
  already holds the rules it would run inline.
- **A Codex sandbox override key read by the installer.** The maintainer chose
  `Write` in the tools list over a new installer contract.
- **Make `/agentdev:iwe-verify` explicit-only.** It would gate a skill that
  mutates nothing and that no dispatching workflow invokes.
