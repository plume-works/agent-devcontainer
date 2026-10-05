---
type: plan
created: 2026-10-01
description: Serve the agentdev catalog to OpenCode through a dependency-free bridge plugin shipped inside the catalog, and provision OpenCode with the same image-build, postCreate, and postAttach lifecycle as Claude Code and Codex.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-01T12:00:00Z
sources:
- resource: .agents/plugins/agentdev
- resource: ansible/roles/agentic_tools
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postAttachCommand.sh
- resource: docs/knowledge/data/spec/catalog-lifecycle.md
- resource: https://github.com/anomalyco/opencode/tree/0112a92/packages/plugin/src
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/opencode/src/skill/index.ts
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/opencode/src/command/index.ts
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/tui/src/component/prompt/autocomplete.tsx
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/core/src/v1/config/agent.ts
---

# Load the agentdev catalog into OpenCode through a bridge plugin

## Context

The agentdev catalog serves Claude Code and Codex from one tree,
`.agents/plugins/agentdev/`, and the image installs it into both. OpenCode (the
`opencode-ai` npm package, 1.18.34, plugin API v1) has neither a Claude plugin
loader nor a Codex manifest format. This plan adds it as a third host for the
same tree, without copies and without depending on Claude Code.

Facts this design rests on, from OpenCode 1.18.34 source:

- **Skills.** OpenCode discovers skills from `skills.paths` in its config. Each
  skill's name comes from its frontmatter, so ours load bare (`git-commit`). The
  skill tool and skill-derived commands append the skill's base directory and
  state that relative paths resolve against it.
- **Commands.** Skill-derived commands are excluded from the `/` autocomplete
  (`autocomplete.tsx:451`). Ordinary commands are listed, matched with fuzzysort
  over name and description, and capped at 10 results.
- **Plugin hooks.** A v1 plugin's `config` hook receives the resolved config and
  may add `skills.paths`, `command`, `agent`, and `permission` entries.
  `tool.execute.before` may rewrite a tool call's arguments.
- **Agents.** The per-agent `tools` map is deprecated in favor of `permission`.
- **Plugin specs.** A plugin may be referenced by an absolute path.

It depends on
[Reference bundled skill code by skill-relative agent-code paths](20261001-skill-relative-agent-code.md):
once skill bodies reference `agent-code/<script>` relative to the skill
directory, OpenCode needs no text substitution at all.

## Approach

A bridge plugin, `.agents/plugins/agentdev/.opencode-plugin/`, ships inside the
catalog next to `.claude-plugin/` and `.codex-plugin/`. It resolves the plugin
root from its own location and reads that tree at startup.

- **Skills.** It adds `<root>/skills` to `skills.paths`, so the skill tool lists
  every skill under its bare name.
- **Slash commands.** For each skill it adds a command `agentdev:<name>` whose
  template is the skill body plus the same base-directory footer OpenCode's own
  skill commands carry. That gives users the `/agentdev:<name>` spelling they
  type in Claude Code and Codex, and it appears in autocomplete.
- **Namespaced skill-tool calls.** Catalog text names siblings as
  `/agentdev:<name>`, so the plugin's `tool.execute.before` hook strips an
  `agentdev:` prefix from the `skill` tool's `name` argument.
- **`disable-model-invocation`.** A skill carrying it gets a
  `permission.skill.<name> = "deny"` entry. The model can no longer load it
  through the skill tool, while `/agentdev:<name>` still works.
- **Agents.** Each `agents/<stem>.agent.md` becomes a subagent `<stem>` with its
  body as the prompt.
  - Tools absent from its Claude `tools:` list are set to `deny`.
  - Listed tools are left unset, so the user's own approval settings still
    apply. A Claude `tools:` list restricts which tools are available; it does
    not pre-approve them.
- **User config wins.** Entries the user already defined under the same keys are
  left alone.

The plugin has no runtime dependencies. It uses type-only imports and Bun
built-ins, because the staged catalog in the image is root-owned and read-only,
so no `node_modules` can be installed into it.

