---
type: plan
created: 2026-10-18
release:
- features/opencode-catalog-host
- features/opencode-web-coder-autostart
description: Ship OpenCode v2 as the image's OpenCode, serve the agentdev catalog to it through a bridge that loads in both v1 and v2, run the Coder web UI with v2's always-on server password, and keep OpenCode logins per worktree.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-18T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .devcontainer/scripts/opencode-web-start.sh
- resource: .devcontainer/scripts/link-opencode-auth.sh
- resource: ansible/roles/agentic_tools/defaults/main.yml
- resource: scripts/e2e/20261007-agent-owned-ship-implement/run.sh
- resource: https://opencode.ai/v2/docs
---

# Make OpenCode v2 the devcontainer default

## Context

[OpenCode as a catalog host](../features/opencode-catalog-host.md) and [OpenCode
web UI autostart on Coder](../features/opencode-web-coder-autostart.md) are the
features this plan changes. Both are built on OpenCode v1 (`opencode-ai`, pinned
at 1.19.3). In v1 a command's template is sent as the user's message, so every
`/agentdev:<name>` command posts the whole skill body into the chat; OpenCode's
own skill-derived commands do the same. OpenCode v2 (`@opencode/cli`) attaches a
skill to a message as a structured skill reference instead, and the chat shows
only the user's text and a skill chip.

The current design is in [OpenCode catalog
bridge](../architecture/opencode-catalog-bridge.md) and [Agent auth
persistence](../architecture/agent-auth-persistence.md); the contracts are
[OpenCode catalog bridge](../spec/opencode-catalog-bridge.md), [OpenCode
web](../spec/opencode-web.md), and [Coder IDE baseline
template](../spec/coder-ide-baseline.md).

[Ship a standalone OpenCode
container](20261017-standalone-opencode-container.md) builds on
`link-opencode-auth.sh` and on Coder's `opencode web`, both of which this plan
replaces. The maintainer chose to ship this plan first; the standalone plan is
revised for v2 before it is implemented.

OpenCode v2.0.32 behavior this plan relies on:

- **Plugin loading.** A plugin module is `{id, setup(ctx)}` or `{id, effect}`;
  v1's `{id, server}` alone fails to load. v2 ignores `server` and v1 ignores
  `setup`, so one default export carrying all three loads in both.
- **Config.** v2 reads the v1 `plugin` key as its `plugins` list, and accepts an
  absolute directory path as an entry.
- **Skills.** `ctx.skill.transform` takes an editor whose
  `add({id, name, description, autoinvoke, path, content})` registers a skill;
  `autoinvoke: false` keeps it out of model invocation. The catalog's
  `.agents/plugins/agentdev/skills` is not one of v2's native skill roots.
- **Commands.** `ctx.command.transform` takes an editor whose
  `add({name, description, execute})` registers a command; `execute` receives
  `{sessionID, prompt: {text, files, agents, skills}, delivery}` and can call
  `ctx.session.prompt` with the skill appended to `skills`.
- **Agents.** `ctx.agent.transform` has no `add`; `update(id, fn)` creates a
  missing agent from defaults whose permission ruleset starts with allow `*`.
  `{action, resource: "*", effect: "deny"}` rules pushed after the defaults take
  effect, and a denied tool is withheld from the model. Subagents appear in the
  `subagent` tool's list next to `explore` and `general`.
- **Tool permissions.** `shell`, `read`, `edit`, `write`, `patch`, `grep`,
  `glob`, `websearch`, `webfetch`, `subagent`, `skill`, `question`, and
  `browser` (denied by default). There is no to-do or LSP tool. Every agent is
  offered `execute`, v2's code-mode tool.
- **Hooks.** `ctx.tool.hook("execute.before", fn)` sees `{tool, input}` and can
  replace `input`. Awaiting a hook registration inside `setup` blocks plugin
  activation, and every request waits on activation.
- **Server.** `opencode serve --port --hostname` serves the API and the web UI;
  there is no `web` command. The server always requires a password: it uses
  `OPENCODE_SERVER_PASSWORD`, or a random one when that is unset. Basic auth
  uses the user `opencode`.
- **Logins.** Provider logins live in the SQLite database in OpenCode's data
  directory; `auth.json` is read once, as an import.
- **CLI.** `opencode run` sends plain text only, with no `--command`.
  `opencode api session.command` runs a command against a session.
- **Install.** Bun blocks the package's postinstall, which fetches the platform
  binary, until the package is trusted. The package installs `opencode` and
  `opencode2`.

