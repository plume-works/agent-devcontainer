---
type: spec
description: The contract of the OpenCode bridge plugin that serves the agentdev catalog's skills, namespaced commands, and agents to OpenCode v1 and v2.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T14:33:31Z
sources:
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .agents/plugins/agentdev/tests/opencode/bridge.test.ts
- resource: .agents/plugins/agentdev/tests/opencode/verify-agent-limits-host.ts
---

# OpenCode catalog bridge

## Purpose

Defines what OpenCode sees of the agentdev catalog once the bridge plugin in
`.agents/plugins/agentdev/.opencode-plugin/` is registered: the catalog's
skills, a namespaced slash command per skill, and its agents as subagents
limited to their declared tools. The design is in [OpenCode catalog
bridge](../architecture/opencode-catalog-bridge.md).

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
SHALL send the user's text as the message, with the skill attached as a skill
reference rather than pasted into the text.

#### Scenario: the user types a namespaced command on v1

- **WHEN** the user types `/agentdev:pr-gen-description` in OpenCode v1
- **THEN** OpenCode sends the `pr-gen-description` skill body with its base
  directory, and a relative `agent-code/` step resolves inside that skill.

#### Scenario: the user types a namespaced command on v2

- **WHEN** the user types `/agentdev:pr-gen-description for the current branch`
  in OpenCode v2
- **THEN** the chat shows the message `for the current branch` with the
  `pr-gen-description` skill attached, and the model receives the skill body
  with its base directory.

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

- **WHEN** OpenCode v1 dispatches the `tdd-red` subagent, whose `tools:` list is
  Bash, Read, Edit, Write, Grep, Glob
- **THEN** its `webfetch`, `websearch`, and `task` permissions are `deny`, and
  `bash` follows the user's configured approval setting.

#### Scenario: a subagent declares a restricted tool list on v2

- **WHEN** OpenCode v2 dispatches the `tdd-red` subagent
- **THEN** it is not offered `webfetch`, `websearch`, `subagent`, `skill`, or
  `question`, and `shell` follows the user's configured approval setting.

#### Scenario: a subagent runs under full access on v2

- **WHEN** the user's global permission is `"*": "allow"` and the `tdd-red`
  subagent calls `webfetch`
- **THEN** OpenCode refuses the call, and `tdd-red` still reads and edits files
  without a prompt.

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

- **WHEN** the user's config defines an agent `tdd-red` with its own prompt
- **THEN** OpenCode runs the user's prompt, and the agent may use every tool the
  user's permissions allow, including `webfetch`.