Provisioning mirrors the other two hosts:

- the role installs the CLI as a pinned Bun global;
- `reinstall-agentdev-opencode.sh` registers the bridge's absolute path in the
  user's OpenCode config;
- the image build, postCreate, and postAttach call it the way they call the
  Claude and Codex installers.

Rejected alternatives:

- **oh-my-opencode's Claude compatibility layer.**
  - It is licensed under the Sustainable Use License, not an open-source
    licence, and sends telemetry by default.
  - It discovers plugins through Claude Code's `installed_plugins.json`.
- **OCX registry distribution.** It copies files into `.opencode/` without
  conversion, so it provides neither namespaced commands nor agent mapping, and
  its OpenCode 2 line is a pre-release (`3.0.0-alpha.1`).
- **OpenCode v2 embedded skills registered under `agentdev:<name>`.** These are
  not in the released 1.18 plugin API, and v2's tool and session hooks exist
  only in `packages/plugin/src/v2/effect/PLAN.md`.
- **Bare `<name>` commands.** They would win OpenCode's prefix-match bonus when
  typing `/pr`. The cost is names that differ from Claude and Codex, plus
  collisions with other plugins' bare skills. This remains the fallback if Task
  1 measures `/pr` ranking as unusable.
- **Rewriting catalog text to "the `<name>` skill".** That means rewriting more
  than 100 `/agentdev:<name>` references and less precise invocation in Claude
  Code, for a gap the prefix rewrite closes.

## Implementation Steps

### Task 1: Settle the OpenCode host behavior the bridge relies on

**Files:** Create: `docs/knowledge/data/architecture/opencode-catalog-bridge.md`

- [x] With a throwaway prototype under `./.tmp/` and `bunx opencode-ai@1.18.34`,
  establish each point below. A result that contradicts this plan's Approach
  goes back to `/agentdev:iwe-plan` before Task 2 starts.
  1. A `skills.paths` entry added in the `config` hook reaches
     `opencode debug skill`.
  2. A command key containing `:` loads, autocompletes, and runs.
  3. `/pr` and `/pr-` list the `agentdev:pr-*` commands within the 10-result
     cap.
  4. `tool.execute.before` can rewrite the `skill` tool's `name`.
  5. `permission.skill.<name> = "deny"` hides a skill from the skill tool but
     not from its command.
  6. `Bun.YAML.parse` is available to plugins.
  7. A `plugin` config entry holding the bridge directory's absolute path loads
     it.
  - **Evidence:** commit "Settle the OpenCode host behavior the bridge relies
    on": all seven hold against `opencode-ai@1.18.34`, recorded under "Host
    behavior the design rests on" in `architecture/opencode-catalog-bridge`;
    `/pr` shows 8 of the 10 `agentdev:pr-*` commands and `/pr-` all 10, so the
    Approach stands
- [x] Record the decision, the facts it rests on, and the rejected alternatives
  from `## Approach` in `data/architecture/opencode-catalog-bridge.md`, linked
  from `data/architecture.md`
  - **Evidence:** commit "Settle the OpenCode host behavior the bridge relies
    on" adds the document and its inclusion link

### Task 2: Build the bridge plugin

**Files:** Create: `.agents/plugins/agentdev/.opencode-plugin/package.json`,
`.agents/plugins/agentdev/.opencode-plugin/index.ts`,
`.agents/plugins/agentdev/tests/opencode/bridge.test.ts`

- [x] `bun test` cases, written first, run against the real plugin root:
  - every skill directory yields an `agentdev:<name>` command whose template
    ends with the base-directory footer;
  - `<root>/skills` is added to `skills.paths`;
  - every `disable-model-invocation` skill yields a `permission.skill` deny;
  - every agent file yields a subagent with deny entries for exactly the tools
    its `tools:` list omits;
  - every Claude tool name used by a catalog agent has an OpenCode permission
    mapping;
  - user-defined keys are preserved;
  - the `skill` tool's `agentdev:` prefix is stripped, and other tools' calls
    are untouched.
  - **Evidence:** commit "Add the OpenCode bridge plugin for the agentdev
    catalog": `tests/opencode/bridge.test.ts` covers each case above and failed
    on the missing module before the plugin existed
