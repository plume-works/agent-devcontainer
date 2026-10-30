---
type: spec
description: How a project adopts this repository as a template — the normative requirements, with the full setup and update procedure owned by the agentdev template-consume skill.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T02:01:26Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/65#discussion_r3794941822
- resource: .devcontainer/devcontainer.json
- resource: https://github.com/plume-works/vscode-expo-bridge
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

This document holds only the requirements the procedure must satisfy. Read
[Template boundary](../architecture/template-boundary.md) for the
keep/customize/optional/delete inventory the guide walks.

## Requirement: the finished project retains every runtime capability

The default setup SHALL retain every runtime capability the template's
devcontainer provides — the digest-pinned `agentdev-devcontainer` image with its
supervised nested Docker and Codespaces SSH, worktree-safe mounts,
Xpra/VirtualGL, the MCP gateway and secrets socket, persistent agent-state
volumes with one shared credentials volume, the image-staged `agentdev` catalog,
keyring and GitHub authentication, uv caching and pre-commit setup, and the
opt-in egress firewall. It SHALL NOT infer a language, create application code,
choose dependencies, or invent CI for the consuming project's product.

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

A consumer SHALL delete `.agents/`, `.claude-plugin/`, `py_packages/`, and
`scripts/validate-super-linter-tool-versions.sh`, and SHALL adapt every CI
workflow, pre-commit hook, `pyproject.toml` entry, and path filter that
referenced them. Agent-file validation, when retained, SHALL run the validator
the digest-pinned image provides, never the deleted working-tree package.

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
pull request; `ai-review-present` SHALL waive its requirement only for the bot
logins listed in `TRUSTED_BOT_ACTORS`, matched exactly and only when `user.type`
is `Bot`. The gate checks that the pull request has a review, not that its head
commit does — a copy comparing the review's `commit_id` to the head SHA is a
policy change. The fork gate and write-access gate SHALL be preserved as
written; the owner gate SHALL be repointed at the consumer. The
`workflow_dispatch` bridge SHALL be retained so default-branch comment events
can run the pull request head branch's workflow and attach checks to that head.

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

Neither file SHALL appear in `tracked_paths`; both are consumer-created state,
not template paths.

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
`AGENTS.md` body under an `## Expo` section.

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
- **AND** `check-updates.sh` reports `UP_TO_DATE`
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
`pr-gen-description` skill generates, proposing a section-by-section mapping for
the user to confirm. Sections with no equivalent in that structure MAY be
captured, at the user's choice, as instructions in a consumer-owned
`.github/pr-description-guidance.md`; capturing SHALL translate a template
section into a generation instruction rather than copying its heading verbatim.

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
invoke `iwe-setup` followed by `iwe-map`, and validate the resulting consumer
workspace. The invoked skills' confirmation gates SHALL remain in force. Mapping
SHALL be explicitly deferred for a project with no code.

### Scenario: fresh full-copy adoption

- **WHEN** Workflow A retains IWE and data is proven to be the unmodified
  publisher copy
- **THEN** adoption removes that publisher copy, invokes bootstrap, and onboards
  the consumer

### Scenario: adoption into an existing repository without knowledge

- **WHEN** Workflow B retains IWE and the bootstrap-managed destinations are
  absent
- **THEN** adoption invokes bootstrap and runs setup before mapping

### Scenario: a greenfield consumer

- **WHEN** an adopting project has no code to map
- **THEN** setup establishes product memory and the report explicitly defers
  mapping

### Scenario: required onboarding input is pending

- **WHEN** setup or map requires an unanswered question or confirmation
- **THEN** adoption reports pending work, preserves current data, and does not
  declare onboarding complete or reset it on resumption

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
