---
type: codebase
description: The OpenCode catalog bridge and its non-blocking registration of the active Git worktree with configured local CBM.
source: .agents/plugins/agentdev/.opencode-plugin
source_digest: sha256:2e999e0effbf98167be412a15595a0d6a8be35bf5176b9d9394b4354c8e67202
verified:
  by: opencode/gpt-6.1-sol
  at: 2026-10-18T18:50:00Z
stale_after: 2027-01-16
generated:
  by: opencode/gpt-6.1-sol
  at: 2026-10-18T18:50:00Z
sources:
- id: code
  resource: .agents/plugins/agentdev/.opencode-plugin
---

# OpenCode bridge

A two-module OpenCode v1 plugin: `package.json` names `index.ts` as its entry
point, and `index.ts` default-exports `{ id, server }`. It reads the catalog
from the directory above its own and has no runtime dependencies. The design and
the OpenCode behavior it rests on are in [OpenCode catalog
bridge](../../../../architecture/opencode-catalog-bridge.md).

## Public surface

- The default export — the plugin OpenCode loads from a `plugin` entry holding
  this directory's absolute path; its `id` is `agentdev-opencode-bridge`
- `bridge(root, input?, adapters?)` — builds catalog hooks with optional active
  directory, logging client, and injected registration adapters
- `workspace-index.ts` — `registerWorkspace` and the bounded `runCommand`
  adapter
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

The config hook also starts `registerWorkspace` without awaiting it. The helper
gates on enabled local CBM, resolves Git's canonical worktree root, and follows
project-list pages for an exact-root match. An absent root starts the daemon and
submits async indexing with the configured command and environment. An in-flight
map shares registration per root; failures log and release the entry for later
initialization. Commands use argument arrays, a ten-second timeout, and a
combined 1 MiB capture limit; daemon startup discards output.

## Depends on

The OpenCode v1 plugin API (types only, from `@opencode-ai/plugin`), Bun's
`Bun.YAML` and `import.meta.dir`, and the catalog's
`.claude-plugin/plugin.json`, `skills/`, and `agents/`; Node-compatible
filesystem and child-process built-ins; Git and the configured CBM executable
for workspace registration.

## Invariants & gotchas

- Catalog command, agent, and permission keys already defined by the user win.
- The SDK's `Config` type lacks `skills` and `permission.skill`, so the hook
  works on a local `BridgeConfig` shape.
- Tests live in `tests/opencode/` and run under `bun test`, not pytest.

## Key references

Verified anchor points (line numbers as of 2026-10-18):

- `.agents/plugins/agentdev/.opencode-plugin/index.ts:10` — `TOOL_PERMISSIONS`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:25` —
  `SUBAGENT_TOOL_PERMISSIONS`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:58` — `readCatalog`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:104` — `applyCatalog`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:125` — `bridge`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:150` — default export
- `.agents/plugins/agentdev/.opencode-plugin/workspace-index.ts:20` —
  `runCommand`
- `.agents/plugins/agentdev/.opencode-plugin/workspace-index.ts:74` —
  `registerWorkspace`
- `.agents/plugins/agentdev/tests/opencode/` — catalog and workspace Bun suites
