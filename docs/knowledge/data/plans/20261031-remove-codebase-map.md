---
type: plan
created: 2026-10-31
release:
- features/agentdev-iwe-workflow-skills
- features/consumer-iwe-seed
- features/resumable-template-consumption
description: Remove the data/codebase/ map, the iwe-map skill, its staleness check and push gate from the catalog, this workspace, and the bootstrap scaffold, and have a template update remove the map from a consumer.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T16:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-map/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .github/workflows/validate-agent-files.yml
stage: done
completed: 2026-10-31
---

# Remove the codebase map

## Context

The `data/codebase/` map is a derived description of the code, one document per
component, each pinned to a `source_digest` of the files it describes. The
[workflow skills](../features/agentdev-iwe-workflow-skills.md) give it one
writer, `/agentdev:iwe-map`. [Fresh codebase map on
push](../features/fresh-map-on-push.md) gates every agent push on the digest
check, CI runs the same check, and [digest masks for version
bumps](../features/map-masks-version-bumps.md) keep pin updates from marking
docs stale.

No workflow skill or agent is instructed to read the map. Every instruction that
names `data/codebase/` writes, refreshes, or gates it. Agents orient with `grep`
over the code plus the `spec/` and `architecture/` documents. A digest only
shows that a document was re-stamped after its sources changed, not that its
text is still correct.

Keeping it costs every pull request that touches mapped code: a refresh before
push, a CI gate, and digest lines that conflict between parallel branches. The
maintainer decided to remove the map. `/agentdev:iwe-setup` already drafts the
module-layout architecture document that orients a new reader, so it covers the
cold start the map was meant for. Consumers that adopted the map lose its
tooling with this catalog version, so a template update removes it from them.

## Approach

Delete the lane outright: the `iwe-map` skill and its `stale-map-docs.py`, the
push helper's map check and its two result codes, the CI step, the codebase
schema and hub, the scaffold's example map, and every map document in this
workspace. Every document, skill, and spec that hands work to the map loses that
handoff. `.agent.metadata.json` stays as a format, because the root file's
`template-consume` section is the adoption marker; only its `iwe-map` key goes,
and the four files in this repository that hold nothing else are deleted. The
map-doc stamper task is retired with the map; backlog tasks gain a `cancelled`
stage, mapped to OKF `status: deprecated` as for cancelled plans and bugs, so
that retirement stays listed like every other work item.

Template-consume update mode removes a consumer's map without asking, as the one
exception to its rule that migrating consumer documents is the user's decision:
the installed catalog no longer ships the script the consumer's map tooling
calls, so a consumer that keeps the map keeps a CI step that fails.

Rejected:

- **Keeping a one-page orientation doc** (the hub's `## Getting around`) without
  digests or a gate. It duplicates what setup's architecture document and the
  repository README already state.
- **Making the gate advisory.** It keeps the full refresh cost and the risk of
  wrong content, and only removes the push block.
- **Telling planners to read the map.** It adds derived text to every plan's
  input that no check confirms is still correct: a digest proves re-stamping,
  not accuracy.

## Implementation Steps

### Task 1: Remove the map tooling from the catalog

**Files:** Delete: `.agents/plugins/agentdev/skills/iwe-map/`,
`.agents/plugins/agentdev/tests/test_stale_map_docs.py`,
`.agents/plugins/agentdev/tests/test_stale_map_docs_masks.py`,
`.agents/plugins/agentdev/tests/test_stale_map_docs_replay.py`,
`.agents/plugins/agentdev/tests/test_push_branch_map_check.py`,
`docs/knowledge/tests/test_devcontainer_metadata_mask.py`,
`docs/knowledge/tests/test_pin_metadata_masks.py`,
`docs/knowledge/tests/test_pre_commit_rev_mask.py`. Modify:
`.agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py`,
`.agents/plugins/agentdev/skills/pr-open/SKILL.md`,
`.agents/plugins/agentdev/skills/update-branch/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-review/SKILL.md`,
`.agents/plugins/agentdev/agents/iwe-verifier.agent.md`.

- [x] Delete the `iwe-map` skill directory and the seven test files that load
  `stale-map-docs.py` or test the push gate.
  - **Evidence:** commit b5f5a4b "Remove the iwe-map skill and the push map
    check" deletes `skills/iwe-map/` and the seven test files.
- [x] `push-branch.py` runs no map check: drop `MAP_STALE`, `MAP_CHECK_FAILED`,
  `MAP_CHECK_SCRIPT`, the `--skip-map-check` option, the `MAP_CHECK=` output
  line, the check function, and their usage-text and result-name entries.
  Branch-up-to-date reports `SUCCESS` with `ACTION=none` directly.
  - **Evidence:** commit b5f5a4b "Remove the iwe-map skill and the push map
    check"; `push-branch.py` holds no `MAP_` constant, `--skip-map-check`, or
    `MAP_CHECK=` line, and `uv run pytest .agents/plugins/agentdev/tests` passed
    (424).
- [x] `pr-open` step 8 lists no map result codes, no `--skip-map-check`, and no
  `MAP_STALE` refresh; its stack-publish note no longer mentions a map check.
  - **Evidence:** commit b5f5a4b "Remove the iwe-map skill and the push map
    check" edits `pr-open/SKILL.md` step 8 and its stack-publish note.
- [x] `update-branch` step 2 no longer names `MAP_STALE`.
  - **Evidence:** commit b5f5a4b "Remove the iwe-map skill and the push map
    check" edits `update-branch/SKILL.md` step 2.
- [x] `pr-review` drops its IGNORE rule for stale codebase-map docs.
  - **Evidence:** commit b5f5a4b "Remove the iwe-map skill and the push map
    check" removes the IGNORE rule from `pr-review/SKILL.md`.
- [x] The verifier's audit drops the stale-map-docs item.
  - **Evidence:** commit b5f5a4b "Remove the iwe-map skill and the push map
    check" removes the item from `iwe-verifier.agent.md`.
- [x] `uv run pytest .agents/plugins/agentdev/tests` passes, and the
  `Validate Agent Files` command CI runs
  (`.github/workflows/validate-agent-files.yml`) passes.
  - **Evidence:** on commit b5f5a4b "Remove the iwe-map skill and the push map
    check", `uv run pytest .agents/plugins/agentdev/tests` passed (424) and
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reported 67/67 skills valid, 0 errors.

### Task 2: Remove the map from onboarding and template consumption

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.py`,
`.agents/plugins/agentdev/tests/test_iwe_bootstrap.py`,
`.agents/plugins/agentdev/skills/template-consume/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`.agents/plugins/agentdev/tests/test_template_consume_check_updates.py`.

- [x] `iwe-setup` step 3 drops the parenthetical that defers a per-module map to
  `/agentdev:iwe-map`; the starting architecture document is the onboarding's
  code orientation.
  - **Evidence:** commit 9bde574 "Drop the map from onboarding and remove it on
    template update" edits `iwe-setup/SKILL.md` step 3.
- [x] `iwe-bootstrap` names only `/agentdev:iwe-setup` as the next step (rule 2,
  the `SUCCESS` result row, completion criteria), and `bootstrap-iwe.py` prints
  `NEXT_SKILLS=iwe-setup`; `test_iwe_bootstrap.py` asserts that value.
  - **Evidence:** commit 9bde574 "Drop the map from onboarding and remove it on
    template update"; `uv run pytest .agents/plugins/agentdev/tests` passed
    (424), including `test_iwe_bootstrap.py` asserting `NEXT_SKILLS=iwe-setup`.
- [x] Template-consume setup step 5 and the guide's "Onboard the consumer's
  project memory" invoke only `/agentdev:iwe-setup`. The greenfield case no
  longer defers mapping, and verification drops the `stale-map-docs.py` check.
  - **Evidence:** commit 9bde574 "Drop the map from onboarding and remove it on
    template update" edits `template-consume/SKILL.md` setup step 5 and the
    guide's onboarding, greenfield, and verification text.
- [x] Template-consume update mode removes a consumer's codebase map without
  asking, and reports each removal. The step sits in update mode's procedure,
  and step 8's "migrating their documents is the user's decision" names it as
  the exception. It removes, wherever present, every `data/codebase/` document
  and the `data/codebase.md` hub through `iwe delete`, then the de-linked lines
  that deletion leaves in other documents; `.iwe/schemas/codebase.yaml`, the
  `[schemas.codebase]` block, and `"data/codebase"` in the hub schema's `match`
  list of `.iwe/config.toml`; the `iwe-map` key of every `.agent.metadata.json`,
  and each such file left holding no key; and any CI step or pre-commit hook
  that runs `stale-map-docs.py`. It then runs `iwe normalize` and
  `iwe schema validate` from the consumer root. The guide's update section
  states the same, and drops the sentence saying update mode never re-runs
  `/agentdev:iwe-map`.
  - **Evidence:** commit 9bde574 "Drop the map from onboarding and remove it on
    template update" adds update-mode step 9, names it as the exception in step
    8, and states the removal in the guide's `## Ongoing maintenance`.
- [x] The "metadata without template-consume" fixture in
  `test_template_consume_check_updates.py` uses a neutral key in place of
  `iwe-map`, and the test passes.
  - **Evidence:** commit 9bde574 "Drop the map from onboarding and remove it on
    template update" uses an `other-skill` key;
    `uv run pytest .agents/plugins/agentdev/tests` passed (424).

### Task 3: Remove the map from the scaffold and this workspace's support files

**Files:** Delete: `.iwe/schemas/codebase.yaml`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/.iwe/schemas/codebase.yaml`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/codebase.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/codebase/`.
Modify, in this workspace and byte-identically in the scaffold:
`.iwe/config.toml`, `docs/knowledge/AGENTS.md`, `docs/knowledge/SCHEMA.md`,
`docs/knowledge/STRUCTURE.md`, `docs/knowledge/README.md`,
`docs/knowledge/CHANGELOG.md`. Modify, scaffold only:
`assets/docs/knowledge/data/index.md`, `assets/docs/knowledge/data/log.md`.

- [x] Delete both `codebase.yaml` schemas, and remove `[schemas.codebase]` and
  `"data/codebase"` from the hub match list in both `config.toml` copies.
  - **Evidence:** commit a94e8d3 "Remove the codebase lane from the scaffold and
    workspace docs" deletes both schemas and edits both `config.toml` copies,
    byte-identical.
- [x] Delete the scaffold's `data/codebase.md` and its four `*.example.md` map
  docs; the scaffold's `data/index.md` and `data/log.md` no longer name the
  codebase hub.
  - **Evidence:** commit a94e8d3 "Remove the codebase lane from the scaffold and
    workspace docs" deletes the scaffold hub and its four example docs and edits
    the scaffold's `data/index.md` and `data/log.md`.
- [x] `AGENTS.md`: drop the "Code structure changed" operating-loop item, the
  codebase-map provenance clause, and the `/agentdev:iwe-map` skill-table row.
  - **Evidence:** commit a94e8d3 "Remove the codebase lane from the scaffold and
    workspace docs" edits both `AGENTS.md` copies, byte-identical.
- [x] `SCHEMA.md`: drop the `## Codebase map` section and the codebase-map
  examples under `sources`, `verified`, and `stale_after`.
  - **Evidence:** commit a94e8d3 "Remove the codebase lane from the scaffold and
    workspace docs" edits both `SCHEMA.md` copies, byte-identical.
- [x] `STRUCTURE.md`: drop the "codebase map is derived truth" paragraph and
  `codebase` from the schema and hub listings.
  - **Evidence:** commit a94e8d3 "Remove the codebase lane from the scaffold and
    workspace docs" edits both `STRUCTURE.md` copies, byte-identical, and also
    drops `map` from the skill list.
- [x] `README.md` drops `codebase.md codebase/` from its tree.
  - **Evidence:** commit a94e8d3 "Remove the codebase lane from the scaffold and
    workspace docs" edits both `README.md` copies, byte-identical.
- [x] `CHANGELOG.md` gains a `### Removed` entry under `[Unreleased]` telling a
  clone of an earlier copy to delete `data/codebase/`, `data/codebase.md`,
  `.iwe/schemas/codebase.yaml`, and their `config.toml` entries.
  - **Evidence:** commit a94e8d3 "Remove the codebase lane from the scaffold and
    workspace docs" adds the `### Removed` entry to both `CHANGELOG.md` copies.
- [x] `uv run pytest docs/knowledge/tests` passes, including the
  scaffold-matches-publisher and seed validation tests.
  - **Evidence:** on commit a94e8d3 "Remove the codebase lane from the scaffold
    and workspace docs", `uv run pytest docs/knowledge/tests` passed (40),
    including `test_checked_in_seed_matches_normalized_output`.

### Task 4: Remove this repository's map and its CI and metadata

**Files:** Delete: `docs/knowledge/data/codebase/`,
`docs/knowledge/data/codebase.md`, `.agent.metadata.json`,
`.devcontainer/.agent.metadata.json`, `.github/.agent.metadata.json`,
`ansible/roles/.agent.metadata.json`. Modify:
`.github/workflows/validate-agent-files.yml`, `README.md`,
`.agents/plugins/agentdev/README.md`, `docs/knowledge/data/index.md`,
`scripts/tests/test_download_claude_responder_runs.py`.

- [x] Remove every map document with `iwe delete`, the hub last, and remove the
  de-linked lines it leaves in `data/index.md` and
  `backlog/remove-agentdev-session-start-hook.md`. Plans and the log keep the
  flattened text as history.
  - **Evidence:** commit 7643d40 "Remove this repository's codebase map, its CI
    step, and metadata" deletes the 28 map docs and the hub through `iwe delete`
    and drops the de-linked lines from `data/index.md` and
    `remove-agentdev-session-start-hook.md`; `iwe schema validate` passed.
- [x] Delete the four `.agent.metadata.json` files; each holds only an `iwe-map`
  key.
  - **Evidence:** commit 7643d40 "Remove this repository's codebase map, its CI
    step, and metadata" deletes all four.
- [x] `validate-agent-files.yml` drops the "Check codebase map docs against
  their sources" step, and the paths-filter comment and entries that track map
  sources (`.pre-commit-config.yaml`, `devcontainer-compose-pins.yml`,
  `docs/knowledge/tests/**`, `docs/knowledge/AGENTS.md`,
  `docs/knowledge/SCHEMA.md`, `docs/knowledge/STRUCTURE.md`,
  `docs/knowledge/data/codebase/**`). `.iwe/**` stays.
  - **Evidence:** commit 7643d40 "Remove this repository's codebase map, its CI
    step, and metadata" removes the step, the comment, and the seven paths,
    keeping `.iwe/**`.
- [x] The root README's IWE section and the catalog README drop the map from
  their descriptions and the `iwe-map` rows from their skill tables.
  - **Evidence:** commit 7643d40 "Remove this repository's codebase map, its CI
    step, and metadata" edits `README.md` and
    `.agents/plugins/agentdev/README.md`.
- [x] `git grep -n -I -E 'iwe-map|stale-map-docs|MAP_STALE|MAP_CHECK|data/codebase|source_digest'`
  matches nothing outside `docs/knowledge/data/plans/`,
  `docs/knowledge/data/log.md`, `docs/knowledge/data/releases/`,
  `docs/knowledge/data/spec/` (Ship merges the spec changes), both
  `CHANGELOG.md` copies, documents whose `stage` is `done`, `deprecated`, or
  `cancelled`, a hub link whose title names such a document, the
  template-consume `SKILL.md` and `consumption-guide.md` (update mode names the
  artifacts it removes), and `data/someday/remove-codebase-memory-mcp.md` (its
  evidence that no agent read the map).
  - **Evidence:** on commit 21217a4a "Cancel the map-doc stamper task", the grep
    matched only the exempt paths, `stage: done` bugs `missing-map-skill` and
    `pin-bumps-invalidate-map-docs`, the `deprecated` features
    `fresh-map-on-push` and `map-masks-version-bumps`, the `cancelled`
    `map-doc-stamper`, and the hub links to a done plan (`data/plans.md`) and to
    that task (`data/backlog.md`).

### Task 5: Let a backlog task be cancelled

**Files:** Modify, in this workspace and byte-identically in the scaffold:
`.iwe/schemas/task.yaml`, `docs/knowledge/AGENTS.md`,
`docs/knowledge/SCHEMA.md`, `docs/knowledge/CHANGELOG.md`.

- [x] `task.yaml` accepts `stage: cancelled` beside `planned` and `done`, in
  both copies.
  - **Evidence:** commit cf99950 "Let a backlog task be cancelled" edits both
    `task.yaml` copies, byte-identical.
- [x] `SCHEMA.md` lists `cancelled` in the task example's stage comment and maps
  task `cancelled` to `status: deprecated` in the `stage` versus `status` table,
  dropping `task` from the types that never set `status`; `AGENTS.md` lists
  `planned|done|cancelled` for backlog and adds a "Task dropped" operating-loop
  item: `stage: cancelled`, link moved to `## Cancelled` in `data/backlog.md`.
  - **Evidence:** commit cf99950 "Let a backlog task be cancelled" edits both
    `SCHEMA.md` and `AGENTS.md` copies, byte-identical.
- [x] `CHANGELOG.md` gains an `### Added` entry under `[Unreleased]` for the
  task `cancelled` stage.
  - **Evidence:** commit cf99950 "Let a backlog task be cancelled" adds the
    entry to both `CHANGELOG.md` copies.
- [x] `uv run pytest docs/knowledge/tests` passes, and `iwe schema validate`
  passes from the repository root.
  - **Evidence:** on commit cf99950 "Let a backlog task be cancelled",
    `uv run pytest docs/knowledge/tests` passed (40) and `iwe schema validate`
    exited 0.

### Task 6: Update the knowledge graph

**Files:** Modify: `docs/knowledge/data/features/fresh-map-on-push.md`,
`docs/knowledge/data/features/map-masks-version-bumps.md`,
`docs/knowledge/data/features/agentdev-iwe-workflow-skills.md`,
`docs/knowledge/data/features/consumer-iwe-seed.md`,
`docs/knowledge/data/features/native-stacked-prs.md`,
`docs/knowledge/data/backlog/map-doc-stamper.md`,
`docs/knowledge/data/backlog.md`,
`docs/knowledge/data/backlog/remove-agentdev-session-start-hook.md`,
`docs/knowledge/data/backlog/resilient-task-evidence.md`,
`docs/knowledge/data/architecture/agent-metadata-files.md`,
`docs/knowledge/data/architecture/template-boundary.md`,
`docs/knowledge/data/architecture/pr-review-correctness-bar.md`.

- [x] `fresh-map-on-push` and `map-masks-version-bumps` move to
  `stage: deprecated`, with OKF `status` set from the `SCHEMA.md` table.
  - **Evidence:** commit 0340656 "Retire the codebase map in the knowledge
    graph" sets both to `stage: deprecated` with `status: deprecated`;
    `iwe schema validate` passed.
- [x] `agentdev-iwe-workflow-skills` lists eight skills without Map, and drops
  the "Map owns the `data/codebase/` lane" behaviour, the Setup edge case, and
  the `iwe-map` source.
  - **Evidence:** commit 0340656 "Retire the codebase map in the knowledge
    graph".
- [x] `consumer-iwe-seed` names only `iwe-setup` as the onboarding step after
  bootstrap.
  - **Evidence:** commit 0340656 "Retire the codebase map in the knowledge
    graph".
- [x] `native-stacked-prs` drops the stack-push edge case about the map check.
  - **Evidence:** commit 0340656 "Retire the codebase map in the knowledge
    graph".
- [x] The `map-doc-stamper` task is `stage: cancelled` with
  `status: deprecated`, and its link moves to a new `## Cancelled` section after
  `## Done` in `data/backlog.md`.
  - **Evidence:** commit 21217a4a "Cancel the map-doc stamper task" sets
    `stage: cancelled` and `status: deprecated` and moves the link to a new
    `## Cancelled` section; `iwe schema validate` exited 0.
- [x] `remove-agentdev-session-start-hook` drops its map-refresh steps and the
  map docs from its version-pin sweep; `resilient-task-evidence` drops the
  `source_digest` alternative.
  - **Evidence:** commit 7643d40 "Remove this repository's codebase map, its CI
    step, and metadata" drops the map-refresh steps and commit 0340656 "Retire
    the codebase map in the knowledge graph" the map docs from the pin sweep and
    the `source_digest` alternative.
- [x] `agent-metadata-files` names template-consume's root section as the only
  current consumer and drops the `iwe-map` example, the digest-mask consumer
  entry, and the `stale-map-docs.py` sources and references; the root-to-leaf
  resolution stays as the contract for a future colocated consumer.
  `template-boundary` drops the root file's `iwe-map` rules, and
  `pr-review-correctness-bar` drops the codebase-map review-ignore item.
  - **Evidence:** commit 0340656 "Retire the codebase map in the knowledge
    graph" edits all three architecture docs; `iwe schema validate` passed.

### Task 7: Validate

- [x] `iwe normalize` and `iwe schema validate` pass from the repository root.
  - **Evidence:** on commit e199a638 "Record the stamper and grep evidence for
    the codebase map removal", `iwe normalize` left the tree clean and
    `iwe schema validate` exited 0.
- [x] `uv run pytest .agents/plugins/agentdev/tests docs/knowledge/tests`
  passes.
  - **Evidence:** on commit e199a638 "Record the stamper and grep evidence for
    the codebase map removal", the run passed (464).

### Task 8: CI passes

- [x] The pull request's CI is green.
  - **Evidence:** PR #585 at merge commit 9ccdfba: Primary checks run
    41222473715, Agent files validation 41222473792, Knowledge base validation
    41222473641, Validate Renovate config 41222473748, and AI Responder
    41222473660 all concluded success; the PR squash-merged to main as commit
    5ee5e4c "Remove the codebase map (#585)".

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — the Map skill and the
push gate are retired; the spec's `description` and `sources` drop Map and
`iwe-map`:

``` markdown
## REMOVED Requirements

### Requirement: Map derives the codebase lane from the code and refreshes it incrementally

Retired: the catalog no longer ships the Map skill, and no workspace keeps a
`data/codebase/` lane.

### Requirement: Map staleness reflects described content

Retired with the map: there is no staleness check to classify documents.

### Requirement: Map masks a version-only change before refreshing

Retired with the map: there are no digests to mask.

### Requirement: An agent push carries a fresh codebase map

Retired: the push helper runs no map check, and the AI review has no map
staleness to defer to CI.
```

[IWE bootstrap](../spec/iwe-bootstrap.md):

``` markdown
## MODIFIED Requirements

### Requirement: bootstrap and onboarding are separate operations

Bootstrap SHALL stop after the blank workspace validates. It SHALL NOT run
`iwe-setup`, answer its confirmation gates, or merge repository CI and
pre-commit configuration.

#### Scenario: direct initialization succeeds

- **WHEN** bootstrap creates a workspace for a mounted repository
- **THEN** it reports `iwe-setup` as the next product-onboarding operation
```

[Template consumption](../spec/template-consumption.md):

``` markdown
## MODIFIED Requirements

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

## ADDED Requirements

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

- **WHEN** an `.agent.metadata.json` carries an `iwe-map` key beside another key,
  such as the root `template-consume` section
- **THEN** only the `iwe-map` key is removed and the file stays

### Scenario: a consumer never adopted the map

- **WHEN** update mode finds no codebase-map artifact
- **THEN** it changes nothing for the map and reports nothing about it
```

## Depends on

None. [Conflict-free knowledge layout](20261031-kb-conflict-free-layout.md)
ships after this plan.

## Verification

- `uv run pytest .agents/plugins/agentdev/tests docs/knowledge/tests` passes.
- the `Validate Agent Files` command CI runs
  (`.github/workflows/validate-agent-files.yml`) passes.
- `iwe normalize` and `iwe schema validate` pass from the repository root.
- The `git grep` in Task 4 matches only history documents.
- `push-branch.py --help` lists no map option or result code.
- In a scratch consumer under `/tmp` holding a bootstrapped workspace with a
  `data/codebase/` doc, the `iwe-map` metadata key beside a `template-consume`
  section, and a workflow step running `stale-map-docs.py`, following update
  mode's map-removal step leaves no map artifact, keeps the `template-consume`
  section, and passes `iwe schema validate`.
- CI on the pull request is green.

## Verification results

- `uv run pytest .agents/plugins/agentdev/tests docs/knowledge/tests` passed
  (464); the `Validate Agent Files` command reported 0 errors; `iwe normalize`
  and `iwe schema validate` passed; `push-branch.py --help` names no map option
  or result code.
- The Task 4 grep matched only the paths its revised check exempts.
- A scratch consumer under `/tmp`, built from the pre-removal scaffold with four
  `data/codebase/` docs, an `iwe-map` key beside `template-consume` in the root
  metadata, an `iwe-map`-only `.github/.agent.metadata.json`, and a CI step
  running `stale-map-docs.py`, was taken through update mode's step 9 as
  written: no map document, hub, schema, config entry, `iwe-map` key, or CI step
  remained, the root file kept `template-consume`, the `iwe-map`-only file was
  deleted, and `iwe schema validate` passed. The consumer's scaffold
  `AGENTS.md`, `SCHEMA.md`, and `STRUCTURE.md` still describe the map until
  update mode's tracked-path diff applies this version's copies.

## Out of scope

- The codebase-memory MCP server and its hooks; a separate plan owns them.
- A catalog version bump; the release cut owns it.
- Rewriting plans, the log, and release pages that describe the map's history.
- A one-page orientation doc to replace the hub's `## Getting around`.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `.agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py:35-40` —
  `MAP_STALE`, `MAP_CHECK_FAILED`, `MAP_CHECK_SCRIPT`
- `.agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py:47-76` —
  usage text, `--skip-map-check`, `MAP_CHECK=` output, result codes 6 and 7
- `.agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py:101` —
  `--skip-map-check` parsing
- `.agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py:132-179` —
  `check_map_freshness`
- `.agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py:310-311` —
  result names
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:224-258` — map check note,
  result codes, `--skip-map-check`, `MAP_STALE` refresh
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:136` — `MAP_STALE`
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:43` — stale-map IGNORE
  rule
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md:113-117` — stale map
  docs audit item
- `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md:29-32` — map deferral
- `.agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md:30`, `:57`, `:90` —
  `iwe-map` as a next step
- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.py:36`
  — `NEXT_SKILLS`
- `.agents/plugins/agentdev/tests/test_iwe_bootstrap.py:171` — `NEXT_SKILLS`
  assertion
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:111`, `:233-245` —
  setup onboarding, update step 8
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:878`,
  `:898-901`, `:910-913`, `:1182-1184` — map onboarding, greenfield deferral,
  verification, update-mode note
- `.agents/plugins/agentdev/tests/test_template_consume_check_updates.py:330` —
  `iwe-map` fixture key
- `.github/workflows/validate-agent-files.yml:45-52` — map-source paths filter
- `.github/workflows/validate-agent-files.yml:104-105` — staleness CI step
- `.iwe/config.toml:78-79`, `:101` — codebase schema binding and hub match
- `docs/knowledge/AGENTS.md:62-66`, `:103-104`, `:224` — refresh loop item,
  provenance clause, skill row
- `docs/knowledge/SCHEMA.md:33-41`, `:156-177` — map field examples, map section
- `docs/knowledge/STRUCTURE.md:25`, `:32`, `:94-107` — schema list, hub list,
  derived-truth paragraph
- `docs/knowledge/README.md:81` — `codebase.md codebase/` tree line
- `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/index.md:32`,
  `data/log.md:15` — scaffold hub mentions
- `README.md:304-311`, `.agents/plugins/agentdev/README.md:141`, `:147` — map
  descriptions and skill rows
- `docs/knowledge/data/architecture/agent-metadata-files.md:14-34`, `:140-158` —
  decision, consumers, references
- `docs/knowledge/data/architecture/template-boundary.md:76-78` — root `iwe-map`
  rules
- `docs/knowledge/data/architecture/pr-review-correctness-bar.md:54-55` — map
  review-ignore item
- `docs/knowledge/data/features/agentdev-iwe-workflow-skills.md:19`, `:33-39`,
  `:62-63` — source, skill list and Map lane, Setup edge case
- `docs/knowledge/data/features/consumer-iwe-seed.md:44-48` — onboarding names
  `iwe-map`
- `docs/knowledge/data/features/native-stacked-prs.md:68-69` — map check edge
  case
- `docs/knowledge/data/backlog/remove-agentdev-session-start-hook.md:36-46` —
  map refresh steps and pin sweep
- `docs/knowledge/data/backlog/resilient-task-evidence.md:53-55` —
  `source_digest` alternative
- `docs/knowledge/data/spec/iwe-workflow-skills.md:654`, `:694`, `:728`, `:792`
  — the four removed requirements
- `docs/knowledge/data/spec/iwe-bootstrap.md:66-77` — onboarding separation
- `docs/knowledge/data/spec/template-consumption.md:322-352` — fresh adoption
- `.iwe/schemas/task.yaml:11-13` — task `stage` enum
- `docs/knowledge/SCHEMA.md:46-55`, `:146` — `stage` versus `status` table, task
  stage comment
- `docs/knowledge/AGENTS.md:63-64`, `:97` — task-finished loop item, backlog
  stage vocabulary
- `docs/knowledge/data/backlog.md:49`, `:63` — stamper link, `## Done`
