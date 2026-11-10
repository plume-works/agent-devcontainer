# OpenCode catalog bridge Specification

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

The bridge plugin SHALL declare no package dependencies and SHALL use only
type-only imports, Bun built-ins, and, on v2, the host-provided `effect` and
`@opencode/plugin/promise/adapter` modules.

#### Scenario: OpenCode loads the bridge from the read-only staged catalog

- **WHEN** OpenCode loads the bridge from the root-owned `/opt/agentdev` with no
  `node_modules` beside it
- **THEN** the bridge loads and serves the catalog

## Rationale

### One dependency-free bridge serves both OpenCode majors

OpenCode is the catalog's second host and reads the same tree as Claude Code.
One module serves v1 and v2 because a v1 install, such as a consumer image or a
Mac still on v1, would otherwise lose the catalog, and two directories would
make the config know the installed major and duplicate the parser. The staged
catalog is root-owned and read-only, so no `node_modules` can sit beside it.
Commands are namespaced `agentdev:<name>` to match Claude Code and avoid
colliding with other plugins' bare skills; OpenCode's own skill-derived commands
are excluded from `/` autocomplete, which is why the bridge registers ordinary
commands. Catalog text names sibling skills as `/agentdev:<name>`, so the skill
tool strips the prefix rather than more than 100 references being rewritten. A
Claude `tools:` list restricts which tools exist for an agent without
pre-approving them, so mapped tools stay unset.

On v2, deny rules on an agent cannot hold: the config-agent transform runs after
every plugin, appends the global permission rules, and rules match last-wins, so
the devcontainer's `"*": "allow"` would cancel them. The limits are therefore
enforced in `session.hook("context")` and `permission.hook("evaluate")`, keeping
parity with Claude Code, which enforces declared tools under full access. Those
hooks apply only while an agent's `system` is still the catalog body, because v2
merges a user's same-id agent and shows plugins no user config. `execute` stays
allowed by the maintainer's choice, and `browser` stays at v2's default deny.

Host contracts the bridge rests on, to recheck on an OpenCode pin change: v1
loads a directory plugin by absolute path through `package.json` `main`, finds
`skills.paths` added in the `config` hook, accepts `:` in command keys, hands
`tool.execute.before` the arguments before the tool resolves them, hides a
`deny`-permission skill from the model while its command still runs, and denies
`task` and `todowrite` to a dispatched subagent unless its own rules name them.
v2 (2.0.32) loads `{id, effect}` and runs only `effect` when `setup` is also
present, reads v1's `plugin`, `permission`, and `mcp` keys, runs a plugin's
setup once per opened directory, lets a user's skill or command win over a
plugin's, and does not import a v1 OpenAI OAuth login. A changed bridge takes
effect only after OpenCode restarts.

Rejected:

- **oh-my-opencode's Claude compatibility layer.** Not open-source licensed,
  sends telemetry by default, and ties OpenCode to a Claude install.
- **OCX registry distribution.** No namespaced commands or agent mapping, and
  its OpenCode 2 line is a pre-release.
- **Register v2 skills as `agentdev:<name>`.** The model would fail to load a
  skill under its bare name, which the catalog also uses.
- **Drop tool limits on every harness.** Claude Code enforces them.
- **Read the user's config files to skip a replaced agent.** It duplicates v2's
  config discovery.
- **v2 diagnostics through `console`, the plugin's own `Effect.runPromise`, or a
  bridge-owned log file.** None reaches `opencode.log`.
- **Bare `<name>` commands.** They rank higher but differ from Claude Code and
  can collide.
