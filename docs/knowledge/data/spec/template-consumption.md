---
type: spec
description: How a project adopts this repository as a template — the normative requirements, with the full setup and update procedure owned by the agentdev template-consume skill.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/65#discussion_r3794941822
- resource: .devcontainer/devcontainer.json
- resource: https://github.com/plume-works/vscode-expo-bridge
- resource: docker/base/agentdev-base.Dockerfile
- resource: .dockerignore
- resource: .agents/plugins/agentdev/bin/skill_common.py
- resource: .agents/plugins/agentdev/bin/python_lint_check.py
- resource: py_packages/validate_agent_files/tests
- resource: ansible/roles/validate_agent_files/tasks/main.yml
---

# Template consumption

The procedure for adopting this repository's development environment and
conventions in another project is owned by the `agentdev` catalog's
`/agentdev:template-consume` skill, at
`.agents/plugins/agentdev/skills/template-consume/`. Its
`references/consumption-guide.md` is the single step-by-step guide — Workflow A
(full repository copy), Workflow B (existing repository), the optional
custom-image bundle, and verification — and its `SKILL.md` defines setup mode,
update mode, the `template-consume` section of `.agent.metadata.json`, and the
progress document. Edit the guide, not this document, when a step, a
deleted-or-retained path, or a CI adaptation changes. The skill ships in the
plugin, so a consumer runs it from an installed catalog without this repository
checked out.

This document holds only the requirements the procedure must satisfy; the
path-by-path inventory is the guide's.

## Requirement: the finished project retains every runtime capability

The default setup SHALL retain every runtime capability the template's
devcontainer provides — the digest-pinned `agentdev-devcontainer` image with its
supervised nested Docker, worktree-safe mounts, Xpra/VirtualGL, persistent
agent-state volumes with one shared credentials volume, the image-staged
`agentdev` catalog, keyring and GitHub authentication, uv caching and pre-commit
setup, and the opt-in egress firewall. It SHALL NOT infer a language, create
application code, choose dependencies, or invent CI for the consuming project's
product.

## Requirement: an update migrates the consumer to the agentdev image family in one change

When a consumer's Dev Container pins `agent-desktop` and the upstream template
pins `agentdev-devcontainer`, update mode SHALL apply the new descriptor only
together with moving the Compose pin and every workflow `container.image`
reference to `agentdev-devcontainer`, removing the keepalive command and the
Docker-in-Docker Feature, and replacing copied agentdev lifecycle scripts with
the image's commands. It SHALL preserve the consumer's own lifecycle additions
as descriptor commands or derived-image hooks.

### Scenario: a consumer updates across the image change

- **WHEN** update mode applies the migration
- **THEN** one change moves the pin, descriptor, and workflow images together,
  and the rebuilt Dev Container reaches runtime readiness

### Scenario: a consumer declines the migration

- **WHEN** the user declines the migration
- **THEN** the descriptor and pin keep their previous values, and `consumed_ref`
  does not advance past the change

### Scenario: a custom image derives from agent-desktop

- **WHEN** the consumer's retained Dockerfile derives from `agent-desktop`
- **THEN** update mode asks whether it derives from `agentdev-base` or
  `agentdev-devcontainer` and changes the base to the chosen image

## Requirement: publisher-only source never survives adoption

A consumer SHALL delete `.agents/`, `.claude-plugin/`, and `py_packages/`, and
SHALL adapt every CI workflow, pre-commit hook, `pyproject.toml` entry, and path
filter that referenced them. Agent-file validation, when retained, SHALL run the
validator the digest-pinned image provides, never the deleted working-tree
package.

## Requirement: `.ruff.toml` and `pyproject.toml` never both configure ruff

Ruff resolves the first configuration file it finds and silently ignores the
rest. A consumer SHALL keep exactly one of the template's `.ruff.toml` and a
`[tool.ruff]` table.

## Requirement: a linter hook is never added without its matching config, or vice versa

A `.clang-format` with no C++ is inert; a clang-format hook with no
`.clang-format` fails. Hooks and their configuration SHALL be adopted as pairs.

## Requirement: formatter adoption never rewrites verbatim third-party captures

Directories holding byte-exact third-party captures SHALL be excluded in
`.prettierignore` and ruff's `extend-exclude` before the formatters first run.

## Requirement: the AI review gate's trust is explicit