- [x] Implement the plugin with type-only imports and no `dependencies` in
  `package.json`. Tool mapping: Bash→`bash`, Read→`read`, Edit and Write→`edit`,
  Grep→`grep`, Glob→`glob`, WebSearch→`websearch`, WebFetch→`webfetch`,
  Agent→`task`, TodoWrite→`todowrite`, Skill→`skill`.
  - **Evidence:** commit "Add the OpenCode bridge plugin for the agentdev
    catalog": `.opencode-plugin/package.json` has no `dependencies` and
    `index.ts` imports only types plus `node:fs` and `node:path`; registered in
    `opencode-ai@1.18.34`, `opencode debug skill` lists all 38 catalog skills
    and `opencode debug agent tdd-red` shows the deny entries
- [x] `bun test ./.agents/plugins/agentdev/tests/opencode` passes
  - **Evidence:** commit "Add the OpenCode bridge plugin for the agentdev
    catalog": 12 pass, 0 fail

### Task 3: Run the bridge tests in CI

**Files:** Modify: `.github/workflows/validate-agent-files.yml`

- [x] Add a pinned `oven-sh/setup-bun` step and a
  `bun test ./.agents/plugins/agentdev/tests/opencode` step to the
  `validate-agent-files` job
  - **Evidence:** commit "Run the OpenCode bridge tests in CI": steps pinned to
    `oven-sh/setup-bun@v2.2.0`; the actionlint and zizmor pre-commit hooks pass

### Task 4: Install the OpenCode CLI in the image

**Files:** Modify: `ansible/roles/agentic_tools/defaults/main.yml`,
`ansible/roles/agentic_tools/README.md`

- [x] Add `agentic_tools_opencode_version: "1.18.34"` under a
  `# renovate: datasource=npm depName=opencode-ai` comment, and an `opencode-ai`
  entry in `agentic_tools_bun_packages`
  - **Evidence:** commit "Install the OpenCode CLI in the image"; ansible-lint
    passes, and the role's `bun add --global --exact opencode-ai@1.18.34` form
    installs a working `opencode` 1.18.34 that `bun pm ls --global` reports as
    `opencode-ai@1.18.34`
- [x] Document the new variable in the role README
  - **Evidence:** commit "Install the OpenCode CLI in the image": an "Agent
    CLIs" variable table and the Bun-globals list name `opencode-ai`

### Task 5: Register the bridge in a user's OpenCode config

**Files:** Create: `.devcontainer/scripts/reinstall-agentdev-opencode.sh`

- [x] The script takes an optional catalog root, defaulting to this checkout,
  like `reinstall-agentdev-codex.sh`. When
  `<root>/.agents/plugins/agentdev/.opencode-plugin` is absent, it reports that
  and exits 0.
  - **Evidence:** commit "Register the OpenCode bridge in the user's config":
    run with `/nonexistent` prints "ships no OpenCode bridge plugin" and exits 0
- [x] Otherwise it writes the bridge's absolute path into the `plugin` array of
  `${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}/opencode.json`.
  It creates the file when missing, replaces any earlier entry ending in
  `/.agents/plugins/agentdev/.opencode-plugin`, and preserves every other key.
  - **Evidence:** commit "Register the OpenCode bridge in the user's config":
    from a config holding `model`, `other-plugin`, and an old-root
    `[spec, options]` bridge entry, the run keeps `model` and `other-plugin` and
    replaces the old entry; with no config it creates `{"plugin": [<bridge>]}`
- [x] Run it twice against `HOME=./.tmp/opencode-home`, once with the staged
  root and once with no argument. The config then lists exactly one bridge
  entry, pointing at the last root. `shellcheck` passes.
  - **Evidence:** commit "Register the OpenCode bridge in the user's config":
    after the staged-root run and the no-argument run, `plugin` holds one bridge
    entry, the checkout's; `shellcheck` and the pre-commit shellcheck hook pass