## Approach

**One bridge module for both majors.** The default export becomes
`{id, server, setup}`. `server` keeps today's v1 hooks unchanged. `setup` reads
the same catalog and registers it through v2's editors: each skill under its
bare name (`autoinvoke: false` for `disable-model-invocation`), each skill as a
command `agentdev:<name>` whose `execute` re-prompts the session with the user's
text and the skill appended to `skills`, and each agent through `update` as a
subagent with deny rules. The `agentdev:` prefix rewrite moves to
`ctx.tool.hook("execute.before")`, registered without being awaited. Keys the
user already defined are left alone, as in v1. The catalog parsing that both
paths share is factored out once.

The v2 tool mapping:

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
left alone: the maintainer chose not to deny it, so catalog subagents get it
whatever their `tools:` list says.

**Image ships v2.** `agentic_tools_bun_packages` installs `@opencode/cli`
instead of `opencode-ai`, trusted so its postinstall fetches the binary, with
its Renovate annotation moved to the new package. The bridge registration
(`plugin` key in `~/.config/opencode/opencode.json`) is unchanged, since v2
reads that key.

**Web UI on v2.** `opencode-web-start.sh` runs `opencode serve` instead of
`opencode web`. With a non-empty `OPENCODE_SERVER_PASSWORD` it binds `0.0.0.0`
as today. Without one, the script generates a random password once into
`~/.local/share/opencode/agentdev-server-password` (mode `0600`, on the
per-worktree `agentdev-opencode` volume), binds `127.0.0.1`, and the pane reads
the file into `OPENCODE_SERVER_PASSWORD` itself, so the password never appears
on a command line or in the log. The printed line names the file next to the
link.

**Per-worktree logins.** `link-opencode-auth.sh`, its tests, its calls, and the
`/root/.agents-auth/opencode` directory go away. Logins live in v2's database on
the `agentdev-opencode` volume: they survive a rebuild, and each worktree logs
in once. The maintainer accepted losing cross-worktree login sharing.

**E2E harness on v2.** `run.sh` starts each OpenCode scenario through
`opencode api session.command` with the `agentdev:<name>` command instead of
`opencode run --command`, and reads subagent dispatches from the `subagent` tool
instead of `task`.

Assumptions:

- The web UI keeps v1's `/<base64url(directory)>/session` route and serves
  `/site.webmanifest` without the password. Task 7 checks both; a different
  route or an authenticated manifest sends the plan back to revise mode.
- An `auth.json` symlink left on an existing `agentdev-opencode` volume is
  harmless: v2 imports it once and never writes it.

Rejected:

- **v2-only bridge.** A v1 install, such as a consumer image or a Mac still on
  v1, would lose the catalog entirely.
- **Two plugin directories, one per major.** The config would have to know which
  major is installed, and the catalog parsing would be duplicated.
- **Registering skills as `agentdev:<name>` ids.** The model would then fail to
  load a skill under its bare frontmatter name, which the catalog also uses.
- **Keeping `auth.json` as a shared login seed.** v2 never writes it, so the
  shared file only carries stale v1 logins.
- **Requiring `OPENCODE_SERVER_PASSWORD` for the web UI.** Workspaces without
  the Coder secret would lose the web UI.
- **Printing the generated password in the agent-start log.** Anyone who can
  read that log would have it.

## Implementation Steps

### Task 1: Register the catalog through v2's plugin API

**Files:** Modify: `.agents/plugins/agentdev/.opencode-plugin/index.ts`,
`.agents/plugins/agentdev/tests/opencode/bridge.test.ts`

- [ ] Tests first, against a fake v2 `ctx` whose editors record calls:
  - every catalog skill is added under its bare name with its description,
    `SKILL.md` path, and body; explicit-only skills carry `autoinvoke: false`;
  - every skill is added as command `agentdev:<name>`; its `execute` calls
    `session.prompt` with the invocation's text, files, agents, and delivery,
    and the invocation's skills plus `{id: <name>}`;
  - every agent is updated as a `subagent` with its description, body as
    `system`, and a deny rule for each action of the mapping table its `tools:`
    list omits plus `question`; never `execute` or `browser`;
  - a skill, command, or agent the user already defined is not touched;
  - the `execute.before` tool hook rewrites a `skill` call's `agentdev:<name>`
    to `<name>` and leaves every other call unchanged;
  - `setup` resolves without waiting on the hook registration;
  - the default export carries `id`, `server`, and `setup`, and `server` still
    returns the v1 hooks the existing tests cover.
