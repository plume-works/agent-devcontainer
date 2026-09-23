---
type: codebase
description: 'The canonical Claude Code and Codex plugin: agents, skills, hooks, bin helpers, and its own test suite, published from this repository and staged into the image.'
source:
- .agents/plugins/agentdev
- .agents/plugins/marketplace.json
- .claude-plugin
source_digest: sha256:459f562a17472d5b48845b3f3d859bdc261a7b7669d4fddea09043b949150fe2
verified:
  by: codex/gpt-5
  at: 2026-09-23T22:25:36Z
stale_after: 2026-12-21
generated:
  by: claude-code/opus-5
  at: 2026-09-22T21:30:00Z
sources:
- id: code
  resource: .agents/plugins/agentdev
---

# The agentdev catalog

One plugin tree consumed two ways. Claude Code reaches it through the
marketplace at `.claude-plugin/marketplace.json` and the plugin manifest at
`.agents/plugins/agentdev/.claude-plugin/plugin.json`; Codex through
`.agents/plugins/marketplace.json` and `.codex-plugin/plugin.json`. The Claude
marketplace also publishes `self-improve`, which ships no Codex manifest, so the
two ecosystems publish different plugin sets. Skills are invoked as
`/agentdev:<name>`. The design decisions behind the layout are in
[Module layout](../../../architecture/module-layout.md) and
[Template boundary](../../../architecture/template-boundary.md).

## Contains

[Skills](agentdev/skills.md)

[bin helpers](agentdev/bin.md)

[Plugin tests](agentdev/tests.md)

*Not mapped*: `agents/` — five agent definitions (`Principal Engineer`,
`TDD Red`, `TDD Green`, `TDD Refactor`, `Durable Knowledge Auditor`), one file
each; `hooks/` — Claude's `hooks.json` wires a single `SessionStart` command,
while Codex's `codex-hooks.json` declares no hooks.

## Public surface

- `/agentdev:<skill>` for every directory under `skills/` with a `SKILL.md` (36
  at this commit)
- Agent names, addressed as `principal-engineer`, `tdd-red`, `tdd-green`,
  `tdd-refactor`, `durable-knowledge-auditor`
- `bin/` on `PATH` while the plugin is enabled — the shell helpers plus
  `result_codes.py`, which a Python skill script imports from there
- `hooks/session-start.sh` — brings up the project devcontainer for Claude Code
  web sessions, only when `CLAUDE_CODE_REMOTE=true`
- `hooks/codex-hooks.json` — explicitly disables Codex hook discovery for this
  Claude-specific startup hook
- `version` — `3.3.0`, declared identically in both plugin manifests, the
  marketplace entry, and the Dockerfile pin

## How it works

The marketplace manifests point at `./.agents/plugins/agentdev` as a local
source. The image build copies `.claude-plugin/` and `.agents/` whole into
`/opt/agentdev` and installs from there
([agentic_tools](../../ansible/roles/agentic_tools.md)); the devcontainer
lifecycle installs again over the mounted volumes and, for this repository only,
re-registers the workspace copy on attach
([lifecycle scripts](../../devcontainer/scripts.md)). Codex reads the same
files; there is no generated mirror.

## Depends on

`git`, an authenticated `gh`, Docker for Super-Linter, `uv` for the Python
skills — whatever the skill in use shells out to. Validation comes from the
[validator package](../../py_packages/validate_agent_files.md).

## Invariants & gotchas

- No link in any shipped Markdown may resolve outside the plugin root, and no
  skill body may contain a literal `.claude/skills/...` path; the validator
  enforces both because the plugin runs from a cache, not this checkout.
- The four version pins move together or the image build fails.
- `.codex/` and `.claude/` at the repository root are project configuration,
  never a copy of the catalog.

## Key references

Verified anchor points (line numbers as of 2026-09-23):

- `.claude-plugin/marketplace.json:13` — the published plugin version
- `.agents/plugins/agentdev/.claude-plugin/plugin.json:3` — Claude manifest
  version
- `.agents/plugins/agentdev/.codex-plugin/plugin.json:3` — Codex manifest
  version
- `.agents/plugins/agentdev/.codex-plugin/plugin.json:23` — Codex-specific hook
  configuration
- `.agents/plugins/agentdev/hooks/codex-hooks.json:2` — empty Codex hook set
- `.agents/plugins/agentdev/hooks/session-start.sh:5` — the Claude remote-only gate
- `.agents/plugins/agentdev/hooks/session-start.sh:29` — `devcontainer up`
- `docker/desktop/agent-desktop.Dockerfile:18` — `AGENTDEV_PLUGIN_VERSION`, the
  fourth pin
