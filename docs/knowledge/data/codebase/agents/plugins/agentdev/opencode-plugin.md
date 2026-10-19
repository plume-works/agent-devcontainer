---
type: codebase
description: The OpenCode catalog bridge for OpenCode v1 and v2 and its non-blocking registration of the active Git worktree with configured local CBM.
source: .agents/plugins/agentdev/.opencode-plugin
source_digest: sha256:6ae03618b6be72baadebe3f8672758e65dcd511b5f36cd9a27fd9473b8176da4
verified:
  by: claude-code/opus-5.5
  at: 2026-10-19T02:30:00Z
stale_after: 2027-01-17
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T02:30:00Z
sources:
- id: code
  resource: .agents/plugins/agentdev/.opencode-plugin
---

# OpenCode bridge

A two-module OpenCode plugin for both majors: `package.json` names `index.ts` as
its entry point, and `index.ts` default-exports `{ id, server, effect }` — v1
runs `server`, v2 runs `effect`. It reads the catalog from the directory above
its own and has no runtime dependencies. The design and the OpenCode behavior it
rests on are in [OpenCode catalog
bridge](../../../../architecture/opencode-catalog-bridge.md).

## Public surface

- The default export — the plugin OpenCode loads from a `plugin` entry holding
  this directory's absolute path; its `id` is `agentdev-opencode-bridge`
- `bridge(root, input?, adapters?)` — the v1 hooks, with optional active
  directory, logging client, and injected registration adapters
- `setupBridge(root, ctx, adapters?)` — the v2 setup against a plugin ctx
- `v2Effect(root, ctx, load, adapters?)` — the v2 entry; `load` resolves the
  host's `effect` and `@opencode/plugin/promise/adapter` modules
- `workspace-index.ts` — `registerWorkspace` and the bounded `runCommand`
  adapter
- `TOOL_PERMISSIONS` / `SUBAGENT_TOOL_PERMISSIONS` — v1 tool mapping and denies
- `V2_TOOL_ACTIONS` / `V2_SUBAGENT_ACTIONS` — v2 tool mapping and denies

## How it works

`readCatalog` takes the namespace from `.claude-plugin/plugin.json` and parses
each `skills/*/SKILL.md` and `agents/*.agent.md` with `Bun.YAML.parse` into
skills (name, description, file, body, explicit-only) and agents (stem,
description, body, Claude tools). On v1 the `config` hook appends
`<root>/skills` to `skills.paths`, adds a command `<namespace>:<name>` per skill
whose template is the body plus OpenCode's base-directory footer, adds a
`mode: "subagent"` agent per agent file with `deny` for each unmapped
permission, and denies each `disable-model-invocation` skill under
`permission.skill`, widening a string-valued `permission` first.
`tool.execute.before` strips `<namespace>:` from the skill tool's `name`.

On v2 `effect` requires the two host modules, captures the host's Effect context
with `Effect.contextWith`, and runs `setupBridge` through `fromPromise` with a
log adapter that writes a `service: agentdev` warning through that context.
`setupBridge` registers, without awaiting any of it: an `mcp.transform` callback
that hands the `codebase-memory-mcp` entry to `registerWorkspace`; skills under
their bare names (`autoinvoke: false` when explicit-only); `<namespace>:<name>`
commands whose `execute` re-prompts with the skill appended to `skills`; agents
via `update` as subagents with `system` set to the body; `session` `context` and
`permission` `evaluate` hooks that withhold and deny a catalog agent's unmapped
actions while its `system` is still the catalog body; and an `execute.before`
hook that strips `<namespace>:` from the skill tool's `id`.

`registerWorkspace` gates on a local CBM entry with a nonempty command that
neither `enabled: false` nor `disabled: true` turns off, resolves Git's
canonical worktree root, and follows project-list pages for an exact-root match.
An absent root starts the daemon and submits async indexing with the configured
command and environment. An in-flight map shares registration per root; failures
log and release the entry. Commands use argument arrays, a ten-second timeout,
and a combined 1 MiB capture limit; daemon startup discards output.

## Depends on

The OpenCode v1 plugin API (types only, from `@opencode-ai/plugin`); on v2 the
host's `effect` and `@opencode/plugin/promise/adapter`, required lazily; Bun's
`Bun.YAML` and `import.meta.dir`; the catalog's `.claude-plugin/plugin.json`,
`skills/`, and `agents/`; Node built-ins; Git and the configured CBM executable.

## Invariants & gotchas

- The module imports nothing at runtime beyond Bun and Node built-ins; only
  `effect` calls `require`, and v1 never calls it.
- The default export carries no `setup`: v2 would run only `effect` anyway.
- On v1, keys the user already defined win; on v2, user skills and commands win
  through the host's order, and a catalog agent whose `system` differs from its
  body gets no limits.
- The SDK's `Config` type lacks `skills` and `permission.skill`, so the v1 hook
  works on a local `BridgeConfig` shape.
- Tests live in `tests/opencode/` and run under `bun test`, not pytest.

## Key references

Verified anchor points (line numbers as of 2026-10-19):

- `.agents/plugins/agentdev/.opencode-plugin/index.ts:10,25` — v1 mapping
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:32,47` — v2 mapping
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:127` — `readCatalog`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:159` — `applyCatalog`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:202` — `bridge`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:231` — `setupBridge` (MCP
  callback at 235, agent limits hooks at 296-302)
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:319` — `v2Effect`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:337` — default export
- `.agents/plugins/agentdev/.opencode-plugin/workspace-index.ts:20` —
  `runCommand`
- `.agents/plugins/agentdev/.opencode-plugin/workspace-index.ts:74` —
  `registerWorkspace`
- `.agents/plugins/agentdev/tests/opencode/` — catalog and workspace Bun suites