The `claude-respond` and `ai-review-present` jobs in `ai-responder.yml` SHALL be
kept or dropped together. The responder SHALL NOT auto-review any bot-authored
pull request; `ai-review-present` SHALL waive its requirement, and the
trusted-bot approval job SHALL approve, only for the bot logins listed in
`TRUSTED_BOT_ACTORS`, matched exactly and only when `user.type` is `Bot`. The
gate checks that the pull request has a review, not that its head commit does —
a copy comparing the review's `commit_id` to the head SHA is a policy change.
The fork gate and write-access gate SHALL be preserved as written; the owner
gate SHALL be repointed at the consumer. The workflow SHALL NOT gain a comment,
issue, or `workflow_dispatch` trigger, so no comment starts it.

## Requirement: adoption is recorded for later updates

Setup SHALL write two records at the consumer root, both tracked in git.

The `template-consume` section of `.agent.metadata.json` SHALL record the full
commit SHA of the template consumed, the workflow used, the optional bundles
kept, and the template paths still tracked. It SHALL remain the only
machine-parsed record of the consumed ref, and SHALL be read root-only: the
consumer reads the repository-root file and does not walk, because a repository
has exactly one adopted ref. Update mode SHALL diff only those paths from that
SHA and SHALL NOT advance the SHA past what was actually applied.

`.agentdev-template-progress.md` SHALL own the task list for the chosen workflow
and the choices the user made. Setup SHALL write it before executing the guide's
steps, so an interrupted session leaves a resumable record. It MAY name the
adopted SHA as context, but SHALL NOT be read as the source of truth for it.

`tracked_paths` SHALL hold template paths only. Neither file SHALL appear in it,
nor SHALL `.github/pr-description-guidance.md`, `docs/knowledge/data/`,
`docs/knowledge/LICENSE.md`, any file of the `iwe-bootstrap` scaffold, or any
publisher-only path (`.agents/`, `.claude-plugin/`, `py_packages/`).

### Scenario: a consumer keeps the knowledge base

- **WHEN** setup records the paths of a consumer that kept the knowledge-base
  bundle
- **THEN** `tracked_paths` lists `.iwe/` and the `docs/knowledge/` support
  documents and tests, and names neither `docs/knowledge/data/` nor
  `docs/knowledge/LICENSE.md`

### Scenario: setup is interrupted and resumed

- **WHEN** a setup session ends with tasks in `.agentdev-template-progress.md`
  still unticked
- **THEN** the next session continues from those tasks and the recorded choices,
  rather than restarting the workflow and scope interview

### Scenario: a task is completed during consumption

- **WHEN** a consumption task is finished
- **THEN** its checkbox is ticked in the same edit that writes an indented
  `- **Evidence:**` child naming what closed it

### Scenario: a consumer adopted before the records were consolidated

- **WHEN** update mode finds a legacy `.agentdev-template.json` at the consumer
  root
- **THEN** its fields are moved into the `template-consume` section of
  `.agent.metadata.json` and the legacy file is deleted, without advancing
  `consumed_ref`

### Scenario: a choice constrains a later update

- **WHEN** update mode considers a changed template path the consumer's choice
  log records as customized
- **THEN** the recorded choice is applied rather than re-derived, and the path
  is merged manually rather than overwritten

## Requirement: adoption is summarized into a consumer's knowledge base

When the consumer kept the IWE knowledge base, setup and update SHALL write a
summary document into the consumer's graph at the end of the episode recording
the adopted SHA, the workflow, and the settled choices, and pointing at
`.agentdev-template-progress.md` as the live record. It SHALL NOT mirror the
task list. A consumer without a knowledge base SHALL skip this step, and its
absence SHALL NOT block consumption.

## Requirement: an Expo consumer is prepared for EAS cloud builds

The template devcontainer SHALL pass `EXPO_TOKEN` from the host environment into
the container through `containerEnv` for every consumer, and SHALL store it
nowhere in the repository or a volume.

When the consumer is an Expo app, setup SHALL record `"expo"` in
`optional_bundles` without adding any `tracked_paths`, SHALL NOT add a second
`EXPO_TOKEN` definition, and SHALL leave the consumer with: the Expo hosts in
the firewall allowlist; `.env.eas-simulator` ignored by git; every `eas.json`
build profile pinning `bun` to the devcontainer's bun version; and one root
`AGENTS.md` that keeps the template's content and holds the Expo template's
`AGENTS.md` body under an `## Expo` section, followed by a line telling agents
to run each `npx` command Expo's skills write with `bunx`.
`.claude/settings.json` SHALL keep `expo@claude-plugins-official` in
`enabledPlugins`. The guide SHALL require the app to be tracked in the consumer
repository, never under an ignored path, because EAS archives the project by
cloning the enclosing repository.

