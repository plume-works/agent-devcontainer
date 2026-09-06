---
type: plan
created: 2026-09-05
description: Maintain a reusable IWE seed in this repository and initialize consumer project memory through setup and mapping without overwriting existing knowledge.
generated:
  by: codex/gpt-6
  at: 2026-09-05T17:30:00Z
sources:
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: .agents/plugins/agentdev/skills/iwe-setup/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-map/SKILL.md
---

# Repository-owned IWE seed for consumers

## Context

Consumers choosing IWE need a complete starting workspace: reusable schemas,
document hubs, product placeholders, onboarding tasks, and examples. This
repository's live `docs/knowledge/data/` describes the publisher. Removing it
leaves consumers without that starting structure, while retaining it gives them
another project's memory. The consumption guide makes IWE optional but does not
initialize consumer data or invoke onboarding.

This repository will own a clean seed and maintain it alongside its schemas and
skills. The data tree from `plume-works/iwe-dev-workspace` supplies the initial
content; subsequent maintenance and consumer setup must remain independent of
that fork. Template consumption will install the seed and run iwe-setup followed
by iwe-map to populate the consumer's own project memory. This extends the
existing [template consumption contract](../spec/template-consumption.md).

## Approach

Keep the canonical seed in `templates/iwe/data/`, outside the live IWE library.
Import the upstream data tree once, preserve its license notice, and maintain it
alongside this repository's schemas and skills. Retain placeholders, onboarding
tasks, hubs, and fictional examples; adapt example metadata and guidance to the
current `source_digest` contract without claiming that fictional source was
verified against this repository.

The installed consumption skill reads the seed from the agent-devcontainer
checkout at the ref being adopted, just as it reads other template files. There
is no second seed copy inside the plugin and no fetch from the old fork. For a
fresh knowledge base, install the reusable IWE configuration and supporting
documents, seed consumer data, then invoke iwe-setup followed by iwe-map.
Existing knowledge is consumer-owned and must be preserved. Updates compare
explicit reusable paths, never the publisher's data or the seed against live
consumer memory.

## Implementation Steps

### Task 1: Maintain a standalone seed

**Files:** Create: `templates/iwe/data/**`, `templates/iwe/README.md`,
`templates/iwe/LICENSE.md`. Modify: `.prettierignore`.

- [x] Import the data tree from the initial source at commit
  `249943bcc30ac1016469d5ee89a16ce454cc882f`, retaining the MIT notice. Commit
  the complete seed so no future consumer needs the import checkout.
  - **Evidence:** commit `19baf92` checks in all 34 seed documents plus the
    upstream MIT `LICENSE.md` verbatim, so the seed resolves from this
    repository alone.
- [x] Adapt the seed to current schemas, including fictional map examples and
  digest terminology; retain the onboarding keys iwe-setup closes and remove
  publisher-specific content. Document local ownership, seed purpose, and
  maintenance against the shared schemas.
  - **Evidence:** commit `27af41b` — the four `data/codebase/*.example.md` docs
    carry `source_digest` instead of `commit`, the hub and index describe the
    digest, the two onboarding tasks point at `/agentdev:iwe-setup` and
    `/agentdev:iwe-plan` instead of `.claude/skills/` paths, and
    `templates/iwe/README.md` records ownership and schema-coupled maintenance.
    `iwe schema validate` exits 0 against the consumer fixture built from the
    repo's own `.iwe/`.
- [x] Exclude seed Markdown from Prettier and normalize it through an isolated
  consumer fixture, keeping it outside the publisher's active graph.
  - **Evidence:** `.prettierignore` gained `templates/iwe/**` in commit
    `19baf92`, and the pre-commit `prettier` hook has passed on every commit
    since. `docs/knowledge/tests/test_iwe_seed.py` normalizes the seed in a
    throwaway `.tmp/` consumer workspace and asserts the checked-in bytes match;
    `test_seed_is_not_a_member_of_the_publisher_graph` asserts root-level `iwe`
    never lists a `templates/` key.
    `uv run pytest docs/knowledge/tests/test_iwe_seed.py` — 8 passed.

### Task 2: Initialize consumer knowledge through both adoption workflows

**Files:** Modify: `.agents/plugins/agentdev/skills/template-consume/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`.

