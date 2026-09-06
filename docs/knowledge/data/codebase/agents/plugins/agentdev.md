---
type: codebase
description: 'The canonical Claude Code and Codex plugin: agents, skills, hooks, bin helpers, and its own test suite, published from this repository and staged into the image.'
source:
- .agents/plugins/agentdev
- .agents/plugins/marketplace.json
- .claude-plugin
source_digest: sha256:61c598fadf6bba61b7da8f34f597b0b62ec7b3e8fe623982a3155984dd059a40
verified:
  by: claude/opus-5
  at: 2026-09-06T00:00:00Z
stale_after: 2026-12-05
generated:
  by: claude/opus-5
  at: 2026-09-06T00:00:00Z
sources:
- id: code
  resource: .agents/plugins/agentdev
---

# The agentdev catalog

One plugin tree consumed two ways. Claude Code reaches it through the
marketplace at `.claude-plugin/marketplace.json` and the plugin manifest at
`.agents/plugins/agentdev/.claude-plugin/plugin.json`; Codex through
`.agents/plugins/marketplace.json` and `.codex-plugin/plugin.json`. Skills are
invoked as `/agentdev:<name>`. The design decisions behind the layout are in
[Module layout](../../../architecture/module-layout.md) and
[Template boundary](../../../architecture/template-boundary.md).

## Contains

[Skills](agentdev/skills.md)

[bin helpers](agentdev/bin.md)

[Plugin tests](agentdev/tests.md)

*Not mapped*: `agents/` — five agent definitions (`Principal Engineer`,
`TDD Red`, `TDD Green`, `TDD Refactor`, `Durable Knowledge Auditor`), one file
each; `hooks/` — `hooks.json` wiring a single `SessionStart` command.

## Public surface

- `/agentdev:<skill>` for every directory under `skills/` with a `SKILL.md` (36
  at this commit)
- Agent names, addressed as `principal-engineer`, `tdd-red`, `tdd-green`,
  `tdd-refactor`, `durable-knowledge-auditor`
- `bin/` on `PATH` while the plugin is enabled — the shell helpers plus
  `result_codes.py`, which a Python skill script imports from there
- `hooks/session-start.sh` — brings up the project devcontainer, only when
  `CLAUDE_CODE_REMOTE=true`
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

Verified anchor points (line numbers as of 2026-09-06):

- `.claude-plugin/marketplace.json:13` — the published plugin version
- `.agents/plugins/agentdev/.claude-plugin/plugin.json:3` — Claude manifest
  version
- `.agents/plugins/agentdev/.codex-plugin/plugin.json:3` — Codex manifest
  version
- `.agents/plugins/agentdev/hooks/session-start.sh:5` — the remote-only gate
- `.agents/plugins/agentdev/hooks/session-start.sh:29` — `devcontainer up`
- `docker/desktop/agent-desktop.Dockerfile:18` — `AGENTDEV_PLUGIN_VERSION`, the
  fourth pin
