---
type: spec
description: The contract of the OpenCode bridge plugin that serves the agentdev catalog's skills, namespaced commands, and agents to OpenCode v1 and v2.
sources:
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .agents/plugins/agentdev/tests/opencode/bridge.test.ts
- resource: .agents/plugins/agentdev/tests/opencode/verify-agent-limits-host.ts
- resource: .agents/plugins/agentdev/.opencode-plugin/package.json
---

# OpenCode catalog bridge

## Purpose

Defines what OpenCode sees of the agentdev catalog once the bridge plugin in
`.agents/plugins/agentdev/.opencode-plugin/` is registered: the catalog's
skills, a namespaced slash command per skill, and its agents as subagents
limited to their declared tools.

## Requirements

### Requirement: one bridge loads in OpenCode v1 and v2

The bridge plugin's default export SHALL carry `id`, a v1 `server` function, and
a v2 `effect` function, so the same `plugin` config entry loads it in either
major version. Only the `effect` function SHALL load OpenCode v2's `effect` and
`@opencode/plugin` modules.

#### Scenario: OpenCode v1 starts with the bridge registered

- **WHEN** OpenCode v1 starts with the bridge in its `plugin` config
- **THEN** it serves the catalog through the v1 hooks.

#### Scenario: OpenCode v2 starts with the bridge registered

- **WHEN** OpenCode v2 starts with the bridge in its `plugin` config
- **THEN** it serves the catalog through the `effect` export, and the bridge's
  warnings reach OpenCode's log.

### Requirement: OpenCode lists every catalog skill

On OpenCode v1 the bridge plugin SHALL add the catalog's `skills/` directory to
OpenCode's skill search paths. On OpenCode v2 it SHALL register every catalog
skill with OpenCode's skill registry. Either way, OpenCode's skill tool lists
every catalog skill under the name in its frontmatter.

#### Scenario: OpenCode starts with the bridge registered

- **WHEN** OpenCode starts with the bridge plugin in its `plugin` config
- **THEN** OpenCode's skill list shows every skill under the catalog's `skills/`
  directory.

### Requirement: every skill is a namespaced slash command

The bridge plugin SHALL register a command `agentdev:<name>` for each catalog
skill, described by the skill's frontmatter description. On OpenCode v1 its
template SHALL be the skill body followed by the skill's base directory and the
statement that relative paths resolve against it. On OpenCode v2 running it
SHALL submit one user message whose text is `/agentdev:<name>` followed, when
arguments are nonempty, by one space and the supplied argument text. The skill
SHALL remain attached as a skill reference rather than pasted into the text.
Existing attachments and their text references, session ID, and delivery mode
SHALL be preserved. The Web UI SHALL show the invocation as a user message,
including when there are no arguments, and retain it after reload.

#### Scenario: the user types a namespaced command on v1

- **WHEN** the user types `/agentdev:pr-gen-description` in OpenCode v1
- **THEN** OpenCode sends the `pr-gen-description` skill body with its base
  directory, and a relative `agent-code/` step resolves inside that skill.

#### Scenario: the user types a namespaced command on v2

- **WHEN** the user types `/agentdev:pr-gen-description for the current branch`
  in OpenCode v2
- **THEN** the chat shows the message
  `/agentdev:pr-gen-description for the current branch` with the
  `pr-gen-description` skill attached, and the model receives the skill body
  with its base directory.

#### Scenario: the user types a command without arguments on v2

- **WHEN** the user types `/agentdev:iwe-ship` without arguments in OpenCode v2
- **THEN** the chat shows one user message containing `/agentdev:iwe-ship`,
  without a trailing space, with the `iwe-ship` skill attached
- **AND** the message remains visible after reloading the Web UI.

#### Scenario: an invocation carries attachments or queued delivery on v2

- **WHEN** a namespaced command has existing file, agent, or skill attachments,
  or requests queued delivery
- **THEN** adding the command name preserves those attachments and the text
  spans they refer to, the session ID, and the requested delivery mode
- **AND** the bridge submits only one user prompt.

#### Scenario: the user types a command prefix

- **WHEN** the user types `/pr` in the OpenCode TUI
- **THEN** the autocomplete offers `agentdev:pr-*` commands.

### Requirement: the skill tool accepts the catalog's namespaced names

