---
type: plan
created: 2026-10-23
release:
- features/consumer-iwe-seed
description: Extract a self-contained IWE bootstrap skill and make full template adoption reuse it without overwriting consumer knowledge.
generated:
  by: claude-code/opus-5
  at: 2026-10-25T06:17:32Z
sources:
- resource: docs/knowledge/data/features/consumer-iwe-seed.md
- resource: docs/knowledge/data/spec/template-consumption.md
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: .agents/plugins/agentdev/skills/iwe-setup/SKILL.md
- resource: docs/knowledge/tests/test_iwe_seed.py
---

# Extract a reusable IWE bootstrap skill

## Context

[Consumer IWE seed](../features/consumer-iwe-seed.md) currently initializes
project memory only as an optional phase of full
[`template-consume`](../spec/template-consumption.md) adoption. The seed lives
under `templates/iwe/`, outside the installed agentdev catalog, so an agent
working from a persistent agentdev runtime cannot initialize an unrelated
mounted repository without also locating an agent-devcontainer source checkout.

The reusable operation must work directly from the installed catalog and must
also remain the one initializer used by full adoption. `template-consume` stays
supported: it keeps its workflow-specific decisions, CI integration, and
onboarding sequence, but delegates creation of the IWE workspace to the new
skill. This plan is independent of the reusable Dev Container image plan; either
can ship first.

## Approach

Move the canonical blank workspace into assets owned by a new
`/agentdev:iwe-bootstrap` skill as the sole source any initialization copies
from. The scaffold's schemas, configuration, and knowledge instructions are the
same bytes this repository's own workspace uses; a publisher-side test keeps the
two identical and every asset tracked, so a schema change is a scaffold change.
Give the skill a deterministic helper that preflights a repository root,
installs the complete `.iwe/` and `docs/knowledge/` scaffold only when its
destinations are absent, validates the result, and reports stable result codes.
A complete valid workspace is an idempotent success. Any partial or conflicting
workspace is a non-destructive stop that identifies the paths requiring
reconciliation.

Keep product discovery and code mapping out of bootstrap. A direct user may
invoke `iwe-setup` and `iwe-map` afterwards; `template-consume` continues to
invoke them in that order when IWE is selected. Workflow A retains the special
proof that copied publisher memory is byte-identical before removing it, then
calls the same bootstrap skill. Updates never invoke bootstrap or apply seed
changes to consumer memory.

Repository CI and pre-commit integration remain template-adoption concerns.
Bootstrap establishes a locally valid knowledge base without merging unrelated
repository configuration.

The scaffold's Markdown uses IWE's extension-less links, which resolve only once
installed, so `validate_agent_files` stops scanning the `assets/` directory
beside a `SKILL.md` for references — in the Agent Skills layout that directory
holds output templates, not documents read in place. No `data/spec/` document
governs that scan; the validators codebase map documents it. The plugin-test CI
job installs the pinned `iwe` so the bootstrap tests run rather than skip.

## Implementation Steps

### Task 1: Specify bootstrap outcomes with failing tests

**Files:** Create: `.agents/plugins/agentdev/tests/test_iwe_bootstrap.py`;
Modify: `.agents/plugins/agentdev/tests/conftest.py`

- [x] Add installed-plugin fixtures that invoke the bootstrap helper against an
  unrelated repository root, with no access to `templates/iwe/` or other
  publisher paths.
  - **Evidence:** `.agents/plugins/agentdev/tests/conftest.py` gains
    `installed_iwe_bootstrap` (copies only `bin/` and `skills/iwe-bootstrap/`
    into a scratch plugin layout) and `unrelated_repository` (a fresh git
    repository); committed with `test_iwe_bootstrap.py`, which runs the helper
    only from that copy.