- [x] Add a shared knowledge-base adoption procedure used by Workflow A and B.
  Copy the seed from the selected agent-devcontainer ref to
  `docs/knowledge/data/`, retain root `.iwe/` with library path
  `docs/knowledge`, and enumerate reusable supporting files, validation hooks,
  and workflow requirements. Preserve the seed's license notice in consumers.
  - **Evidence:** commit `b990f17` adds `## Optional knowledge-base setup` to
    the consumption guide, reached from Workflow A step 9 and Workflow B step 5
    and from the knowledge-base validation subsection. It lists the reusable
    scaffold (root `.iwe/` with `[library].path = "docs/knowledge"`, the
    supporting docs, `test_plan_checkboxes.py`), the retained validation
    (workflow, both pre-commit hooks, the `testpaths` entry), and copies
    `templates/iwe/LICENSE.md` to `docs/knowledge/LICENSE.md`.
- [x] In Workflow A, replace only the identified unmodified publisher data
  copied from that ref; if data differs, treat it as existing consumer memory.
  In Workflow B, seed only an absent or empty data directory. Ask how to merge
  any existing knowledge/configuration collision without deleting or replacing
  it. Keep the publisher checkout unchanged when targeting another directory.
  - **Evidence:** commit `b990f17`, the guide's `### Seed the consumer's data`.
    Step 1 makes Workflow A compare the copied data against the adopted ref's
    and seed only on a byte-identical match, and makes Workflow B seed only an
    absent or empty directory. Step 2 forbids deleting, overwriting, or
    resetting existing data and requires asking how to reconcile it — including
    a root `.iwe/` whose schemas or `[library].path` differ. The closing
    paragraph keeps the publisher's `docs/knowledge/` and `templates/iwe/`
    unmodified when the skill runs against another target directory.
- [x] Invoke iwe-setup and then iwe-map for fresh onboarding, preserving their
  interviews and confirmation gates. Use the consumer root for IWE commands. For
  greenfield projects, complete setup and report mapping as deferred until code
  exists. For interrupted onboarding, resume from consumer state rather than
  recopying the seed; do not claim completion while required input is pending.
  - **Evidence:** commit `b990f17`, the guide's
    `### Onboard the consumer's project memory`, plus step 4 of `## Setup Mode`
    in `SKILL.md`. Both invoke `/agentdev:iwe-setup` then `/agentdev:iwe-map`
    from the consumer root, state that the skills own their interviews and
    gates, defer mapping for a greenfield consumer, and require reporting
    onboarding as pending — resuming from the consumer's current data rather
    than recopying the seed — while any input is outstanding.
- [ ] When IWE is declined, skip seeding and onboarding and prune copied
  publisher knowledge, seed-source files, and IWE-only validation as
  appropriate; preserve any pre-existing consumer knowledge. Normal consumers
  need not retain `templates/iwe/` after the seed has been copied.

### Task 3: Protect consumer memory during template updates

**Files:** Modify: `.agents/plugins/agentdev/skills/template-consume/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`docs/knowledge/data/architecture/template-boundary.md`.

- [ ] Replace broad `docs/knowledge/` tracking with an explicit inventory of
  reusable support files/directories and `.iwe/`; exclude `docs/knowledge/data/`
  and the initialization-only seed. Document ownership and the seed's
  source-to-destination mapping in the template boundary.
- [ ] Before invoking check-updates.sh, migrate legacy markers that broadly
  track knowledge to that retained support inventory without advancing
  `consumed_ref`. Preserve unrelated tracked paths and optional bundle choices.
  Update mode must never reseed or automatically rerun onboarding; review
  schema/support-file changes against existing consumer data before applying.

### Task 4: Validate the seed as a consumer workspace

**Files:** Create: `docs/knowledge/tests/test_iwe_seed.py`. Modify:
`.github/workflows/validate-knowledge-base.yml`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`.

- [ ] Add focused fixture tests that assemble `.iwe/`, reusable support files,
  and the seed at the consumer layout under repo-root `.tmp/`, run schema
  validation and normalization, and check links and onboarding keys. Require the
  checked-in seed to match normalized output and remain separate from live
  publisher data. Keep these seed-source tests publisher-only during adoption.
- [ ] Make the knowledge validation workflow run the seed tests when seed,
  schema, or relevant support files change, without expanding to the full suite.
- [ ] Exercise the guide on disposable Workflow A, Workflow B, existing-memory,
  interrupted-onboarding, IWE-declined, greenfield, and legacy-marker fixtures.
  Check file preservation by comparing before/after bytes and review the skill
  handoff order and pending-input behavior; record results when executed.

## Spec changes

Extend [Template consumption](../spec/template-consumption.md):

