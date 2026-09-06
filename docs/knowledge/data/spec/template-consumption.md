---
type: spec
description: How a project adopts this repository as a template — the normative requirements, with the full setup and update procedure owned by the agentdev template-consume skill.
generated:
  by: claude-code/opus-5
  at: 2026-09-06T05:39:02Z
sources:
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/65#discussion_r3794941822
---

# Template consumption

The procedure for adopting this repository's development environment and
conventions in another project is owned by the `agentdev` catalog's
`/agentdev:template-consume` skill, at
`.agents/plugins/agentdev/skills/template-consume/`. Its
`references/consumption-guide.md` is the single step-by-step guide — Workflow A
(full repository copy), Workflow B (existing repository), the optional
custom-image bundle, and verification — and its `SKILL.md` defines setup mode,
update mode, and the `.agentdev-template.json` marker file. Edit the guide, not
this document, when a step, a deleted-or-retained path, or a CI adaptation
changes. The skill ships in the plugin, so a consumer runs it from an installed
catalog without this repository checked out.

This document holds only the requirements the procedure must satisfy. Read
[Template boundary](../architecture/template-boundary.md) for the
keep/customize/optional/delete inventory the guide walks.

## Requirement: the finished project retains every runtime capability

The default setup SHALL retain every runtime capability the template's
devcontainer provides — the digest-pinned `agent-desktop` image,
Docker-in-Docker and Codespaces SSH, worktree-safe mounts, Xpra/VirtualGL, the
MCP gateway and secrets socket, persistent agent-state volumes with one shared
credentials volume, the image-staged `agentdev` catalog, keyring and GitHub
authentication, uv caching and pre-commit setup, and the opt-in egress firewall.
It SHALL NOT infer a language, create application code, choose dependencies, or
invent CI for the consuming project's product.

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
machine-parsed record of the consumed ref. Update mode SHALL diff only those
paths from that SHA and SHALL NOT advance the SHA past what was actually
applied.

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

## Requirement: the repository owns a complete reusable IWE seed

The repository SHALL maintain a clean seed in `templates/iwe/data/`, compatible
with its IWE schemas and onboarding skills and separate from publisher memory.
Consumption SHALL use the seed at the adopted agent-devcontainer ref and SHALL
NOT depend on the initial import repository remaining available.

### Scenario: the initial source is unavailable

- **WHEN** a consumer adopts IWE after the initial import repository disappears
- **THEN** all seed content is available from agent-devcontainer and adoption
  makes no request to the initial import repository

## Requirement: fresh IWE adoption initializes consumer memory

For both adoption workflows, choosing IWE SHALL install its reusable scaffold
and seed, invoke iwe-setup followed by iwe-map, and validate the resulting
consumer workspace. The invoked skills' confirmation gates SHALL remain in
force. Mapping SHALL be explicitly deferred for a project with no code.

### Scenario: fresh full-copy adoption

- **WHEN** Workflow A retains IWE and data is the unmodified publisher copy
- **THEN** adoption replaces that data with the seed and onboards the consumer

### Scenario: adoption into an existing repository without knowledge

- **WHEN** Workflow B retains IWE and its data directory is absent or empty
- **THEN** adoption installs the seed and runs setup before mapping

### Scenario: a greenfield consumer

- **WHEN** an adopting project has no code to map
- **THEN** setup establishes product memory and the report explicitly defers
  mapping

### Scenario: required onboarding input is pending

- **WHEN** setup or map requires an unanswered question or confirmation
- **THEN** adoption reports pending work, preserves current data, and does not
  declare onboarding complete or reset it on resumption

## Requirement: consumer knowledge survives adoption and updates

Adoption SHALL preserve pre-existing consumer knowledge and resolve collisions
with the user. Updates SHALL exclude publisher data and initialization seeds
from consumer-memory changes, narrow legacy broad knowledge tracking before
checking updates, and preserve the consumed ref until updates are applied.
Schema changes SHALL be reviewed against existing consumer data.

### Scenario: knowledge already exists

- **WHEN** adoption encounters consumer-authored data, including a modified
  publisher copy or partially completed onboarding
- **THEN** it preserves that data and resolves collisions without reseeding

### Scenario: an older marker tracks the entire knowledge directory

- **WHEN** update mode encounters broad knowledge tracking
- **THEN** it narrows tracking to retained reusable support paths before
  diffing, preserving unrelated paths and the consumed ref

### Scenario: publisher memory or seed content changes

- **WHEN** updates change publisher data or the seed
- **THEN** those changes are not applied to consumer memory and onboarding is
  not rerun

### Scenario: IWE is declined

- **WHEN** the consumer declines IWE adoption
- **THEN** setup skips seeding and onboarding, removes copied IWE-only
  artifacts, and preserves pre-existing consumer knowledge