- [ ] Implement until the tests pass, keeping the module free of runtime
  dependencies.

### Task 2: Install OpenCode v2 in the image

**Files:** Modify: `ansible/roles/agentic_tools/defaults/main.yml`,
`ansible/roles/agentic_tools/tasks/main.yml`,
`ansible/roles/agentic_tools/README.md`

- [ ] Replace `opencode-ai` with `@opencode/cli` pinned at the current v2
  release, with its `# renovate: datasource=npm` annotation, and trust its
  postinstall in the Bun global install.
- [ ] A role run in a fresh container leaves `opencode --version` printing the
  pinned 2.x version, and a rerun changes nothing.

### Task 3: Run the web UI on v2 with a password

**Files:** Modify: `.devcontainer/scripts/opencode-web-start.sh`,
`scripts/tests/test_opencode_web_start.py`,
`docs/knowledge/data/codebase/devcontainer/scripts.md`

- [ ] Tests first: the pane runs `opencode serve --port 4096`; with a password
  it binds `0.0.0.0`; without one it binds `127.0.0.1`, creates the password
  file once with mode `0600`, reuses it on a rerun, never puts the password in
  the pane's command line or the script's output, and prints the file's path
  with the link; the real-tmux test sees the generated password in the server's
  environment.
- [ ] Implement until the tests pass.

### Task 4: Stop sharing the OpenCode login

**Files:** Delete: `.devcontainer/scripts/link-opencode-auth.sh`,
`scripts/tests/test_link_opencode_auth.py`; Modify:
`.devcontainer/scripts/postCreateCommand.sh`,
`.devcontainer/scripts/postStartCommand.sh`, `.devcontainer/devcontainer.json`,
`docs/knowledge/data/codebase/devcontainer/scripts.md`

- [ ] Remove the script, its tests, both calls, the
  `/root/.agents-auth/opencode` directory creation, and the auth-sharing wording
  of the `agentdev-opencode` mount comment.

### Task 5: Drive the E2E harness through v2

**Files:** Modify: `scripts/e2e/20261007-agent-owned-ship-implement/run.sh`,
`scripts/e2e/20261007-agent-owned-ship-implement/fixtures/opencode.json`

- [ ] Start each OpenCode scenario with `opencode api session.command` running
  `agentdev:<name>` with the scenario's arguments, read dispatches from the
  `subagent` tool, and keep the fixture's permissions valid for v2.
- [ ] `run.sh --harness opencode` passes every OpenCode check against the
  default test models.

### Task 6: Update the design documents

**Files:** Modify:
`docs/knowledge/data/architecture/opencode-catalog-bridge.md`,
`docs/knowledge/data/architecture/agent-auth-persistence.md`,
`docs/knowledge/data/features/opencode-catalog-host.md`,
`docs/knowledge/data/features/opencode-web-coder-autostart.md`

- [ ] Record the dual-export decision, the v2 host behavior from `## Context`,
  the v2 tool mapping, and the rejected alternatives in the bridge architecture;
  drop "v2 embedded skills" from its rejected list.
- [ ] Record per-worktree OpenCode logins in the auth architecture and both
  features, and the generated password in the web feature.

### Task 7: Verify the web UI on a Coder workspace

- [ ] On a Coder workspace built from this branch, with and without the
  `OPENCODE_SERVER_PASSWORD` secret: the printed link opens a session in the
  workspace folder after the browser's password prompt, the dashboard's
  `OpenCode` app is healthy, and a provider login survives a rebuild.

## Spec changes

- [OpenCode catalog bridge](../spec/opencode-catalog-bridge.md):