### Scenario: an Expo app adopts the template

- **WHEN** setup runs in a repository whose app was created by `create-expo-app`
  and the user confirms it is an Expo app
- **THEN** the marker's `optional_bundles` includes `"expo"`
- **AND** the Expo template's separate `AGENTS.md` no longer exists
- **AND** the progress document records the root `AGENTS.md` as customized

### Scenario: the image's bun changes

- **WHEN** update mode applies a change to `devcontainer-compose-pins.yml` for a
  consumer whose `optional_bundles` includes `"expo"`
- **THEN** each `eas.json` build profile's `bun` is compared with
  `bun --version` in the rebuilt devcontainer and updated when they differ

### Scenario: a non-Expo consumer

- **WHEN** the user says the consumer is not an Expo app
- **THEN** setup makes none of the Expo edits and `optional_bundles` omits
  `"expo"`
- **AND** the devcontainer still passes `EXPO_TOKEN`, empty when the host does
  not set it

### Scenario: a Coder workspace supplies the token

- **WHEN** `EXPO_TOKEN` is a Coder user secret and the Dev Container is rebuilt
  with the passthrough
- **THEN** a shell started by the Dev Container's sub-agent sees `EXPO_TOKEN`
  and `eas whoami` reports the account

## Requirement: an Expo consumer can build iOS on a Mac host through the bridge

When the consumer's `optional_bundles` includes `"expo"`, setup SHALL list
`plume-works.vscode-expo-bridge` in `customizations.vscode.extensions`, add
`8081` to `forwardPorts` with the `portsAttributes` entry
`"8081": { "label": "Metro", "onAutoForward": "silent" }`, and add to the
`## Expo` section of the root `AGENTS.md` a rule that an iOS Simulator build
uses `eas-host` when `eas-host status` succeeds and EAS cloud with the same
profile otherwise, and that device and store builds always use EAS cloud. The
rule SHALL name the order `status`, `build <profile>`, `install`, `launch`,
`screenshot`, and SHALL say to start Metro in the container on port 8081 before
`launch` of a development build. Update mode SHALL reconcile these edits against
the guide whenever `optional_bundles` includes `"expo"`, even when no tracked
path changed. Setup SHALL NOT add any host command bridge other than this
extension pack, SHALL NOT change the firewall allowlist for it, and SHALL NOT
pre-authorize the bridge: trust in a workspace is granted only on the Mac.