### Task 6: Install the bridge through the catalog lifecycle

**Files:** Modify: `.devcontainer/scripts/postCreateCommand.sh`,
`.devcontainer/scripts/postAttachCommand.sh`,
`ansible/roles/agentic_tools/tasks/install_catalog.yml`

- [x] postCreate calls `reinstall-agentdev-opencode.sh "$AGENTDEV_CATALOG_DIR"`
  inside the existing staged-catalog branch
  - **Evidence:** commit "Install the OpenCode bridge through the catalog
    lifecycle"; `shellcheck` passes
- [x] postAttach calls `reinstall-agentdev-opencode.sh` with no argument,
  alongside the Codex and Claude reinstalls
  - **Evidence:** commit "Install the OpenCode bridge through the catalog
    lifecycle"; `shellcheck` passes
- [x] The build-time install writes the staged bridge path into
  `{{ user_home }}/.config/opencode/opencode.json`, merging with any existing
  content
  - **Evidence:** commit "Install the OpenCode bridge through the catalog
    lifecycle"; ansible-lint and the `setup-dev.yml` syntax check pass, and the
    block run against localhost keeps existing keys and plugin entries, is
    unchanged on a second run, creates the file when absent, and skips when the
    staged catalog has no bridge

### Task 7: Document OpenCode as a catalog host

**Files:** Modify: `.agents/AGENTS.md`, `.agents/plugins/agentdev/README.md`,
and whichever `docs/knowledge/data/codebase/` documents `stale-map-docs.py`
reports

- [x] `.agents/AGENTS.md`: OpenCode consumes the same tree through
  `.opencode-plugin/`. The bridge takes no runtime dependencies.
  - **Evidence:** commit "Document OpenCode as a catalog host": a bullet under
    "Catalog locations and portability"
- [x] The plugin README names OpenCode and how a project enables the bridge
  - **Evidence:** commit "Document OpenCode as a catalog host": title, an
    "Installing in OpenCode" section with the `plugin` config entry, OpenCode
    usage, and the bun suite; `validate_agent_files` reports 0 errors
- [x] Refresh the stale codebase-map documents through `/agentdev:iwe-map`
  - **Evidence:** commit "map: refresh 13 docs and map the OpenCode bridge": run
    after Task 8 so the release pins are covered; adds
    `codebase/agents/plugins/agentdev/opencode-plugin`, and `stale-map-docs.py`
    ends `RESULT=SUCCESS` with 28 of 28 fresh

### Task 8: Release the catalog

**Files:** Modify: `.agents/plugins/agentdev/.claude-plugin/plugin.json`,
`.agents/plugins/agentdev/.codex-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `docker/desktop/agent-desktop.Dockerfile`,
`.codex/setup-codex-cloud.sh`, `README.md`

- [x] agentdev minor version bump in both manifests and the marketplace entry
  - **Evidence:** commit "Release agentdev 4.2.0": 4.1.0 → 4.2.0 in all three
- [x] Move the image's `AGENTDEV_PLUGIN_VERSION` pin, the Codex cloud setup pin,
  and the root README's version with them
  - **Evidence:** commit "Move the remaining agentdev 4.2.0 pins": `git grep`
    finds no agentdev `4.1.0` outside the knowledge graph's history
- [x] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes
  - **Evidence:** commit "Release agentdev 4.2.0": 56/56 skills valid, 0 errors,
    0 warnings

### Task 9: Confirm the catalog in a rebuilt devcontainer

- [x] In a container built from this branch, with no manual setup:
  - `opencode debug skill` lists the agentdev skills;
  - `/pr` in the TUI offers `/agentdev:pr-*` commands;
  - `/agentdev:pr-gen-description` runs its script from the skill's
    `agent-code/`;
  - asking for a TDD Red subagent dispatches `tdd-red` without web tools.
  - **Evidence:** the pull request's `agent-desktop` image, run with no
    lifecycle scripts: the build-time `opencode.json` lists the staged bridge;
    `opencode debug skill` lists all 38 catalog skills from `/opt/agentdev`;
    `/pr` shows 8 `agentdev:pr-*` commands and `/pr-` all 10; with
    `opencode/big-pickle`, the command ran `review-git-changes.sh` from the
    staged `agent-code/` to `RESULT=SUCCESS`, and a TDD Red request dispatched a
    `tdd-red` session that called only `bash` and `write`

### Task 10: CI passes on the branch

- [x] The `validate-agent-files` workflow passes on the pull request, including
  the bun step
  - **Evidence:** pull request #255: `validate-agent-files` passes, the bun step
    reporting 12 pass, 0 fail

## Spec changes

[Catalog lifecycle](../spec/catalog-lifecycle.md) — OpenCode joins both install
requirements; the credentials requirement is unchanged:

``` markdown
## MODIFIED Requirements

## Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the image build, at Claude user scope, via
Codex's own registration, and by registering the catalog's OpenCode bridge
plugin in the user's OpenCode config, so a consumer that runs the image without
devcontainer lifecycle hooks resolves `agentdev:*` skills. `postCreateCommand.sh`
SHALL also install it, because a mounted `~/.claude` / `~/.codex` volume shadows
what the image build wrote. Because the build-time Claude install seeds a real
`/root/.claude.json` into the image, `postCreateCommand.sh` SHALL establish the
volume→`/root/.claude.json` symlink before `codebase-memory-mcp-install.sh` runs
— discarding the image's real file, seeding `/root/.claude/claude.json` with
`{}` only when the volume has none — so the mounted `agentdev-claude` volume
remains the source of truth for `claude.json`, cbm-install folds its MCP entry
back into the volume, and no image content is folded into it.

### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `ghcr.io/plume-works/agent-desktop` and no
  lifecycle hook runs
- **THEN** the catalog installed during the image build is present, an
  `agentdev:*` skill resolves in Claude Code and Codex, and OpenCode loads the
  staged bridge plugin and lists the catalog's skills.

### Scenario: a devcontainer starts for the first time on a fresh volume

- **WHEN** `postCreateCommand` runs, `$AGENTDEV_CATALOG_DIR` exists, and the
  image ships a real `/root/.claude.json`
- **THEN** `postCreateCommand` discards that image file and symlinks
  `/root/.claude.json` to a freshly-seeded `/root/.claude/claude.json` before
  `codebase-memory-mcp-install.sh` runs, so cbm-install folds only its MCP entry
  into the volume's clean `claude.json` with no image content, and
  `reinstall-agentdev-codex.sh`, `reinstall-agentdev-claude.sh ... user`, and
  `reinstall-agentdev-opencode.sh` install the staged catalog into the fresh
  `agentdev-claude` / `agentdev-codex` volumes and the OpenCode user config.

### Scenario: a devcontainer starts with a catalog already installed on its volume

- **WHEN** the `agentdev-claude` / `agentdev-codex` volumes already contain a
  prior install and `claude.json` (they persist per devcontainer instance), and
  the recreated container carries the image's `/root/.claude.json`
- **THEN** `postCreateCommand` discards the image's `/root/.claude.json` and
  symlinks `/root/.claude.json` to the volume's existing `claude.json` before
  cbm-install runs, so that content is preserved (cbm-install folds its MCP
  entry back in; Claude may append bootstrap fields, so the guarantee is content
  preservation, not byte-identity), the volume mount shadows the image-build
  catalog install, and `postCreateCommand` re-applies that install every time
  the container is created, so it is never silently stale.

## Requirement: this repository's own checkout overrides the staged catalog on attach

`postAttachCommand.sh` SHALL re-run `reinstall-agentdev-codex.sh`,
`reinstall-agentdev-claude.sh`, and `reinstall-agentdev-opencode.sh` with no
catalog-dir argument on every editor attachment (including after a window
reload), registering this workspace's `.agents/plugins/agentdev/` over the
image's staged copy.