``` markdown
## ADDED Requirements

### Requirement: one bridge loads in OpenCode v1 and v2

The bridge plugin's default export SHALL carry `id`, a v1 `server` function, and
a v2 `setup` function, so the same `plugin` config entry loads it in either
major version.

#### Scenario: OpenCode v1 starts with the bridge registered

- **WHEN** OpenCode v1 starts with the bridge in its `plugin` config
- **THEN** it serves the catalog through the v1 hooks.

#### Scenario: OpenCode v2 starts with the bridge registered

- **WHEN** OpenCode v2 starts with the bridge in its `plugin` config
- **THEN** it serves the catalog through `setup`.

## MODIFIED Requirements

### Requirement: OpenCode lists every catalog skill

On OpenCode v1 the bridge plugin SHALL add the catalog's `skills/` directory to
OpenCode's skill search paths. On OpenCode v2 it SHALL register every catalog
skill with OpenCode's skill registry. Either way, OpenCode's skill tool lists
every catalog skill under the name in its frontmatter.

#### Scenario: OpenCode starts with the bridge registered

- **WHEN** OpenCode starts with the bridge plugin in its `plugin` config
- **THEN** OpenCode's skill list shows every skill under the catalog's
  `skills/` directory.

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

The bridge plugin SHALL rewrite a `skill` tool call whose `name` starts with
`agentdev:` to the name without that prefix, and SHALL leave every other tool
call unchanged, on OpenCode v1 and v2.

#### Scenario: a skill hands off to a sibling by its namespaced name

- **WHEN** the model calls the skill tool with `name: "agentdev:iwe-plan"`
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
not map to SHALL be `deny`: on v1 the mapped set plus `lsp` and `question`; on
v2 `shell`, `read`, `edit`, `write`, `patch`, `grep`, `glob`, `websearch`,
`webfetch`, `subagent`, `skill`, and `question`. A mapped tool SHALL keep the
user's configured permission rather than being set to `allow`.

#### Scenario: a subagent declares a restricted tool list on v1

- **WHEN** OpenCode v1 dispatches the `tdd-red` subagent, whose `tools:` list
  is Bash, Read, Edit, Write, Grep, Glob
- **THEN** its `webfetch`, `websearch`, and `task` permissions are `deny`, and
  `bash` follows the user's configured approval setting.

#### Scenario: a subagent declares a restricted tool list on v2

- **WHEN** OpenCode v2 dispatches the `tdd-red` subagent
- **THEN** it is not offered `webfetch`, `websearch`, `subagent`, `skill`, or
  `question`, and `shell` follows the user's configured approval setting.

### Requirement: user configuration takes precedence

The bridge plugin SHALL NOT overwrite a command, agent, or skill that the
user's OpenCode configuration already defines under the same key, nor, on v1, a
skill permission the user set.

#### Scenario: the user defines a command with the same name

- **WHEN** the user's config defines a command `agentdev:pr-open`
- **THEN** OpenCode runs the user's command, not the bridge's.
```

- [OpenCode web](../spec/opencode-web.md):

``` markdown
## MODIFIED Requirements

### Requirement: the Coder agent start runs the OpenCode web UI

`coder-agent-start.sh` SHALL run `opencode-web-start.sh` on every agent start,
before Remote Control starts. The script SHALL start `opencode serve` in exactly
one detached tmux session named `opencode` on the dedicated tmux server
`tmux -L opencode`, in the workspace folder, without checking for a provider
login. Repeated runs SHALL reuse a live session. It SHALL skip startup when
`opencode` or `tmux` is unavailable. A failure SHALL NOT stop Remote Control
from starting. On a start or a reuse it SHALL print
`<base>/<base64url(workspace folder)>/session`, base64url without `=` padding,
where `<base>` is `VSCODE_PROXY_URI` with `{{port}}` replaced by `4096` and any
trailing `/` removed, or `http://127.0.0.1:4096` when `VSCODE_PROXY_URI` is
unset or empty.

#### Scenario: a workspace starts

- **WHEN** the Coder agent starts and no `opencode` session is live
- **THEN** `opencode serve` runs in the `opencode` session on `tmux -L opencode`.

#### Scenario: the agent start runs again

- **WHEN** the `opencode` session is already live
- **THEN** no second session or server starts.

#### Scenario: the start prints a link into the workspace folder

- **WHEN** the script starts or reuses the `opencode` session
- **THEN** its output carries the link built on Coder's port URL for 4096, which
  opens a session in the workspace folder through Coder.

#### Scenario: the start runs outside Coder

- **WHEN** `VSCODE_PROXY_URI` is unset
- **THEN** the printed link starts with `http://127.0.0.1:4096`.

#### Scenario: the OpenCode start fails

- **WHEN** `opencode-web-start.sh` exits non-zero
- **THEN** the agent start warns and Remote Control still starts.

### Requirement: the server is exposed only behind a password

The server SHALL listen on port 4096 and SHALL always require a password. When
`OPENCODE_SERVER_PASSWORD` is non-empty in the agent's environment, the server
SHALL use it and bind `0.0.0.0`. Otherwise it SHALL bind `127.0.0.1` and use
the password in `~/.local/share/opencode/agentdev-server-password`, which the
script SHALL create with a random value and mode `0600` when it is missing. The
password SHALL NOT appear in the script's output or the server's command line;
the output SHALL name the password file when that file is in use.

