---
type: spec
description: The contract of the OpenCode bridge plugin that serves the agentdev catalog's skills, namespaced commands, and agents to OpenCode.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-05T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .agents/plugins/agentdev/tests/opencode/bridge.test.ts
---

# OpenCode catalog bridge

## Purpose

Defines what OpenCode sees of the agentdev catalog once the bridge plugin in
`.agents/plugins/agentdev/.opencode-plugin/` is registered: the catalog's
skills, a namespaced slash command per skill, and its agents as subagents
limited to their declared tools. The design is in
[OpenCode catalog bridge](../architecture/opencode-catalog-bridge.md).

## Requirements

### Requirement: OpenCode lists every catalog skill

The bridge plugin SHALL add the catalog's `skills/` directory to OpenCode's
skill search paths, so OpenCode's skill tool lists every catalog skill under the
name in its frontmatter.

#### Scenario: OpenCode starts with the bridge registered

- **WHEN** OpenCode starts with the bridge plugin in its `plugin` config
- **THEN** `opencode debug skill` lists every skill under the catalog's
  `skills/` directory.

### Requirement: every skill is a namespaced slash command

The bridge plugin SHALL register a command `agentdev:<name>` for each catalog
skill. Its description SHALL be the skill's frontmatter description, and its
template SHALL be the skill body followed by the skill's base directory and the
statement that relative paths resolve against it.

#### Scenario: the user types a namespaced command

- **WHEN** the user types `/agentdev:pr-gen-description`
- **THEN** OpenCode sends the `pr-gen-description` skill body with its base
  directory, and a relative `agent-code/` step resolves inside that skill.

#### Scenario: the user types a command prefix

- **WHEN** the user types `/pr` in the OpenCode TUI
- **THEN** the autocomplete offers `agentdev:pr-*` commands.

### Requirement: the skill tool accepts the catalog's namespaced names

The bridge plugin SHALL rewrite a `skill` tool call whose `name` starts with
`agentdev:` to the name without that prefix, and SHALL leave every other tool
call unchanged.

#### Scenario: a skill hands off to a sibling by its namespaced name

- **WHEN** the model calls the skill tool with `name: "agentdev:iwe-plan"`
- **THEN** OpenCode loads the `iwe-plan` skill.

### Requirement: explicit-only skills stay out of model invocation

For every catalog skill whose frontmatter sets `disable-model-invocation: true`,
the bridge plugin SHALL deny that skill to OpenCode's skill tool while keeping
its `agentdev:<name>` command.

#### Scenario: the model tries to load an explicit-only skill

- **WHEN** the model calls the skill tool for a skill with
  `disable-model-invocation: true`
- **THEN** OpenCode refuses the call, and the user can still run the skill as
  `/agentdev:<name>`.

### Requirement: catalog agents are subagents limited to their declared tools

The bridge plugin SHALL register each `agents/<stem>.agent.md` as an OpenCode
subagent named `<stem>`, with the file's description and body as its description
and prompt. Every OpenCode tool permission that the file's `tools:` list does
not map to SHALL be `deny`. A mapped tool SHALL keep the user's configured
permission rather than being set to `allow`.

#### Scenario: a subagent declares a restricted tool list

- **WHEN** OpenCode dispatches the `tdd-red` subagent, whose `tools:` list is
  Bash, Read, Edit, Write, Grep, Glob
- **THEN** its `webfetch`, `websearch`, and `task` permissions are `deny`, and
  `bash` follows the user's configured approval setting.

### Requirement: user configuration takes precedence

The bridge plugin SHALL NOT overwrite a command, agent, or skill permission that
the user's OpenCode configuration already defines under the same key.

#### Scenario: the user defines a command with the same name

- **WHEN** the user's config defines a command `agentdev:pr-open`
- **THEN** OpenCode runs the user's command, not the bridge's.