### Scenario: a skill or agent is edited in this checkout and the editor window is reloaded

- **WHEN** the developer reloads the VS Code window (or reattaches)
- **THEN** `postAttachCommand` re-registers the marketplace from
  `.agents/plugins/agentdev/` in the workspace, and points OpenCode's bridge
  entry at the workspace copy, so the edited skill is picked up without a
  container rebuild.

### Scenario: a consuming project (not this repository) attaches

- **WHEN** `postAttachCommand`'s reinstall scripts run in a consumer project
  that has no `.agents/plugins/agentdev/` marketplace manifest or bridge plugin
- **THEN** the scripts find nothing to register and exit quietly, leaving the
  image-staged catalog in place.
```

[OpenCode catalog bridge](../spec/opencode-catalog-bridge.md) (new) — the
bridge's contract, including the permission mapping that limits subagents:

``` markdown
## ADDED Requirements

## Requirement: OpenCode lists every catalog skill

The bridge plugin SHALL add the catalog's `skills/` directory to OpenCode's
skill search paths, so OpenCode's skill tool lists every catalog skill under the
name in its frontmatter.

### Scenario: OpenCode starts with the bridge registered

- **WHEN** OpenCode starts with the bridge plugin in its `plugin` config
- **THEN** `opencode debug skill` lists every skill under the catalog's
  `skills/` directory.

## Requirement: every skill is a namespaced slash command

The bridge plugin SHALL register a command `agentdev:<name>` for each catalog
skill. Its description SHALL be the skill's frontmatter description, and its
template SHALL be the skill body followed by the skill's base directory and the
statement that relative paths resolve against it.

### Scenario: the user types a namespaced command

- **WHEN** the user types `/agentdev:pr-gen-description`
- **THEN** OpenCode sends the `pr-gen-description` skill body with its base
  directory, and a relative `agent-code/` step resolves inside that skill.

### Scenario: the user types a command prefix

- **WHEN** the user types `/pr` in the OpenCode TUI
- **THEN** the autocomplete offers `agentdev:pr-*` commands.

## Requirement: the skill tool accepts the catalog's namespaced names

The bridge plugin SHALL rewrite a `skill` tool call whose `name` starts with
`agentdev:` to the name without that prefix, and SHALL leave every other tool
call unchanged.

### Scenario: a skill hands off to a sibling by its namespaced name

- **WHEN** the model calls the skill tool with `name: "agentdev:iwe-plan"`
- **THEN** OpenCode loads the `iwe-plan` skill.

## Requirement: explicit-only skills stay out of model invocation

For every catalog skill whose frontmatter sets `disable-model-invocation: true`,
the bridge plugin SHALL deny that skill to OpenCode's skill tool while keeping
its `agentdev:<name>` command.

### Scenario: the model tries to load an explicit-only skill

- **WHEN** the model calls the skill tool for a skill with
  `disable-model-invocation: true`
- **THEN** OpenCode refuses the call, and the user can still run the skill as
  `/agentdev:<name>`.

## Requirement: catalog agents are subagents limited to their declared tools

The bridge plugin SHALL register each `agents/<stem>.agent.md` as an OpenCode
subagent named `<stem>`, with the file's description and body as its
description and prompt. Every OpenCode tool permission that the file's `tools:`
list does not map to SHALL be `deny`. A mapped tool SHALL keep the user's
configured permission rather than being set to `allow`.

### Scenario: a subagent declares a restricted tool list

- **WHEN** OpenCode dispatches the `tdd-red` subagent, whose `tools:` list is
  Bash, Read, Edit, Write, Grep, Glob
- **THEN** its `webfetch`, `websearch`, and `task` permissions are `deny`, and
  `bash` follows the user's configured approval setting.

## Requirement: user configuration takes precedence

The bridge plugin SHALL NOT overwrite a command, agent, or skill permission
that the user's OpenCode configuration already defines under the same key.

