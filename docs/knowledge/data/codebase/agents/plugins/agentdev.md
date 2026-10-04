---
type: codebase
description: 'The canonical Claude Code, Codex, and OpenCode plugin: agents, skills, bin helpers, the OpenCode bridge, and its own test suite, published from this repository and staged into the image.'
source:
- .agents/plugins/agentdev
- .agents/plugins/marketplace.json
- .claude-plugin
source_digest: sha256:44825a3d82558f88122193151d61872a74bc91e0e6af315e5e36c5f4b31e74d5
verified:
  by: claude-code/opus-5.5
  at: 2026-10-04T12:00:00Z
stale_after: 2027-01-02
generated:
  by: claude-code/opus-5.5
  at: 2026-10-04T12:00:00Z
sources:
- id: code
  resource: .agents/plugins/agentdev
---

# The agentdev catalog

One plugin tree consumed three ways. Claude Code reaches it through the
marketplace at `.claude-plugin/marketplace.json` and the plugin manifest at
`.agents/plugins/agentdev/.claude-plugin/plugin.json`; Codex through
`.agents/plugins/marketplace.json` and `.codex-plugin/plugin.json`; OpenCode
through the bridge plugin in `.opencode-plugin/`, which a user's OpenCode config
lists by absolute path. The Claude marketplace also publishes `self-improve`,
which ships no Codex manifest, so the two ecosystems publish different plugin
sets. Skills are invoked as `/agentdev:<name>`. The design decisions behind the
layout are in [Module layout](../../../architecture/module-layout.md) and
[Template boundary](../../../architecture/template-boundary.md).

## Contains

[Skills](agentdev/skills.md)

[OpenCode bridge](agentdev/opencode-plugin.md)

[bin helpers](agentdev/bin.md)

[Plugin tests](agentdev/tests.md)

*Not mapped*: `agents/` — five agent definitions (`Principal Engineer`,
`TDD Red`, `TDD Green`, `TDD Refactor`, `Durable Knowledge Auditor`), one file
each.

## Public surface

- `/agentdev:<skill>` for every directory under `skills/` with a `SKILL.md` (38
  at this commit)
- Agent names, addressed as `principal-engineer`, `tdd-red`, `tdd-green`,
  `tdd-refactor`, `durable-knowledge-auditor`
- `bin/` on `PATH` while the plugin is enabled — the shell helpers plus
  `result_codes.py`, which a Python skill script imports from there
- `.opencode-plugin/` — the directory an OpenCode `plugin` entry names
- `version` — `4.2.0`, declared identically in both plugin manifests, the
  marketplace entry, and the Dockerfile pin

## How it works

The marketplace manifests point at `./.agents/plugins/agentdev` as a local
source. The image build copies `.claude-plugin/` and `.agents/` whole into
`/opt/agentdev` and installs from there
([agentic_tools](../../ansible/roles/agentic_tools.md)); the devcontainer
lifecycle installs again over the mounted volumes and, for this repository only,
re-registers the workspace copy on attach
([lifecycle scripts](../../devcontainer/scripts.md)). Codex reads the same
files; there is no generated mirror. OpenCode reads them too, translated at
startup by the bridge rather than copied.

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

Verified anchor points (line numbers as of 2026-10-04):

- `.claude-plugin/marketplace.json:13` — the published plugin version
- `.agents/plugins/agentdev/.claude-plugin/plugin.json:3` — Claude manifest
  version
- `.agents/plugins/agentdev/.codex-plugin/plugin.json:3` — Codex manifest
  version
- `docker/desktop/agent-desktop.Dockerfile:18` — `AGENTDEV_PLUGIN_VERSION`, the
  fourth pin