``` markdown
## ADDED Requirements

### Requirement: the repository owns a complete reusable IWE seed

The repository SHALL maintain a clean seed in `templates/iwe/data/`, compatible
with its IWE schemas and onboarding skills and separate from publisher memory.
Consumption SHALL use the seed at the adopted agent-devcontainer ref and SHALL
NOT depend on the initial import repository remaining available.

#### Scenario: the initial source is unavailable

- **WHEN** a consumer adopts IWE after the initial import repository disappears
- **THEN** all seed content is available from agent-devcontainer and adoption
  makes no request to the initial import repository

### Requirement: fresh IWE adoption initializes consumer memory

For both adoption workflows, choosing IWE SHALL install its reusable scaffold
and seed, invoke iwe-setup followed by iwe-map, and validate the resulting
consumer workspace. The invoked skills' confirmation gates SHALL remain in
force. Mapping SHALL be explicitly deferred for a project with no code.

#### Scenario: fresh full-copy adoption

- **WHEN** Workflow A retains IWE and data is the unmodified publisher copy
- **THEN** adoption replaces that data with the seed and onboards the consumer

#### Scenario: adoption into an existing repository without knowledge

- **WHEN** Workflow B retains IWE and its data directory is absent or empty
- **THEN** adoption installs the seed and runs setup before mapping

#### Scenario: a greenfield consumer

- **WHEN** an adopting project has no code to map
- **THEN** setup establishes product memory and the report explicitly defers mapping

#### Scenario: required onboarding input is pending

- **WHEN** setup or map requires an unanswered question or confirmation
- **THEN** adoption reports pending work, preserves current data, and does not
  declare onboarding complete or reset it on resumption

### Requirement: consumer knowledge survives adoption and updates

Adoption SHALL preserve pre-existing consumer knowledge and resolve collisions
with the user. Updates SHALL exclude publisher data and initialization seeds
from consumer-memory changes, narrow legacy broad knowledge tracking before
checking updates, and preserve the consumed ref until updates are applied.
Schema changes SHALL be reviewed against existing consumer data.

#### Scenario: knowledge already exists

- **WHEN** adoption encounters consumer-authored data, including a modified
  publisher copy or partially completed onboarding
- **THEN** it preserves that data and resolves collisions without reseeding

#### Scenario: an older marker tracks the entire knowledge directory

- **WHEN** update mode encounters broad knowledge tracking
- **THEN** it narrows tracking to retained reusable support paths before diffing,
  preserving unrelated paths and the consumed ref

#### Scenario: publisher memory or seed content changes

- **WHEN** updates change publisher data or the seed
- **THEN** those changes are not applied to consumer memory and onboarding is not rerun

#### Scenario: IWE is declined

- **WHEN** the consumer declines IWE adoption
- **THEN** setup skips seeding and onboarding, removes copied IWE-only artifacts,
  and preserves pre-existing consumer knowledge
```

## Depends on

[Add the iwe-map skill](20260903-iwe-map-skill.md) must ship first: this plan's
onboarding flow invokes that skill and uses its digest-based schema.

## Verification

- Run `uv run pytest docs/knowledge/tests/test_iwe_seed.py` for the isolated
  seed checks, including compatibility before examples are deleted.
- Run `iwe normalize` and `iwe schema validate` from the repository root for the
  publisher graph. Check that seed edits do not add publisher graph members.
- Walk the Task 4 adoption fixtures using only agent-devcontainer as the
  template source. Confirm consumer commands resolve `data/*` under
  `docs/knowledge`, examples disappear after completed setup, and mapping uses
  the consumer's source rather than the publisher or template tree.
- For initialized brownfield fixtures, run the installed iwe-map
  `stale-map-docs.sh` from the consumer root and require `RESULT=SUCCESS`.
- Verify legacy marker narrowing happens before the update helper and that
  publisher-data-only changes produce no consumer memory changes.

## Out of scope

- Implementing or changing the product of a consuming repository.
- Synchronizing with or maintaining the old fork.
- Resetting an existing consumer knowledge base or automatically migrating its
  content.
- Changing iwe-setup or iwe-map's standalone contracts or bypassing their
  approvals.
- Replacing this repository's live project memory with the seed.

## Key references

Verified anchor points (line numbers as of 2026-09-05):

- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:55` — setup mode.
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:90` — update mode.
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:168` — broad
  knowledge tracking.
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:335`
  — knowledge validation adoption.
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:505`
  — Workflow B.
- `.agents/plugins/agentdev/skills/template-consume/scripts/check-updates.sh:166`
  — tracked-path diff loop.
- `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md:13` — onboarding steps.
- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:22` — initial mapping and
  confirmation.
- `.iwe/config.toml:17` — consumer library path.
- `.iwe/schemas/codebase.yaml:11` — required source_digest metadata.