The bridge plugin SHALL rewrite a `skill` tool call whose skill argument starts
with `agentdev:` to the name without that prefix, and SHALL leave every other
tool call unchanged. The skill argument is `name` on OpenCode v1 and `id` on
OpenCode v2.

#### Scenario: a skill hands off to a sibling by its namespaced name

- **WHEN** the model calls the skill tool with `agentdev:iwe-plan` as its skill
  argument
- **THEN** OpenCode loads the `iwe-plan` skill.

### Requirement: explicit-only skills stay out of model invocation

For every catalog skill whose frontmatter sets `disable-model-invocation: true`,
the bridge plugin SHALL keep that skill from OpenCode's skill tool — a `deny`
skill permission on v1, `autoinvoke: false` on v2 — while keeping its
`agentdev:<name>` command.

#### Scenario: the model tries to load an explicit-only skill

- **WHEN** the model calls the skill tool for a skill with
  `disable-model-invocation: true`
- **THEN** OpenCode refuses the call, and the user can still run the skill as
  `/agentdev:<name>`.

### Requirement: catalog agents are subagents limited to their declared tools

The bridge plugin SHALL register each `agents/<stem>.agent.md` as an OpenCode
subagent named `<stem>`, with the file's description and body as its description
and prompt. Every OpenCode tool permission that the file's `tools:` list does
not map to SHALL be `deny`, including when the user's global permission allows
every tool: on v1 the mapped set plus `lsp` and `question`; on v2 `shell`,
`read`, `edit`, `write`, `patch`, `grep`, `glob`, `websearch`, `webfetch`,
`subagent`, `skill`, and `question`. On v2 a denied tool SHALL NOT be offered to
the model, and a call to it SHALL be refused. A mapped tool SHALL keep the
user's configured permission rather than being set to `allow`.

#### Scenario: a subagent declares a restricted tool list on v1

- **WHEN** OpenCode v1 dispatches the `iwe-revision-evaluator` subagent, whose
  `tools:` list is Bash, Read, Grep, Glob
- **THEN** its `webfetch`, `websearch`, and `task` permissions are `deny`, and
  `bash` follows the user's configured approval setting.

#### Scenario: a subagent declares a restricted tool list on v2

- **WHEN** OpenCode v2 dispatches the `iwe-revision-evaluator` subagent
- **THEN** it is not offered `webfetch`, `websearch`, `subagent`, `skill`, or
  `question`, and `shell` follows the user's configured approval setting.

#### Scenario: a subagent runs under full access on v2

- **WHEN** the user's global permission is `"*": "allow"` and the
  `iwe-revision-evaluator` subagent calls `webfetch`
- **THEN** OpenCode refuses the call, and `iwe-revision-evaluator` still reads
  files without a prompt.

### Requirement: user configuration takes precedence

The bridge plugin SHALL NOT overwrite a command or skill that the user's
OpenCode configuration already defines under the same key, nor, on v1, a skill
permission the user set. An agent the user defines under a catalog agent's name
SHALL replace the catalog agent: the user's prompt and permissions SHALL apply,
and none of the catalog agent's tool limits. On v1 the bridge SHALL NOT register
its agent under that name; on v2 a field the user's agent leaves unset keeps the
catalog agent's value.

#### Scenario: the user defines a command with the same name

- **WHEN** the user's config defines a command `agentdev:pr-open`
- **THEN** OpenCode runs the user's command, not the bridge's.

#### Scenario: the user defines an agent with a catalog agent's name

- **WHEN** the user's config defines an agent `iwe-revision-evaluator` with its
  own prompt
- **THEN** OpenCode runs the user's prompt, and the agent may use every tool the
  user's permissions allow, including `webfetch`.

### Requirement: the bridge has no runtime dependencies

The bridge plugin SHALL import only types and Bun or Node built-ins at runtime,
and its `package.json` SHALL declare no dependencies, so it loads from the
root-owned, read-only catalog staged in the image, where no `node_modules` can
be installed beside it.

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
- **v2 diagnostics through `console` or the plugin's own `Effect.runPromise`.**
  Neither reaches `opencode.log`.
- **A bridge-owned log file for v2 diagnostics.** It would sit outside
  OpenCode's own log.

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