#### Scenario: no password is set

- **WHEN** `OPENCODE_SERVER_PASSWORD` is unset or empty
- **THEN** the server listens on `127.0.0.1:4096` only, rejects a request
  without the password from the password file, and the output names that file.

#### Scenario: the workspace starts again without a password

- **WHEN** the password file already exists and `OPENCODE_SERVER_PASSWORD` is
  unset
- **THEN** the server uses the existing password.

#### Scenario: a password is set

- **WHEN** `OPENCODE_SERVER_PASSWORD` is non-empty
- **THEN** the server listens on `0.0.0.0:4096` and rejects a request without
  that password.

### Requirement: OpenCode logins and chats survive a rebuild

`~/.local/share/opencode`, which holds OpenCode's provider logins, sessions,
and the generated server password, SHALL live on the per-instance
`agentdev-opencode` volume.

#### Scenario: a provider is connected and the container is rebuilt

- **WHEN** a provider is connected from the web UI's Settings and the Dev
  Container is rebuilt
- **THEN** the provider is still connected and earlier sessions are listed.

#### Scenario: a second worktree starts

- **WHEN** another worktree's Dev Container starts on the same host
- **THEN** it sees none of the first worktree's provider logins or sessions.
```

- [Coder IDE baseline template](../spec/coder-ide-baseline.md): the `OpenCode`
  app requirement SHALL describe the repository's agent-start script as starting
  the OpenCode server (`opencode serve`) rather than `opencode web`; its
  behavior is unchanged.

## Verification

- `bun test ./.agents/plugins/agentdev/tests/opencode`
- `uv run pytest scripts/tests/test_opencode_web_start.py scripts/tests/test_coder_agent_start.py`
- Both majors load the checked-out bridge, from a sandboxed `HOME` under
  `./.tmp`: OpenCode v1.19 (`bunx opencode-ai@1.19.3 debug skill`,
  `debug agent tdd-red`) and the image's v2 (`opencode api command.list` and
  `opencode api skill.list` against `opencode serve`) each list every catalog
  skill, every `agentdev:*` command, and the catalog subagents.
- In the v2 TUI, `/agentdev:pr-gen-description for the current branch` shows
  only that text with a skill chip.
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh --harness opencode`
  passes.
- Task 7 on a Coder workspace.
- `iwe normalize` and `iwe schema validate` pass after the document edits.

## Out of scope

- Cross-worktree sharing of OpenCode logins.
- Denying v2's `execute` tool to catalog subagents.
- Changing the Coder template's `OpenCode` app or healthcheck, unless Task 7
  shows v2 breaks it.
- Native skill discovery of the catalog through v2's `.agents/skills` roots.
- Self-improve on OpenCode.

## Key references

Verified anchor points (line numbers as of 2026-10-18):

- `.agents/plugins/agentdev/.opencode-plugin/index.ts:8` — `TOOL_PERMISSIONS`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:23` —
  `SUBAGENT_TOOL_PERMISSIONS`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:56` — `readCatalog`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:102` — `applyCatalog`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:123` — `bridge` (v1 hooks,
  `tool.execute.before` at 129)
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:138` — default export
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts:141` — default-export
  test
- `ansible/roles/agentic_tools/defaults/main.yml:8-9,20-21` — `opencode-ai` pin
  and package entry
- `ansible/roles/agentic_tools/tasks/main.yml:24-37` — Bun global install loop
- `ansible/roles/agentic_tools/README.md:7,88` — `opencode-ai` mentions
- `.devcontainer/scripts/opencode-web-start.sh:23-35` — bind choice and pane
  command
- `scripts/tests/test_opencode_web_start.py:12-13` — expected pane commands
- `.devcontainer/scripts/link-opencode-auth.sh` — script to delete
- `.devcontainer/scripts/postCreateCommand.sh:72-73,80` — auth directory and
  link call
- `.devcontainer/scripts/postStartCommand.sh:28` — link call
- `.devcontainer/devcontainer.json:102-107` — `agentdev-opencode` mount and
  comment
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:384-400` —
  `opencode_run`, `opencode_calls`, shipper dispatch readers
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:418,428,439,444,452` —
  `--command` call sites
- `docs/knowledge/data/codebase/devcontainer/scripts.md:40,46` —
  `link-opencode-auth.sh` and `opencode-web-start.sh` rows