The protocol contract and security model are specified in
[`plume-works/vscode-expo-bridge`](https://github.com/plume-works/vscode-expo-bridge)
(`docs/protocol.md`), not in this repository.

### Scenario: an Expo consumer is opened by VS Code on a Mac

- **WHEN** an Expo consumer's devcontainer is opened by VS Code on a Mac with
  the listed pack's workspace extension in the container, the host extension
  installed locally on the Mac, the tools `eas-host status` checks present, and
  the workspace trusted on the Mac
- **THEN** `eas-host status` succeeds
- **AND** `eas-host build` with a profile from `eas.json` leaves the artifact
  under `.tmp/expo-bridge/`

### Scenario: setup grants no trust

- **WHEN** setup applies the Expo profile
- **THEN** it writes no bridge trust or security setting into any consumer file
- **AND** the first bridge request from the consumer's workspace asks for trust
  on the Mac

### Scenario: the bridge is unavailable

- **WHEN** the devcontainer runs where the workspace is not on the VS Code host
  — a Codespace, a non-Mac host, or no VS Code window
- **THEN** `eas-host status` exits non-zero
- **AND** the EAS cloud build path works unchanged

### Scenario: an Expo consumer adopted before the bridge updates

- **WHEN** update mode runs for a consumer whose `optional_bundles` includes
  `"expo"` and whose files lack the extension pack, the forwarded port, or the
  iOS rule
- **AND** `check-updates.py` reports `UP_TO_DATE`
- **THEN** update mode still proposes each missing edit from the guide's
  Optional Expo setup

### Scenario: a non-Expo consumer

- **WHEN** the consumer's `optional_bundles` omits `"expo"`
- **THEN** setup adds neither the extension pack, the forwarded port, its
  `portsAttributes` entry, nor the rule

## Pull request description guidance

### Requirement: a consumer may customize generated PR descriptions through a guidance file

Template setup and update SHALL evaluate a consuming repository's existing
`.github/pull_request_template.md` against the section structure the
`pr-gen-description` skill generates, proposing a section-by-section mapping in
two buckets — covered and extras — for the user to correct, and SHALL write or
delete nothing until the user confirms them. The extras SHALL be decided as one
batch, defaulting to capture, with three outcomes: capture them as instructions
in a consumer-owned `.github/pr-description-guidance.md` and reduce the template
to the `<!-- pr-gen-description: no-template -->` stub; drop them all and reduce
the template to the stub; or keep the template as it is. Capturing SHALL
translate a template section into a generation instruction rather than copying
its heading verbatim: the guidance file holds instructions, never section
headings.

When `.github/pr-description-guidance.md` exists, `pr-gen-description` SHALL
apply its instructions with precedence over the default generation of its own
sections, except that the guidance SHALL NOT collapse or rename the Verification
/ Reviewer Handoff split. `pr-gen-description` SHALL NOT read description
structure from the pull request template itself.

#### Scenario: an extra template section is captured as guidance

- **WHEN** a Workflow B consumer's `.github/pull_request_template.md` contains a
  section with no equivalent in the `pr-gen-description` structure, and the user
  chooses to capture it
- **THEN** the section is written as an instruction in
  `.github/pr-description-guidance.md`, the template is reduced to the
  `<!-- pr-gen-description: no-template -->` stub, and later PR-template updates
  preserve the guidance file unless the user explicitly replaces or removes it

#### Scenario: the user keeps the template as it is

- **WHEN** the user chooses to keep a template that has extras
- **THEN** no guidance file is written, the template is unchanged, and
  `pr-gen-description` reports it as not consulted on every generation

#### Scenario: guidance may not break the tense split

- **WHEN** `.github/pr-description-guidance.md` carries an instruction that
  would merge or rename the Verification and Reviewer Handoff sections
- **THEN** `pr-gen-description` preserves the two sections and their `- [x]` /
  `- [ ]` tense split regardless of the guidance

## Requirement: the installed catalog owns a complete reusable IWE scaffold

The installed agentdev catalog SHALL carry one complete IWE scaffold compatible
with its schemas and onboarding skills and separate from publisher memory.
Template consumption SHALL initialize knowledge by invoking
`/agentdev:iwe-bootstrap` and SHALL NOT maintain or copy a second seed source.

### Scenario: agent-devcontainer source is unavailable

- **WHEN** a consumer adopts IWE through an installed agentdev catalog without
  an agent-devcontainer source checkout
- **THEN** all scaffold content is available from the installed skill and
  adoption makes no request to another repository

## Requirement: fresh IWE adoption initializes consumer memory

For both adoption workflows, choosing IWE SHALL invoke `iwe-bootstrap`, then
invoke `iwe-setup`, and validate the resulting consumer workspace. The invoked
skill's confirmation gates SHALL remain in force.

### Scenario: fresh full-copy adoption

- **WHEN** Workflow A retains IWE and data is proven to be the unmodified
  publisher copy
- **THEN** adoption removes that publisher copy, invokes bootstrap, and onboards
  the consumer

### Scenario: adoption into an existing repository without knowledge

- **WHEN** Workflow B retains IWE and the bootstrap-managed destinations are
  absent
- **THEN** adoption invokes bootstrap and runs setup

### Scenario: a greenfield consumer

- **WHEN** an adopting project has no code
- **THEN** setup establishes product memory from the interview alone

### Scenario: required onboarding input is pending

- **WHEN** setup requires an unanswered question or confirmation
- **THEN** adoption reports pending work, preserves current data, and does not
  declare onboarding complete or reset it on resumption

## Requirement: an adopted knowledge base keeps its graph checks

When `optional_bundles` includes `"knowledge-base"`, adoption SHALL track
`docs/knowledge/tests/test_plan_checkboxes.py` and
`docs/knowledge/tests/test_banned_frontmatter_keys.py` and SHALL retain the
`banned-frontmatter-keys` pre-commit hook. A repository initialized by
`iwe-bootstrap` alone gets no such check, because bootstrap adds no hooks.

### Scenario: a consumer keeps the knowledge base

- **WHEN** adoption retains the knowledge-base bundle
- **THEN** both test files are tracked paths and the `banned-frontmatter-keys`
  hook stays in the consumer's pre-commit configuration

## Requirement: consumer knowledge survives adoption and updates

Adoption SHALL preserve pre-existing consumer knowledge, send partial or
incompatible bootstrap destinations to explicit reconciliation, and resolve
collisions with the user. Updates SHALL never invoke bootstrap, SHALL exclude
publisher data and bootstrap scaffold changes from consumer-memory changes,
SHALL narrow legacy broad knowledge tracking before checking updates, and SHALL
preserve the consumed ref until selected updates are applied. Schema changes
SHALL be reviewed against existing consumer data.

### Scenario: knowledge already exists

- **WHEN** adoption encounters consumer-authored data, including a modified
  publisher copy or partially completed onboarding
- **THEN** it preserves that data and resolves collisions without bootstrapping

### Scenario: an older marker tracks the entire knowledge directory

- **WHEN** update mode encounters broad knowledge tracking
- **THEN** it narrows tracking to retained reusable support paths before
  diffing, preserving unrelated paths and the consumed ref

### Scenario: publisher memory or the bundled scaffold changes

- **WHEN** an update changes the publisher's `docs/knowledge/data/` or an
  agentdev update changes bootstrap assets
- **THEN** template update mode does not apply those changes to consumer memory,
  does not invoke bootstrap, and does not rerun onboarding

### Scenario: IWE is declined

- **WHEN** the consumer declines IWE adoption
- **THEN** setup skips bootstrap and onboarding, removes copied IWE-only
  artifacts, and preserves pre-existing consumer knowledge

## Requirement: an update removes a retired codebase map

When a consumer holds codebase-map artifacts, update mode SHALL remove them
without asking: every `data/codebase/` document and the `data/codebase.md` hub,
the codebase schema and its `.iwe/config.toml` entries, the `iwe-map` key of
every `.agent.metadata.json` and each such file left empty, and any CI step or
pre-commit hook that runs `stale-map-docs.py`. It SHALL report each removal and
SHALL leave the workspace passing `iwe normalize` and `iwe schema validate`.
This is the one consumer-memory change update mode makes without the user's
decision.

### Scenario: a mapped consumer updates

- **WHEN** update mode runs for a consumer with a `data/codebase/` map and a CI
  step running `stale-map-docs.py`
- **THEN** the map documents, hub, schema, configuration entries, metadata keys,
  and CI step are removed, each removal is reported, and schema validation
  passes

### Scenario: metadata holds another key

- **WHEN** an `.agent.metadata.json` carries an `iwe-map` key beside another
  key, such as the root `template-consume` section
- **THEN** only the `iwe-map` key is removed and the file stays

### Scenario: a consumer never adopted the map

- **WHEN** update mode finds no codebase-map artifact
- **THEN** it changes nothing for the map and reports nothing about it

## Requirement: an update removes the retired Docker MCP gateway

When a consumer holds Docker MCP gateway artifacts and its choice log does not
record keeping the gateway, update mode SHALL remove them: the `gateway` server
in `.mcp.json`, the `mcp__gateway__*` permission in `.claude/settings.json`, and
any gateway wiring in a customized `.devcontainer/`. It SHALL stop tracking
`.mcp.json`, delete that file when no server remains, keep every other server,
report each removal, and tell the user that Docker Desktop MCP Toolkit tools are
no longer reachable from the container.

### Scenario: `.mcp.json` holds only the gateway

- **WHEN** update mode runs for a consumer whose `.mcp.json` registers only
  `gateway`
- **THEN** the file and its `tracked_paths` entry are removed and each removal
  is reported

### Scenario: `.mcp.json` holds another server

- **WHEN** a consumer's `.mcp.json` registers `gateway` beside its own server
- **THEN** only `gateway` is removed, the file stays, and its `tracked_paths`
  entry is removed

### Scenario: the consumer chose to keep the gateway

- **WHEN** the choice log records the consumer keeping the gateway
- **THEN** update mode leaves the gateway in place and reports that it did

### Scenario: a consumer holds no gateway artifact

- **WHEN** update mode finds no gateway artifact
- **THEN** it changes nothing for the gateway and reports nothing about it

## Requirement: every template path has one class

The guide SHALL classify every tracked path of the template as Template,
Customize, Optional, Publisher, or Generated. A consumer SHALL keep Template
paths, keep Customize paths and edit their project identity and owned paths,
keep an Optional path only together with the rest of its bundle, delete every
Publisher path, and never take a Generated path as template input. The root
`AGENTS.md` and `CLAUDE.md` and the `.claude/` directory SHALL survive the
deletion of publisher-only source.

### Scenario: a full copy deletes publisher-only source

- **WHEN** Workflow A deletes `.agents/`, `.claude-plugin/`, and `py_packages/`
- **THEN** the root `AGENTS.md`, `CLAUDE.md`, and `.claude/` remain, and the
  instructions scoped under the deleted trees leave with them

### Scenario: an existing repository receives the runtime unit

- **WHEN** Workflow B copies `.devcontainer/` and
  `devcontainer-compose-pins.yml`
- **THEN** the consumer's `.gitignore` ignores `.devcontainer/.env` and
  `.devcontainer/local.env` before the first container start, so the generated
  host state never reaches a commit

## Requirement: a retained custom-image bundle builds from an explicit choice

A consumer that keeps the custom-image bundle SHALL keep all of it — `ansible/`,
`ansible.cfg`, `docker/`, `.dockerignore`, `.github/actions/docker/`,
`.github/workflows/ci.yml`, `.github/workflows/delete-old-containers.yml`, and
the image job and image paths in the shared GitHub files. Because the
`agentdev-base` build mounts `py_packages/validate_agent_files/`,
`.claude-plugin/`, and `.agents/plugins/`, setup SHALL make the consumer choose
explicitly to retain that publisher source, to remove the validator and catalog
steps from the build, or to derive from a published image. A path a customized
build reads SHALL be added to the `.dockerignore` allow-list. A consumer that
drops the bundle SHALL also remove the `ci` job from `primary-checks.yml` and
the image and catalog paths from the shared path filter.

### Scenario: a consumer keeps the bundle after deleting publisher source

- **WHEN** a consumer keeps the custom-image bundle and has deleted the
  publisher-only source
- **THEN** setup asks which of the three directions to take, and does not assume
  the retained build still succeeds

## Requirement: catalog scripts act on the repository they run in

A script under the catalog's `bin/` SHALL find its target repository from the
working directory, through Git, and SHALL use its own location only to import
its sibling modules, so it works unchanged from a consumer's installed plugin
cache.

### Scenario: a consumer runs a catalog script

- **WHEN** a skill runs a catalog script from the consumer's checkout with the
  catalog installed in the plugin cache
- **THEN** the script acts on the consumer's repository, not on the plugin cache

## Rationale

### The guide owns the path inventory

Adoption is a file-level copy or merge driven by `/agentdev:template-consume`,
and update mode diffs the tracked paths from the recorded commit. The guide is
the one place that classifies each path; this spec holds only the requirements
that classification must satisfy, so a changed path edits the guide alone.

Rejected:

- **A second inventory in the knowledge base.** Two lists of the same paths
  drift apart.

### Knowledge data is never a template path

`docs/knowledge/data/` holds the publisher's project memory in the publisher and
the consumer's in a consumer: one path, two owners. A consumer's workspace comes
from the `iwe-bootstrap` scaffold in the installed catalog, which initializes
once and is never tracked.

Rejected:

- **Tracking `docs/knowledge/data/`.** Every difference is one owner's history,
  and applying it in either direction destroys the other's memory.
- **Seeding a consumer from the template checkout.** It needs the checkout and
  starts the consumer from the publisher's memory.

### Only full-image building is implemented

The custom-image bundle is the source that publishes the agentdev image family.
The publisher builds the full image from its own publisher source; stopping the
catalog and validator steps, or deriving from a published image, is the
consumer's own image work.

Rejected:

- **A generic derivative-image template.** The bundle would have to build
  without the publisher source it reads, which only a consumer's own changes can
  decide.

### One catalog tree, installed rather than copied

`.agents/plugins/agentdev/` is the catalog's single source: Claude Code reads it
through `.claude-plugin/`, OpenCode through the bridge plugin, and a consumer
runs it from the installed plugin without this repository.

Rejected:

- **A copy of the catalog per harness.** Two trees would have to be kept in
  step.
- **Scripts that find the repository from their own location.** In a consumer's
  plugin cache that location is the cache, not the consumer's repository.

### `validate_agent_files` ships on its own

The validator is a separately released package with its own `pyproject.toml` and
a test suite that needs no repository fixture. For a consumer it is
publisher-only source: the image installs the validator as an isolated uv tool
at `/usr/local/bin/validate_agent_files`.

Rejected:

- **One test suite shared with the plugin.** The released package would then
  depend on this repository's fixtures.