### Scenario: the user defines a command with the same name

- **WHEN** the user's config defines a command `agentdev:pr-open`
- **THEN** OpenCode runs the user's command, not the bridge's.
```

## Depends on

- [Reference bundled skill code by skill-relative agent-code paths](20261001-skill-relative-agent-code.md)

## Verification

- `bun test ./.agents/plugins/agentdev/tests/opencode`
- `shellcheck .devcontainer/scripts/reinstall-agentdev-opencode.sh`, plus the
  two-run check in Task 5
- `bunx opencode-ai@1.18.34 debug skill`, with the bridge registered against
  this checkout, lists the agentdev skills, and
  `bunx opencode-ai@1.18.34 debug agent tdd-red` shows the deny entries
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- `iwe normalize` and `iwe schema validate`
- Tasks 9–10: the rebuilt-devcontainer check and the CI run

## Out of scope

- **self-improve on OpenCode.** Its reviewer builds a Claude-only command line
  (`reviewer.py:62-89`), and its seven hook events need OpenCode equivalents,
  including one for the typed-command authorization that `UserPromptExpansion`
  provides. Both are their own design question.
- **Hook mapping for agentdev.** agentdev ships no hooks, so the bridge maps
  none.
- **Sharing OpenCode credentials** across worktrees through the
  `agentdev-agents-auth` volume, and persisting OpenCode state in a volume.
- **OpenCode v2 plugin API** registration, including skills registered under
  namespaced names.
- **Publishing the bridge to npm** or an OpenCode marketplace.
- **Codex support for the catalog's agents.**

## Key references

Verified anchor points (line numbers as of 2026-10-04):

- `ansible/roles/agentic_tools/defaults/main.yml:1-18` — pinned agent CLIs and
  `agentic_tools_bun_packages`
- `ansible/roles/agentic_tools/defaults/main.yml:71-89` — staged catalog root
  `/opt/agentdev`, staged trees (`.agents` copied whole), prune list
- `ansible/roles/agentic_tools/tasks/install_catalog.yml:27-81` — build-time
  Claude and Codex installs
- `ansible/roles/agentic_tools/tasks/main.yml:44-51` — staging and install gates
- `.devcontainer/scripts/reinstall-agentdev-codex.sh:12-28` — catalog-root
  argument and no-manifest quiet exit to mirror
- `.devcontainer/scripts/postCreateCommand.sh:85-96` — staged-catalog install
  branch
- `.devcontainer/scripts/postAttachCommand.sh:12-15` — workspace re-registration
- `.github/workflows/validate-agent-files.yml:62-90` — `validate-agent-files`
  job steps
- `.agents/plugins/agentdev/agents/tdd-red.agent.md:1-5` — agent frontmatter
  shape (`name`, `description`, `tools`)
- `.agents/plugins/self-improve/selfimprove/reviewer.py:62-89` — Claude-only
  reviewer argv
- `docs/knowledge/data/spec/catalog-lifecycle.md:17-83` — the two requirements
  this plan modifies
- OpenCode `packages/plugin/src/index.ts:225-280` (0112a92) — v1 `config`,
  `tool.execute.before`, `command.execute.before` hooks
- OpenCode `packages/opencode/src/skill/index.ts:211-220` — `skills.paths`
  discovery
- OpenCode `packages/opencode/src/command/index.ts:134-150` — skill-derived
  commands, user and config commands taking precedence
- OpenCode `packages/tui/src/component/prompt/autocomplete.tsx:447-528` —
  command list, skill exclusion, fuzzysort with `limit: 10`
- OpenCode `packages/core/src/v1/config/agent.ts:20-38` — agent `prompt`,
  deprecated `tools`, `mode`, `permission`
- OpenCode `packages/core/src/v1/config/permission.ts:17-33` — permission keys
- OpenCode `packages/opencode/src/plugin/shared.ts:171-173` — `isPathPluginSpec`
  accepts `file://`, relative, and absolute plugin paths
