---
type: architecture
description: Why OpenCode loads the agentdev catalog through a dependency-free bridge plugin shipped inside the catalog, the OpenCode 1.18 host behavior that design rests on, and the alternatives rejected.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-04T12:00:00Z
sources:
- resource: .agents/plugins/agentdev
- resource: https://github.com/anomalyco/opencode/tree/0112a92/packages/plugin/src
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/opencode/src/skill/index.ts
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/opencode/src/command/index.ts
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/opencode/src/tool/skill.ts
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/opencode/src/agent/subagent-permissions.ts
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/tui/src/component/prompt/autocomplete.tsx
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/core/src/v1/config/permission.ts
---

# OpenCode catalog bridge

## Decision

OpenCode is the catalog's third host. It reads the same tree as Claude Code and
Codex, `.agents/plugins/agentdev/`, through a **bridge plugin** at
`.agents/plugins/agentdev/.opencode-plugin/`, which sits next to
`.claude-plugin/` and `.codex-plugin/`. The user's OpenCode config lists the
bridge directory by absolute path. At startup the bridge resolves the catalog
root from its own location and uses the v1 plugin `config` hook to translate the
tree:

- `<root>/skills` is appended to `skills.paths`, so the skill tool lists every
  skill under its bare frontmatter name.
- Every skill becomes a command `agentdev:<name>`. Its template is the skill
  body plus the base-directory footer that OpenCode's own skill commands carry.
- A skill with `disable-model-invocation: true` gets
  `permission.skill.<name> = "deny"`.
- Every `agents/<stem>.agent.md` becomes a subagent `<stem>`. Each OpenCode tool
  that its Claude `tools:` list does not map to is set to `deny`, and mapped
  tools are left unset.
- Keys the user already defines are left alone.

A `tool.execute.before` hook strips an `agentdev:` prefix from the skill tool's
`name` argument, because catalog text names sibling skills as
`/agentdev:<name>`.

The bridge has **no runtime dependencies**. It uses type-only imports and Bun
built-ins, because the staged catalog in the image is root-owned and read-only,
so no `node_modules` can be installed next to it.

## Host behavior the design rests on

These hold for OpenCode 1.18.34, the version the image pins. The pin is the
point at which to recheck them.

- **Plugin loading.** A `plugin` entry holding a directory's absolute path loads
  that directory as a plugin through its `package.json` `main`, including a
  TypeScript entry point. `Bun.YAML.parse` is available inside the plugin.
- **Skill paths.** A `skills.paths` entry added in the `config` hook is
  discovered like one written in the config file, and appears in
  `opencode debug skill`.
- **Commands with `:`.** A command key containing `:` loads, appears in the TUI
  `/` autocomplete, is accepted by `opencode run --command`, and runs its
  template with `$ARGUMENTS` substituted.
- **Autocomplete ranking.** Autocomplete fuzzy-matches name and description and
  shows at most 10 results. With the whole catalog registered, `/pr` shows eight
  of the ten `agentdev:pr-*` commands, behind `/connect` and `/move`. `/pr-`
  shows all ten. OpenCode's own skill-derived commands are excluded from
  autocomplete, which is why the bridge registers ordinary commands.
- **Skill-tool rewrite.** `tool.execute.before` receives the tool's arguments
  before the tool resolves them, and a rewritten `name` is the one OpenCode
  loads.
- **Skill deny.** `permission.skill.<name> = "deny"` removes the skill from the
  `<available_skills>` list the model sees, and makes the skill tool refuse it
  under either spelling. The same skill's `agentdev:<name>` command still runs,
  because commands are not gated by the skill permission.
- **Subagent permissions.** An agent added in the `config` hook with
  `mode: "subagent"` and per-tool `deny` entries appears in
  `opencode debug agent <name>` with those rules after OpenCode's defaults. The
  per-agent `tools` map is deprecated in favor of `permission`.
- **Subagent `task` and `todowrite`.** When the task tool dispatches a subagent,
  OpenCode denies `task` and `todowrite` in that session unless the subagent's
  own ruleset names them. Leaving a mapped Agent or TodoWrite unset therefore
  leaves them denied under OpenCode's defaults. A user who wants a catalog
  subagent to dispatch further subagents grants `task` in their own config.

## Tool mapping

| Claude tool     | OpenCode permission |
| --------------- | ------------------- |
| `Bash`          | `bash`              |
| `Read`          | `read`              |
| `Edit`, `Write` | `edit`              |
| `Grep`          | `grep`              |
| `Glob`          | `glob`              |
| `WebSearch`     | `websearch`         |
| `WebFetch`      | `webfetch`          |
| `Agent`         | `task`              |
| `TodoWrite`     | `todowrite`         |
| `Skill`         | `skill`             |

A catalog subagent is denied every permission in this table that its `tools:`
list does not map to, plus `lsp` and `question`, OpenCode tools no Claude tool
maps to.

A Claude `tools:` list restricts which tools exist for an agent; it does not
pre-approve them. Mapped tools therefore stay unset rather than `allow`, so the
user's approval settings apply.

## Rejected alternatives

- **oh-my-opencode's Claude compatibility layer.** It is licensed under the
  Sustainable Use License, not an open-source licence, and sends telemetry by
  default. It also discovers plugins through Claude Code's
  `installed_plugins.json`, which ties OpenCode to a Claude install.
- **OCX registry distribution.** It copies files into `.opencode/` without
  conversion, so it provides neither namespaced commands nor agent mapping, and
  its OpenCode 2 line is a pre-release.
- **OpenCode v2 embedded skills registered as `agentdev:<name>`.** These are not
  in the released 1.18 plugin API.
- **Bare `<name>` commands.** They would rank higher on `/pr`, but the names
  would differ from Claude Code and Codex and could collide with other plugins'
  bare skills. The namespaced ranking above is usable, so this is not needed.
- **Rewriting catalog text to "the `<name>` skill".** That means rewriting more
  than 100 `/agentdev:<name>` references and less precise invocation in Claude
  Code, for a gap the prefix rewrite closes.
