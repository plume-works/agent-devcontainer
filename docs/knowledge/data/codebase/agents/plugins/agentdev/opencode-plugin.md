---
type: codebase
description: The OpenCode bridge plugin that translates the agentdev catalog's skills and agents into OpenCode skills paths, commands, permissions, and subagents at startup.
source: .agents/plugins/agentdev/.opencode-plugin
source_digest: sha256:1684e073711dad9dd228fd6798f8999afedebfe4670e278ce03013c9347950bd
verified:
  by: claude-code/opus-5.5
  at: 2026-10-04T12:00:00Z
stale_after: 2027-01-02
generated:
  by: claude-code/opus-5.5
  at: 2026-10-04T12:00:00Z
sources:
- id: code
  resource: .agents/plugins/agentdev/.opencode-plugin
---

# OpenCode bridge

A one-module OpenCode v1 plugin: `package.json` names `index.ts` as its entry
point, and `index.ts` default-exports `{ id, server }`. It reads the catalog
from the directory above its own and has no runtime dependencies. The design and
the OpenCode behavior it rests on are in [OpenCode catalog
bridge](../../../../architecture/opencode-catalog-bridge.md).

## Public surface

- The default export — the plugin OpenCode loads from a `plugin` entry holding
  this directory's absolute path; its `id` is `agentdev-opencode-bridge`
- `bridge(root)` — builds the hooks for a catalog rooted at `root`; the tests
  call it directly
- `TOOL_PERMISSIONS` — Claude tool name to OpenCode permission
- `SUBAGENT_TOOL_PERMISSIONS` — every permission a catalog subagent is denied
  unless its `tools:` list maps to it

## How it works

At `server()` time `readCatalog` takes the namespace from
`.claude-plugin/plugin.json` and parses each `skills/*/SKILL.md` and
`agents/*.agent.md` frontmatter with `Bun.YAML.parse`. The `config` hook then
appends `<root>/skills` to `skills.paths` and adds a command
`<namespace>:<name>` per skill, whose template is the body plus OpenCode's
base-directory footer. It adds a `mode: "subagent"` agent per agent file, keyed
by file stem, with `deny` for each unmapped permission. Each
`disable-model-invocation` skill gets a `permission.skill.<name>: "deny"` entry,
and a string-valued `permission` or `permission.skill` is widened to `{"*": …}`
first. The `tool.execute.before` hook strips `<namespace>:` from the skill
tool's `name`.

## Depends on

The OpenCode v1 plugin API (types only, from `@opencode-ai/plugin`), Bun's
`Bun.YAML` and `import.meta.dir`, and the catalog's
`.claude-plugin/plugin.json`, `skills/`, and `agents/`.

## Invariants & gotchas

- Every assignment uses `??=`, so a key the user's config already defines wins.
- The SDK's `Config` type lacks `skills` and `permission.skill`, so the hook
  works on a local `BridgeConfig` shape.
- Tests live in `tests/opencode/` and run under `bun test`, not pytest.

## Key references

Verified anchor points (line numbers as of 2026-10-04):

- `.agents/plugins/agentdev/.opencode-plugin/index.ts:8` — `TOOL_PERMISSIONS`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:23` —
  `SUBAGENT_TOOL_PERMISSIONS`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:56` — `readCatalog`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:102` — `applyCatalog`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:123` — `bridge`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:138` — default export
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts` — the bun suite
