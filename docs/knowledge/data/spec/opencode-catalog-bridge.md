---
type: spec
description: The contract of the OpenCode bridge plugin that serves the agentdev catalog's skills, namespaced commands, and agents to OpenCode v1 and v2.
sources:
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .agents/plugins/agentdev/tests/opencode/bridge.test.ts
- resource: .agents/plugins/agentdev/tests/opencode/verify-agent-limits-host.ts
- resource: .agents/plugins/agentdev/.opencode-plugin/package.json
- resource: .agents/plugins/self-improve/selfimprove/reviewer.py
- resource: .agents/plugins/self-improve/hooks/hooks.json
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
---

# OpenCode catalog bridge

## Purpose

Defines what OpenCode sees of the agentdev catalog once the bridge plugin in
`.agents/plugins/agentdev/.opencode-plugin/` is registered: the catalog's
skills, a namespaced slash command per skill, and its agents as subagents
limited to their declared tools.

## Requirements

### Requirement: the bridge has no runtime dependencies

The bridge plugin SHALL import only types and Bun or Node built-ins at runtime,
and its `package.json` SHALL declare no dependencies, so it loads from the
root-owned, read-only catalog staged in the image, where no `node_modules` can
be installed beside it. It SHALL resolve the catalog root from its own location,
the plugin directory above `.opencode-plugin/`, so the same bridge serves the
staged catalog and a checkout's catalog.

#### Scenario: OpenCode loads the staged catalog's bridge

- **WHEN** OpenCode starts with the bridge directory of the image's staged
  catalog in its `plugin` config
- **THEN** the bridge loads without installing any package.

## Rationale

### OpenCode reads the catalog through a bridge plugin

OpenCode is the catalog's second host and reads the same tree as Claude Code,
`.agents/plugins/agentdev/`, through a bridge plugin beside `.claude-plugin/`
that translates skills, commands, and agents when OpenCode starts.

Rejected:

- **oh-my-opencode's Claude compatibility layer.** It is licensed under the
  Sustainable Use License, not an open-source licence, sends telemetry by
  default, and discovers plugins through Claude Code's `installed_plugins.json`,
  which ties OpenCode to a Claude install.
- **OCX registry distribution.** It copies files into `.opencode/` without
  conversion, so it provides neither namespaced commands nor agent mapping.

### The bridge serves only the agentdev catalog

The bridge translates the agentdev plugin alone. It maps no hooks, because the
agentdev catalog ships none, and it is registered in the OpenCode config by its
absolute path, never published to npm or an OpenCode marketplace.

Rejected:

- **Serving the `self-improve` plugin to OpenCode.** Its reviewer builds a
  Claude-only command line, and its hook events, including the typed-command
  authorization `UserPromptExpansion` provides, have no OpenCode mapping.

### One module serves OpenCode v1 and v2

The bridge's default export carries both v1's `server` and v2's `effect`: v1
ignores `effect`, and v2, given both, runs only `effect`. Both read the catalog
through one parser. The v2 setup runs through the host's own `fromPromise`
adapter, so its failures reach `opencode.log`, and it awaits no registration,
because v2 holds every request until a plugin's setup settles.

Rejected:

- **A v2-only bridge.** A v1 install, such as a consumer image or a Mac still on
  v1, would lose the catalog.
- **Two plugin directories, one per major.** The config would have to know which
  major is installed, and the catalog parsing would be duplicated.
- **A `setup` export next to `effect`.** v2 runs only `effect`, so it would
  never run.
- **Running the v2 setup through `console` reporting or the plugin's own
  `Effect.runPromise`.** Neither reaches `opencode.log`.

### Skills keep their bare names; commands are namespaced

Skills register under their bare frontmatter names, commands as
`agentdev:<name>`, and the skill tool strips an `agentdev:` prefix, because the
catalog's text names sibling skills as `/agentdev:<name>`. Ordinary commands are
registered because OpenCode excludes its own skill-derived commands from
autocomplete.

Rejected:

- **v2 skills registered as `agentdev:<name>` ids.** The model would then fail
  to load a skill under its bare frontmatter name, which the catalog also uses.
- **Bare `<name>` commands.** They would rank higher on `/pr`, but would differ
  from Claude Code's names and could collide with other plugins' bare skills;
  the namespaced ranking is usable.
- **Rewriting catalog text to "the `<name>` skill".** It rewrites more than 100
  `/agentdev:<name>` references and makes invocation in Claude Code less
  precise, for a gap the prefix rewrite closes.

### v2 enforces tool limits in hooks

Claude Code enforces a catalog agent's declared tools under full access, and the
bridge keeps OpenCode at parity. On v2 the host appends the global `permission`
rules to every agent after all plugin transforms, and rules match last-wins, so
the bridge removes denied tools in `session.hook("context")` and denies their
actions in `permission.hook("evaluate")`. A Claude `tools:` list restricts which
tools exist without pre-approving them, so mapped tools keep the user's approval
settings. `browser` stays at v2's default deny, and `execute`, which reaches
only code-mode tools, is left alone by the maintainer's choice.

Rejected:

- **Deny rules on the v2 agent.** The host appends the global rules after them,
  so full access cancels every catalog agent's tool limits.
- **Dropping tool limits on every harness.** Claude Code enforces a catalog
  agent's declared tools under full access.

### A user's agent is recognized by its prompt

On v2 the hooks apply a catalog agent's limits only while its `system` is still
the catalog body, because v2 merges same-id agents and shows plugins no user
config.

Rejected:

- **Reading the user's config files to skip a replaced agent.** It would
  duplicate v2's config discovery, which plugins cannot query.

### Skills reach v2 only through the bridge's skill registration

The catalog's skills reach OpenCode v2 only through the bridge's skill
transform.

Rejected:

- **v2's native skill roots.** `.agents/plugins/agentdev/skills` is not one of
  them, and native `.agents/skills` discovery is not used for the catalog.

### A v2 command echoes its invocation in the user's own message

The invocation is shown by prefixing the user's message with `/agentdev:<name>`,
because the invocation belongs to the user's message; the skill travels as an
attached reference. OpenCode's command parser has already stripped the
whitespace around the arguments, so the bridge can restore only the command name
and the argument text, joined by exactly one space.

Rejected:

- **An assistant acknowledgment of the invocation.** The invocation is the
  user's, not the assistant's.
- **A second synthetic message.** It splits one invocation across two messages.
- **Pasting the skill body into the chat.** The skill is attached, not quoted.