- [x] Define fresh-install, already-valid, partial-scaffold, conflicting-config,
  non-directory collision, and interrupted-install outcomes. Assert that every
  refusal leaves pre-existing bytes unchanged and that a repeated successful run
  makes no filesystem changes.
  - **Evidence:** `test_iwe_bootstrap.py` pins each outcome's exit code and
    `RESULT` pair, compares full path, byte, and mtime snapshots for every
    refusal and repeat, and interrupts both the staging and commit phases with
    `SIGTERM`;
    `uv run pytest .agents/plugins/agentdev/tests/test_iwe_bootstrap.py` fails
    in fixture setup until the skill exists.
- [x] Assert that success installs a normalized, schema-valid graph with the
  onboarding keys, product placeholders, nested knowledge instructions, and MIT
  notice required by `iwe-setup`.
  - **Evidence:** `test_installed_graph_is_normalized_and_schema_valid` and
    `test_installed_graph_carries_what_iwe_setup_needs` in
    `test_iwe_bootstrap.py`, committed with the fixtures above.

### Task 2: Relocate the canonical scaffold into the skill

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/.iwe/**`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/**`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md`; Modify:
`.prettierignore`, `docs/knowledge/tests/test_iwe_seed.py`,
`.github/workflows/validate-knowledge-base.yml`,
`.github/workflows/validate-agent-files.yml`,
`py_packages/validate_agent_files/validate_agent_files/validators/bundled_markdown.py`,
`py_packages/validate_agent_files/tests/test_bundled_markdown_containment.py`;
Delete: `templates/iwe/**`

- [x] Move the seed, schemas, configuration, knowledge instructions, and license
  into one skill-owned asset tree. Preserve normalized bytes, import
  attribution, onboarding keys, and separation from this repository's live IWE
  graph.
  - **Evidence:** the commit that closes this task `git mv`s
    `templates/iwe/data` and `LICENSE.md` under
    `skills/iwe-bootstrap/assets/docs/knowledge/`, copies the tracked `.iwe/`
    files and the knowledge instructions beside them, and moves the seed
    README's ownership, import attribution, and maintenance rules into
    `skills/iwe-bootstrap/references/scaffold.md`;
    `uv run pytest docs/knowledge/tests/test_iwe_seed.py` passes 11 tests,
    including the normalize no-op and publisher-graph separation checks.
- [x] Retarget seed validation to the installed-plugin asset tree and prove the
  packaged scaffold is complete without reconstructing it from publisher-root
  files.
  - **Evidence:** `test_iwe_seed.py` builds its consumer workspace by copying
    `assets/` alone, adds `test_scaffold_is_complete` (a schema file for every
    `[schemas.*]` binding plus every knowledge file) and
    `test_scaffold_support_files_match_the_publisher_workspace`, and the
    knowledge-base workflow's seed filter now watches the asset tree and the
    shared `docs/knowledge/` files; 11 passed.
- [x] Keep IWE-owned Markdown out of Prettier and ensure catalog packaging and
  validation retain nested asset files unchanged.
  - **Evidence:** `.prettierignore` swaps `templates/iwe/**` for the asset tree;
    `test_every_scaffold_file_is_tracked` fails on any ignored asset;
    `validate_agent_files`'s bundled-markdown scan skips the `assets/` directory
    beside a `SKILL.md` (user-directed, since the scaffold's extension-less IWE
    links resolve only once installed), pinned by two new tests in
    `test_bundled_markdown_containment.py`, whose suite passes 169 tests under
    `uv run --isolated --extra dev pytest`.

### Task 3: Implement the reusable bootstrap skill

**Files:** Create: `.agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.sh`;
Modify: `.agents/plugins/agentdev/README.md`,
`.github/workflows/validate-agent-files.yml`

- [x] Define a skill that resolves the explicit or current repository root, runs
  its helper, explains each named outcome, and stops after a validated scaffold
  is present. It must not answer onboarding questions, run `iwe-setup`, run
  `iwe-map`, or edit repository CI.
  - **Evidence:** `skills/iwe-bootstrap/SKILL.md` resolves `--root` or the
    current repository, tables every `RESULT` and `CONFLICT` reason, and reports
    `NEXT_SKILLS` without running them;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reports 64/64 valid.
- [x] Implement preflight and copy as a fail-closed operation using
  skill-relative assets. Reject partial and conflicting destinations before
  copying, make helper-created transaction state recognizable and safely
  recoverable after interruption, and never delete or overwrite consumer-owned
  paths.
  - **Evidence:** `agent-code/bootstrap-iwe.sh` classifies the root before
    writing, stages and validates in an `OWNER`-marked `.iwe-bootstrap.txn/`,
    and discards or completes it by recorded phase;
    `uv run pytest .agents/plugins/agentdev/tests/test_iwe_bootstrap.py` passes
    25 tests with iwe 0.29.0 and the pinned 0.29.1, and `shellcheck -x` is
    clean.
- [x] Use the shared skill-script result contract so shell callers and agents
  can distinguish created, already initialized, reconciliation required, missing
  dependency, validation failure, and interruption outcomes.
  - **Evidence:** the helper sources `bin/result-codes.sh` and declares
    `MISSING_DEPENDENCY` 3, `ALREADY_INITIALIZED` 4, `RECONCILIATION_REQUIRED`
    5, and `VALIDATION_FAILED` 6, each pinned with `SUCCESS`, `PREFLIGHT_ERROR`,
    and `SIGNAL_TERM` in `test_iwe_bootstrap.py`; the validate-agent-files
    workflow now installs the pinned iwe so those tests run in CI.

### Task 4: Make full adoption compose the bootstrap skill

**Files:** Modify: `.agents/plugins/agentdev/skills/template-consume/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [x] Replace Workflow B's manual seed-copy procedure with
  `/agentdev:iwe-bootstrap`, then retain the existing `iwe-setup` and `iwe-map`
  handoffs and their confirmation gates.
  - **Evidence:** the guide's `### Initialize the consumer's knowledge` step 3
    invokes `/agentdev:iwe-bootstrap` and branches on its `RESULT`, Workflow B
    step 5 defers to it, and `### Onboard the consumer's project memory` keeps
    setup before map with its gates; `template-consume/SKILL.md` step 5 names
    the same order.
- [x] In Workflow A, keep the byte-identical publisher-memory check. Remove only
  a proven untouched publisher copy, invoke bootstrap against the consumer, and
  preserve any differing or partial knowledge for explicit reconciliation.
  - **Evidence:** step 1 of `### Initialize the consumer's knowledge` compares
    the copied `.iwe/` and `docs/knowledge/` (tests aside) with the adopted ref,
    removes them only when byte-identical, and sends any difference to the step
    2 reconciliation question without bootstrapping.
- [x] Remove the source-checkout dependency from knowledge initialization and
  its tracked-path rules. Keep update mode non-initializing: it must neither
  invoke bootstrap nor merge changed scaffold assets into consumer memory.
  - **Evidence:** neither `template-consume` file mentions `templates/iwe/`
    except the legacy-marker drop in update step 3; `### Reusable scaffold` says
    bootstrap installs the support files from the catalog, the Default Template
    Surface keeps the scaffold out of `tracked_paths`, and update step 8 plus
    the guide's update section forbid invoking bootstrap or applying scaffold
    changes; `validate_agent_files` reports 64/64 and prettier is clean.

### Task 5: Align the feature and boundary documents

**Files:** Modify: `docs/knowledge/data/features/consumer-iwe-seed.md`,
`docs/knowledge/data/architecture/template-boundary.md`

Spec documents are not edited here: Ship merges `## Spec changes` into
`data/spec/template-consumption` and creates `data/spec/iwe-bootstrap`.

- [x] Update the template boundary inventories so `template-consume` reuses the
  installed skill, the scaffold is catalog-owned rather than a template path,
  and consumer knowledge remains consumer-owned after initialization.
  - **Evidence:** `data/architecture/template-boundary` replaces the
    `templates/iwe/` source table with the `iwe-bootstrap` scaffold's
    destinations and owners, states that the scaffold is never a `tracked_paths`
    entry, drops `LICENSE.md` from the tracked knowledge paths, and removes the
    `templates/iwe/` publisher-only row; `iwe schema validate` passes.
- [x] Refresh the feature from repository-owned seed terminology to a reusable
  catalog-owned bootstrap while preserving full adoption as a supported path.
  - **Evidence:** `data/features/consumer-iwe-seed` (key kept, H1 now "Reusable
    IWE bootstrap") describes the catalog-owned scaffold, direct bootstrap and
    its refusal outcomes, and full adoption composing bootstrap before setup and
    map; `iwe normalize` and `iwe schema validate` pass.

### Task 6: Refresh the codebase map

**Files:** Modify: the `docs/knowledge/data/codebase/` documents
`stale-map-docs.py` reports stale or gone, and `docs/knowledge/data/codebase.md`

- [x] Run `/agentdev:iwe-map` refresh mode over every stale document, retire or
  retarget the `templates/iwe` component to the `iwe-bootstrap` skill's
  scaffold, and leave `stale-map-docs.py` reporting `RESULT=SUCCESS`.
  - **Evidence:** `iwe rename` moved `data/codebase/templates/iwe` to
    `data/codebase/agents/plugins/agentdev/skills/iwe-bootstrap`, rewritten from
    the skill and linked under Catalog skills' `## Contains`; the ten other
    stale docs were re-read and re-stamped, and `stale-map-docs.py` reports
    `RESULT=SUCCESS` for all 28 docs.

## Spec changes

### [IWE bootstrap](../spec/iwe-bootstrap.md)

``` markdown
## ADDED Requirements

### Requirement: bootstrap is self-contained in the installed catalog

The `iwe-bootstrap` skill SHALL install a complete blank IWE workspace into an
explicit repository root using only assets shipped with that installed skill.
It SHALL NOT require an agent-devcontainer source checkout or a network fetch.

#### Scenario: a mounted repository has no IWE workspace

- **WHEN** bootstrap runs against a repository whose managed destinations are
  absent
- **THEN** it installs `.iwe/` and `docs/knowledge/`, including the schemas,
  blank graph, knowledge instructions, and license
- **AND** `iwe normalize` is a no-op and `iwe schema validate` succeeds from the
  repository root

### Requirement: bootstrap never overwrites project knowledge

Bootstrap SHALL classify the target before writing. A complete valid workspace
SHALL be an idempotent success; any partial, incompatible, or colliding managed
destination SHALL stop with the conflicting paths and SHALL preserve every
pre-existing byte.

#### Scenario: bootstrap is repeated

- **WHEN** the installed scaffold is already present and schema-valid
- **THEN** bootstrap reports that initialization is already complete and makes
  no filesystem changes

#### Scenario: project knowledge or configuration already exists

- **WHEN** any managed destination exists but does not constitute the complete
  valid scaffold
- **THEN** bootstrap reports that reconciliation is required
- **AND** it neither deletes, replaces, nor merges the existing content

#### Scenario: installation is interrupted

- **WHEN** bootstrap is interrupted while preparing a fresh workspace
- **THEN** every pre-existing path remains unchanged and any incomplete state is
  identifiable as owned by that bootstrap transaction
- **AND** a later invocation can safely remove or complete only that owned state

### Requirement: bootstrap and onboarding are separate operations

Bootstrap SHALL stop after the blank workspace validates. It SHALL NOT run
`iwe-setup`, run `iwe-map`, answer their confirmation gates, or merge repository
CI and pre-commit configuration.

#### Scenario: direct initialization succeeds

- **WHEN** bootstrap creates a workspace for a mounted repository
- **THEN** it reports `iwe-setup` as the next product-onboarding operation and
  `iwe-map` as the subsequent codebase-mapping operation
```

### [Template consumption](../spec/template-consumption.md)

``` markdown
## REMOVED Requirements

### Requirement: the repository owns a complete reusable IWE seed

**Reason:** The canonical scaffold moves into the installed skill so direct and
full adoption use one source.

## ADDED Requirements

### Requirement: the installed catalog owns a complete reusable IWE scaffold

The installed agentdev catalog SHALL carry one complete IWE scaffold compatible
with its schemas and onboarding skills and separate from publisher memory.
Template consumption SHALL initialize knowledge by invoking
`/agentdev:iwe-bootstrap` and SHALL NOT maintain or copy a second seed source.

#### Scenario: agent-devcontainer source is unavailable

- **WHEN** a consumer adopts IWE through an installed agentdev catalog without
  an agent-devcontainer source checkout
- **THEN** all scaffold content is available from the installed skill and
  adoption makes no request to another repository

## MODIFIED Requirements

### Requirement: fresh IWE adoption initializes consumer memory

For both adoption workflows, choosing IWE SHALL invoke `iwe-bootstrap`, then
invoke `iwe-setup` followed by `iwe-map`, and validate the resulting consumer
workspace. The invoked skills' confirmation gates SHALL remain in force.
Mapping SHALL be explicitly deferred for a project with no code.

#### Scenario: fresh full-copy adoption

- **WHEN** Workflow A retains IWE and data is proven to be the unmodified
  publisher copy
- **THEN** adoption removes that publisher copy, invokes bootstrap, and
  onboards the consumer

#### Scenario: adoption into an existing repository without knowledge

- **WHEN** Workflow B retains IWE and the bootstrap-managed destinations are
  absent
- **THEN** adoption invokes bootstrap and runs setup before mapping

#### Scenario: a greenfield consumer

- **WHEN** an adopting project has no code to map
- **THEN** setup establishes product memory and the report explicitly defers
  mapping

#### Scenario: required onboarding input is pending

- **WHEN** setup or map requires an unanswered question or confirmation
- **THEN** adoption reports pending work, preserves current data, and does not
  declare onboarding complete or reset it on resumption

### Requirement: consumer knowledge survives adoption and updates

Adoption SHALL preserve pre-existing consumer knowledge, send partial or
incompatible bootstrap destinations to explicit reconciliation, and resolve
collisions with the user. Updates SHALL never invoke bootstrap, SHALL exclude
publisher data and bootstrap scaffold changes from consumer-memory changes,
SHALL narrow legacy broad knowledge tracking before checking updates, and SHALL
preserve the consumed ref until selected updates are applied. Schema changes
SHALL be reviewed against existing consumer data.

#### Scenario: knowledge already exists

- **WHEN** adoption encounters consumer-authored data, including a modified
  publisher copy or partially completed onboarding
- **THEN** it preserves that data and resolves collisions without bootstrapping

#### Scenario: an older marker tracks the entire knowledge directory

- **WHEN** update mode encounters broad knowledge tracking
- **THEN** it narrows tracking to retained reusable support paths before
  diffing, preserving unrelated paths and the consumed ref

#### Scenario: publisher memory or the bundled scaffold changes

- **WHEN** an update changes the publisher's `docs/knowledge/data/` or an
  agentdev update changes bootstrap assets
- **THEN** template update mode does not apply those changes to consumer memory,
  does not invoke bootstrap, and does not rerun onboarding

#### Scenario: IWE is declined

- **WHEN** the consumer declines IWE adoption
- **THEN** setup skips bootstrap and onboarding, removes copied IWE-only
  artifacts, and preserves pre-existing consumer knowledge
```

## Verification

- Run `uv run pytest .agents/plugins/agentdev/tests/test_iwe_bootstrap.py`.
- Run `uv run pytest docs/knowledge/tests/test_iwe_seed.py`.
- Run `uv run --isolated --extra dev pytest` from
  `py_packages/validate_agent_files`, confirming a skill's `assets/` is not
  scanned while an `assets/` directory outside a skill still is.
- Run the agent-file validator against the canonical plugin and an installed
  catalog copy, confirming the skill assets survive installation unchanged.
- In a repository fixture outside the publisher tree, run bootstrap twice;
  verify the first run creates a schema-valid workspace and the second produces
  an empty diff.
- Exercise partial `.iwe/`, partial `docs/knowledge/`, incompatible workspace
  path, file-versus-directory collision, and interrupted transaction fixtures;
  verify each preserves all pre-existing bytes.
- Exercise both template-consumption workflows with IWE selected and verify they
  invoke bootstrap before setup/map; exercise update mode and verify it never
  invokes bootstrap.
- Run `iwe normalize` and `iwe schema validate` from the repository root.
- Run `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py` and
  confirm `RESULT=SUCCESS`.

## Verification results

All `## Verification` checks pass on the branch head with iwe 0.29.0, and the
bootstrap and scaffold suites also pass with the pinned 0.29.1.

- `test_iwe_bootstrap.py` 25 passed; `test_iwe_seed.py` 11 passed; the validator
  package's isolated suite 169 passed; the whole plugin suite 217 passed, 1
  skipped.
- `validate_agent_files --recommend . --require-marketplace claude codex`
  reports 64/64 valid both in the checkout and in a `git archive` export of the
  marketplace plugins, whose `iwe-bootstrap/assets/` is byte-identical to the
  checkout's.
- Run from that export against a fresh repository outside the publisher tree,
  bootstrap reported `SUCCESS`, `iwe schema validate` passed, and a second run
  reported `ALREADY_INITIALIZED` with every file's hash unchanged.
- The partial, incompatible, collision, foreign-transaction, and interrupted
  staging and commit cases are the parametrized refusal and interruption tests
  above.
- Both workflows reach `/agentdev:iwe-bootstrap` before setup and map — Workflow
  A through guide step 1's identical-copy removal, Workflow B through its step 5
  — and the only bootstrap mention in update mode is step 8's prohibition.
- `iwe normalize` and `iwe schema validate` are clean, and `stale-map-docs.py`
  reports `RESULT=SUCCESS`.

## Out of scope

- Changing `iwe-setup` interviews or `iwe-map` behavior.
- Automatically onboarding a project or generating its codebase map from the
  bootstrap skill.
- Installing or merging knowledge-base CI workflows, pre-commit hooks, or root
  project configuration outside full `template-consume` adoption.
- Migrating or upgrading an existing consumer knowledge base to new schemas.
- Retiring `template-consume` or either of its full-adoption workflows.
- Depending on, or changing, the reusable agentdev Dev Container image plan.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.sh:142`
  — `transaction_phase`, recognition of helper-owned transaction state
- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.sh:219`
  — `required_files`, the structural files a complete workspace keeps
- `.agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md:26` —
  scaffold ownership and import attribution
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:107` —
  full-adoption bootstrap and onboarding handoff
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:772`
  — retained knowledge paths after bootstrap
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:826`
  — knowledge initialization through bootstrap
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:864`
  — setup-then-map onboarding sequence
- `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md:9` — setup's assumption
  that a blank workspace already exists
- `docs/knowledge/tests/test_iwe_seed.py:28` — `SCAFFOLD`, the packaged asset
  root the seed tests copy
- `docs/knowledge/tests/test_iwe_seed.py:110` —
  `test_scaffold_support_files_match_the_publisher_workspace`
- `py_packages/validate_agent_files/validate_agent_files/validators/bundled_markdown.py:29`
  — `SKILL_ASSETS_DIR`, the skill asset tree the reference scan skips
- `.github/workflows/validate-agent-files.yml:82` — pinned `iwe` install for the
  plugin tests
- `.iwe/config.toml:17` — root-relative IWE workspace path contract
- `docs/knowledge/data/spec/template-consumption.md:279` — current reusable seed
  requirement
- `docs/knowledge/data/spec/template-consumption.md:292` — current fresh IWE
  adoption requirement
- `docs/knowledge/data/spec/template-consumption.md:321` — current
  consumer-knowledge survival requirement, including the IWE-declined scenario
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:225` — update
  mode's bar on bootstrap and on publisher-data and scaffold changes
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:912`
  — declining IWE skips bootstrap and onboarding
