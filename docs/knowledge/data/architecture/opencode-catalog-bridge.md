---
type: architecture
description: The dependency-free OpenCode catalog bridge that loads in OpenCode v1 and v2, its workspace registration boundary, host contracts, and rejected alternatives.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T02:00:00Z
sources:
- resource: .agents/plugins/agentdev
- resource: .agents/plugins/agentdev/.opencode-plugin/workspace-index.ts
- resource: https://github.com/anomalyco/opencode/tree/0112a92/packages/plugin/src
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/opencode/src/skill/index.ts
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/opencode/src/command/index.ts
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/opencode/src/tool/skill.ts
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/opencode/src/agent/subagent-permissions.ts
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/tui/src/component/prompt/autocomplete.tsx
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/core/src/v1/config/permission.ts
- resource: https://opencode.ai/v2/docs
- resource: .agents/plugins/agentdev/tests/opencode/verify-agent-limits-host.ts
- resource: .agents/plugins/agentdev/tests/opencode/verify-workspace-host.ts
---

# OpenCode catalog bridge

## Decision

OpenCode is the catalog's third host. It reads the same tree as Claude Code and
Codex, `.agents/plugins/agentdev/`, through a **bridge plugin** at
`.agents/plugins/agentdev/.opencode-plugin/`, which sits next to
`.claude-plugin/` and `.codex-plugin/`. The user's OpenCode config lists the
bridge directory by absolute path, and one module serves both OpenCode majors:
its default export is `{id, server, effect}`. v1 runs `server` and ignores
`effect`; v2 runs `effect` and ignores `server`. Both read the catalog through
the same parser.

### On OpenCode v1

At startup the bridge resolves the catalog root from its own location and uses
the v1 plugin `config` hook to translate the tree:

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

### On OpenCode v2

`effect` requires the host's `effect` module and the `fromPromise` adapter from
`@opencode/plugin/promise/adapter` only when v2 calls it, so v1 never loads
either. It captures the host's Effect context and runs the bridge's v2 setup
through `fromPromise`, as the host does for its own setup plugins. The setup
receives a log adapter bound to that context. Through v2's editors the setup
registers:

- every skill under its bare frontmatter name, with its `SKILL.md` path and
  body; `disable-model-invocation` sets `autoinvoke: false`;
- a command `agentdev:<name>` per skill whose `execute` re-prompts the session
  with the user's text and the skill appended to the prompt's `skills`, so the
  chat shows the user's words and a skill chip rather than the skill body;
- every agent through `update` as a subagent with its description and body as
  `system`, adding no permission rules.

The `agentdev:` prefix rewrite runs in `tool.hook("execute.before")` on the
skill tool's `id`. No registration is awaited, because v2 holds every request
until a plugin's setup settles.

**Tool limits are enforced by hooks.** v2's config-agent transform runs after
every plugin transform and appends the global `permission` rules to every agent.
Rules match last-wins, so the devcontainer's full-access `"*": "allow"` would
cancel any deny rule the bridge pushed onto an agent. Instead,
`session.hook("context")` removes a catalog agent's denied tools from what the
model is offered, and `permission.hook("evaluate")` sets `deny` for a denied
action. Approval for an allowed tool is untouched. Claude Code and Codex enforce
a catalog agent's declared tools under full access too; this keeps OpenCode at
parity.

**A user's agent replaces the catalog agent.** Both hooks apply a catalog
agent's limits only while its `system` is still the catalog body, so an agent
the user defines under the same id keeps only the user's permissions. v2 merges
same-id agents and shows plugins no user config, so a field the user's agent
leaves unset, such as `description` or `mode`, keeps the catalog agent's value.
A skill or command the user defines under the same name wins through the host's
own order, so the bridge checks for neither.

The bridge has **no runtime dependencies**. It uses type-only imports and Bun
built-ins, because the staged catalog in the image is root-owned and read-only,
so no `node_modules` can be installed next to it.

## Workspace graph registration

The bridge owns active-workspace registration with CBM alongside catalog
loading. After applying the catalog, its config hook starts an unawaited
best-effort attempt using OpenCode's active directory. On v2 the setup runs once
per directory OpenCode opens and registers an `mcp.transform` callback that
reads the `codebase-memory-mcp` entry without changing it and starts the same
attempt for that directory. Registration requires an enabled local
`mcp["codebase-memory-mcp"]` entry with a nonempty command; an entry is disabled
when v1's `enabled` is `false` or v2's `disabled` is `true`. Missing, disabled,
or remote CBM and non-Git directories are quiet skips. The bridge appends
arguments to the configured command and overlays its environment onto the
inherited environment; it never rewrites MCP settings or broadens allowed roots.
CBM's generated augmentation plugin remains separate.

Git and realpath resolve the canonical worktree root. The helper follows
project-list pagination and compares canonical exact roots; a parent repository
does not cover another checkout, and linked worktrees remain distinct roots. An
absent root starts or joins the daemon and submits asynchronous indexing with
CBM's default mode and no repository snapshot persistence. Indexed projects are
retained. In-process attempts share work per canonical root; cross-process
requests rely on CBM's join semantics.

