---
type: bug
description: Codex never loads the agentdev catalog's agents/*.agent.md files, so every skill step that dispatches a catalog agent — iwe-plan's Durable Knowledge Auditor gate, pr-feedback-resolution's Principal Engineer delegation — cannot run as written on Codex.
generated:
  by: claude-code/opus-5-5
  at: 2026-10-08T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents
- resource: .agents/plugins/agentdev/.codex-plugin/plugin.json
- resource: .devcontainer/scripts/reinstall-agentdev-codex.sh
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
stage: done
---

# Bug: Codex never loads the agentdev catalog agents

## Symptom

The catalog defines its agents once, as `agents/<stem>.agent.md`. Claude Code
loads them through the plugin, and the OpenCode bridge registers each as a
subagent. Codex does neither: with agentdev 4.2.0 installed and enabled, the
spawnable agent types are Codex's built-ins (`default`, `explorer`, `worker`)
plus the TOML agents in `~/.codex/agents/`, and no catalog agent appears.

So a skill step that dispatches a catalog agent has nothing to dispatch on
Codex. `/agentdev:iwe-plan` step 7 — the fresh-context audit by the
`Durable Knowledge Auditor` that every plan edit funnels through — cannot run,
and `pr-feedback-resolution`'s delegation to the `Principal Engineer` has no
target.

## Reproduction

1. Install the catalog into Codex with
   `.devcontainer/scripts/reinstall-agentdev-codex.sh`; `codex plugin list`
   shows `agentdev@agent-devcontainer installed, enabled`, and the plugin cache
   contains `agents/*.agent.md`.
2. Run `codex exec --sandbox read-only` and ask it to list every `agent_type` it
   can spawn.
3. The list holds `default`, `explorer`, `worker`, and the agents defined in
   `~/.codex/agents/*.toml`; `durable-knowledge-auditor`, `principal-engineer`,
   and the `tdd-*` agents are absent.

## Root cause

Codex defines custom agents only as TOML — `name`, `description`, optional
`sandbox_mode`, and a required `developer_instructions` — read from
`.codex/agents/` in a project or `~/.codex/agents/` for the user. Its plugin
manifest has no field that carries agents: `.codex-plugin/plugin.json` publishes
`skills` only, and Codex ignores the Markdown agent files sitting in the
installed plugin tree. A project-scoped TOML agent with the same body does load
and dispatch.

## Fix

Every Codex install of the catalog runs its `bin/install-codex-agents.py`, which
writes one `~/.codex/agents/agentdev-<stem>.toml` per catalog agent, with the
body as `developer_instructions` and a sandbox mode derived from the agent's
tools, and removes the `agentdev-*.toml` files the catalog no longer produces.
The contract is in [Catalog lifecycle](../spec/catalog-lifecycle.md); the change
shipped through
[Install the catalog agents into Codex](../plans/20261007-codex-catalog-agents.md).

## Key references

Verified anchor points (line numbers as of 2026-10-07):

- `.agents/plugins/agentdev/.codex-plugin/plugin.json:22` — `"skills"`, the only
  content field the Codex manifest publishes
- `.devcontainer/scripts/reinstall-agentdev-codex.sh:65` — `codex plugin add`,
  the install step that carries no agents
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:114` — step 7, the Durable
  Knowledge Auditor dispatch
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:37` —
  Principal Engineer delegation
- `docs/knowledge/data/architecture/module-layout.md:74` — "no `.codex/agents`
  trampoline"
