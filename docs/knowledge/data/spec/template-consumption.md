---
type: spec
description: How a project adopts this repository as a template — the normative requirements, with the full setup and update procedure owned by the agentdev template-consume skill.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/agent-code/check-updates.py
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

## Requirement: publisher-only source never survives adoption

A consumer SHALL delete `.agents/`, `.claude-plugin/`, and `py_packages/`, and
SHALL adapt every CI workflow, pre-commit hook, `pyproject.toml` entry, and path
filter that referenced them. Agent-file validation, when retained, SHALL run the
validator the digest-pinned image provides, never the deleted working-tree
package.

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

### The Expo profile prepares EAS builds and leaves the workflow to Expo's plugin

Expo's official `expo@claude-plugins-official` plugin owns the agent workflow;
the profile only prepares the consumer for it. Every `eas.json` build profile
pins `bun` because EAS macOS workers do not default to the image's bun, and the
image's bun writes a `bun.lock` an older bun cannot read under
`--frozen-lockfile`. An EAS build needs `api.expo.dev`, `cdp.expo.dev`,
`expo.dev`, `storage.googleapis.com`, `wf-artifacts.eascdn.net`, and
`mcp.expo.dev` (the plugin's MCP server); the two CDN hosts' addresses rotate,
so the allowlist may need a container restart. `eas` treats an empty
`EXPO_TOKEN` as no token, which makes the template-wide passthrough of an unset
host variable inert. EAS Simulator writes a session token to
`.env.eas-simulator`, hence the ignore. The Expo `AGENTS.md` becomes a section
of the root `AGENTS.md`, because that is the one instruction file every agent
reads. Apple signing for device and store builds stays a one-time human
`eas credentials` step, app configuration such as `expo.ios.bundleIdentifier` is
the Expo plugin's, and the guide sets `EXPO_TOKEN` up only for a local Docker
host and Coder.

Rejected:

- **An agentdev EAS skill.** It duplicates the workflow Expo's plugin owns.
- **Passing the token only from the profile.** An Expo-only edit to the
  Template-class `.devcontainer/devcontainer.json` makes every later
  devcontainer update a manual merge.
- **Guidance with no recorded profile.** Update mode would not know the consumer
  is an Expo app.
- **Persisting the token on the shared agent-auth volume.** The token belongs to
  the hosting environment, where it can be scoped and revoked.

### The Expo bridge's record lives in its own repository

The VS Code Expo bridge's whole record — design, plans, bugs, and backlog,
finished ones included — lives in the knowledge graph of
`plume-works/vscode-expo-bridge`. This repository keeps only the Expo profile's
wiring and the release notes for that wiring, and links to bridge documents by
absolute GitHub URL on `main`. The extension repository keeps its project memory
with `/agentdev:iwe-bootstrap` alone.

Rejected:

- **Keeping finished bridge plans and fixed bugs here.** The product's record
  would be split across two repositories, with open bugs there linking into
  finished plans here.
- **Adopting the whole template in the extension repository.** It brings a
  devcontainer and a catalog the extension does not need for project memory.

### `validate_agent_files` ships on its own

The validator is a separately released package with its own `pyproject.toml` and
a test suite that needs no repository fixture. For a consumer it is
publisher-only source: the image installs the validator as an isolated uv tool
at `/usr/local/bin/validate_agent_files`.

Rejected:

- **One test suite shared with the plugin.** The released package would then
  depend on this repository's fixtures.

### The graph keeps no codebase map

The knowledge base keeps no `data/codebase/` map and the catalog ships no map
skill. No workflow skill or agent was told to read the map; a stamped source
digest proves a map document was re-stamped, not that its text is correct; and
every pull request that touched mapped code paid a refresh, a CI gate, and
digest lines that conflict between branches. A new reader orients from the code,
the README, and the specs `/agentdev:iwe-setup` drafts.

Rejected:

- **A one-page orientation document in its place** — it duplicates the README
  and the specs.
- **An advisory digest gate** — it keeps the refresh cost and the risk of wrong
  text.
- **Telling planners to read derived text** — no check confirms that text.

### Update mode removes a retired codebase map without asking

Migrating a consumer's documents is otherwise the user's decision. The codebase
map is the exception because the installed catalog no longer ships
`stale-map-docs.py`, so a consumer that kept its map would keep a CI step or
hook that fails.

Rejected:

- **Asking the user whether to keep the map.** Keeping it leaves a gate that
  cannot pass.

### PR description guidance is a separate instruction file

`.github/pull_request_template.md` stays a pure two-state pointer, the stub or a
real template, so a template update can tell the two apart, and the guidance in
`.github/pr-description-guidance.md` is consumer-created state that updates
preserve. The guidance holds instructions because `pr-gen-description` owns the
section list; a section such as `## Rollback plan` is captured as an instruction
to cover rollback.

Rejected:

- **A guidance block inside the pull request template.** The template would stop
  being a two-state pointer, and an update would have to merge consumer text
  into a template path.
- **A list of section headings.** It is a structure file by another name, which
  `pr-gen-description`'s own section list supersedes.

### Setup progress lives in a root file; the consumed ref stays in JSON

`.agentdev-template-progress.md` sits at the consumer root because the
consumer's IWE graph does not exist until the bootstrap step, itself one of the
tasks, and a consumer who declines IWE never has one; a root file serves both.
`consumed_ref` stays in the `template-consume` section of `.agent.metadata.json`
because that JSON has one parse with one failure signal, `INVALID_MARKER`, and a
wrongly advanced ref silently skips upstream changes forever. The knowledge-base
summary records why the consumer is configured as it is and points at the root
file, because two task lists extended on every update have nothing keeping them
in sync.

Rejected:

- **The progress record in the consumer's IWE graph.** It does not exist during
  bootstrap, nor ever for a consumer without IWE.
- **The consumed SHA read from the progress document.** A SHA in prose has no
  parse and no failure signal.
- **A task list mirrored in the knowledge-base summary.** The two copies drift.