Catalog availability does not imply graph readiness. Each subprocess is bounded
to ten seconds and captured output to a combined 1 MiB. Daemon startup does not
capture output because a detached daemon can retain startup pipes. Failures
produce an `agentdev` warning in `opencode.log` and never reject config
initialization: on v1 through OpenCode's logging client, on v2 through the
host's Effect logger, at warning level annotated `service: agentdev`, using the
context `effect` captured. A plugin's own `Effect.runPromise` reaches only the
server's console, and v2 discards a plugin's `console` output. A failing CBM
command's diagnostic carries its stdout when stderr is empty, which is where CBM
writes an MCP error such as a root outside the allowed root. A later workspace
initialization may retry; there is no completion polling or periodic retry in
the bridge.

Quit and restart OpenCode after installing a changed bridge or changing its
configuration. Existing sessions retain the already-loaded plugin. A host must
remain alive long enough to submit registration; short-lived debug commands can
exit before background work runs.

## Host behavior the design rests on

These are the OpenCode host contracts the bridge requires. Recheck them when
changing the image's OpenCode pin.

### OpenCode v1

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

### OpenCode v2 (2.0.32)

- **Plugin loading.** A module is `{id, setup}` or `{id, effect}`; v1's
  `{id, server}` alone fails to load. With both `setup` and `effect` present, v2
  runs only `effect`. The host resolves a plugin's `require("effect")` and
  `require("@opencode/plugin/promise/adapter")` to its own copies.
- **Config.** v2 reads the v1 `plugin` key as its plugin list, including an
  absolute directory path; the v1 `permission` object as permission rules,
  `external_directory` included; and a v1 `mcp.<name>` entry as an MCP server,
  `enabled: false` becoming `disabled: true`.
- **Plugin instances.** A plugin's setup runs once per directory OpenCode opens,
  with `ctx.location.directory` set to it. An API request names its directory
  with the `location[directory]` query parameter; without one it targets the
  server's working directory.
- **MCP editor.** `get(name)` returns `{type, command, environment, disabled}`
  for a local server.
- **Agents.** The agent editor has no `add`; `update` creates a missing agent
  from defaults. The config-agent transform runs after every plugin transform,
  appends the global permission rules to every agent, then merges the user's
  same-id agents into the existing entries. A denied tool is not offered to the
  model, and a call to it is refused.
- **Precedence.** A skill or command the user's config defines wins over a
  plugin's under the same name.
- **Hooks.** `session.hook("context")` sees `{agent, tools}` before each model
  request; a deleted tool is not offered. `permission.hook("evaluate")` sees
  `{agent, action, effect}` after the rules are evaluated; `deny` refuses the
  call with `Permission denied: <action>`. The skill tool takes `{id}`.
- **Code mode.** Every agent is offered `execute`, which reaches only tools
  registered for code mode, such as the MCP resource tools; the built-in tools
  are not among them.
- **Logins.** Provider logins live in the SQLite database in OpenCode's data
  directory. An OpenAI OAuth login in a v1 `auth.json` is not imported, so each
  data directory logs in again under v2.

## Tool mapping

On v1:

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

On v2:

| Claude tool     | v2 permission actions    |
| --------------- | ------------------------ |
| `Bash`          | `shell`                  |
| `Read`          | `read`                   |
| `Edit`, `Write` | `edit`, `write`, `patch` |
| `Grep`          | `grep`                   |
| `Glob`          | `glob`                   |
| `WebSearch`     | `websearch`              |
| `WebFetch`      | `webfetch`               |
| `Agent`         | `subagent`               |
| `Skill`         | `skill`                  |
| `TodoWrite`     | none                     |

A catalog subagent is denied every action in this table its `tools:` list does
not map to, plus `question`. `browser` stays at v2's default deny. `execute` is
left alone: the maintainer chose not to deny it.

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
- **A v2-only bridge.** A v1 install, such as a consumer image or a Mac still on
  v1, would lose the catalog.
- **Two plugin directories, one per major.** The config would have to know which
  major is installed, and the catalog parsing would be duplicated.
- **v2 skills registered as `agentdev:<name>` ids.** The model would then fail
  to load a skill under its bare frontmatter name, which the catalog also uses.
- **Deny rules on the v2 agent.** The host appends the global rules after them,
  so full access cancels every catalog agent's tool limits.
- **Dropping tool limits on every harness.** Claude Code and Codex enforce a
  catalog agent's declared tools under full access.
- **Reading the user's config files to skip a replaced agent.** It would
  duplicate v2's config discovery, which plugins cannot query.
- **v2 diagnostics through `console` or the plugin's own `Effect.runPromise`.**
  Neither reaches `opencode.log`.
- **A `setup` export next to `effect`.** v2 runs only `effect`, so it would
  never run.
- **A bridge-owned log file for v2 diagnostics.** It would sit outside
  OpenCode's own log.
- **Bare `<name>` commands.** They would rank higher on `/pr`, but the names
  would differ from Claude Code and Codex and could collide with other plugins'
  bare skills. The namespaced ranking above is usable, so this is not needed.
- **Rewriting catalog text to "the `<name>` skill".** That means rewriting more
  than 100 `/agentdev:<name>` references and less precise invocation in Claude
  Code, for a gap the prefix rewrite closes.
