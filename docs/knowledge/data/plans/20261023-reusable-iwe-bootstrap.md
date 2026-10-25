---
type: plan
created: 2026-10-23
release:
- features/consumer-iwe-seed
description: Extract a self-contained IWE bootstrap skill and make full template adoption reuse it without overwriting consumer knowledge.
generated:
  by: codex/gpt-5
  at: 2026-10-23T03:13:20Z
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
`/agentdev:iwe-bootstrap` skill as the sole scaffold source. Give the skill a
deterministic helper that preflights a repository root, installs the complete
`.iwe/` and `docs/knowledge/` scaffold only when its destinations are absent,
validates the result, and reports stable result codes. A complete valid
workspace is an idempotent success. Any partial or conflicting workspace is a
non-destructive stop that identifies the paths requiring reconciliation.

Keep product discovery and code mapping out of bootstrap. A direct user may
invoke `iwe-setup` and `iwe-map` afterwards; `template-consume` continues to
invoke them in that order when IWE is selected. Workflow A retains the special
proof that copied publisher memory is byte-identical before removing it, then
calls the same bootstrap skill. Updates never invoke bootstrap or apply seed
changes to consumer memory.

Repository CI and pre-commit integration remain template-adoption concerns.
Bootstrap establishes a locally valid knowledge base without merging unrelated
repository configuration.

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
Modify: `.agents/plugins/agentdev/README.md`

- [ ] Define a skill that resolves the explicit or current repository root, runs
  its helper, explains each named outcome, and stops after a validated scaffold
  is present. It must not answer onboarding questions, run `iwe-setup`, run
  `iwe-map`, or edit repository CI.
- [ ] Implement preflight and copy as a fail-closed operation using
  skill-relative assets. Reject partial and conflicting destinations before
  copying, make helper-created transaction state recognizable and safely
  recoverable after interruption, and never delete or overwrite consumer-owned
  paths.
- [ ] Use the shared skill-script result contract so shell callers and agents
  can distinguish created, already initialized, reconciliation required, missing
  dependency, validation failure, and interruption outcomes.

### Task 4: Make full adoption compose the bootstrap skill

**Files:** Modify: `.agents/plugins/agentdev/skills/template-consume/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] Replace Workflow B's manual seed-copy procedure with
  `/agentdev:iwe-bootstrap`, then retain the existing `iwe-setup` and `iwe-map`
  handoffs and their confirmation gates.
- [ ] In Workflow A, keep the byte-identical publisher-memory check. Remove only
  a proven untouched publisher copy, invoke bootstrap against the consumer, and
  preserve any differing or partial knowledge for explicit reconciliation.
- [ ] Remove the source-checkout dependency from knowledge initialization and
  its tracked-path rules. Keep update mode non-initializing: it must neither
  invoke bootstrap nor merge changed scaffold assets into consumer memory.

### Task 5: Align the feature contract and maintenance guidance

**Files:** Create: `docs/knowledge/data/spec/iwe-bootstrap.md`; Modify:
`docs/knowledge/data/features/consumer-iwe-seed.md`,
`docs/knowledge/data/spec/template-consumption.md`,
`docs/knowledge/data/architecture/template-boundary.md`,
`docs/knowledge/data/spec.md`

- [ ] Document the independently invokable bootstrap contract, filesystem
  ownership boundary, idempotent and conflict outcomes, and separation from
  onboarding, mapping, and CI adoption.
- [ ] Update full-adoption requirements and boundary inventories so
  `template-consume` reuses the installed skill while consumer knowledge remains
  consumer-owned after initialization.
- [ ] Refresh the feature from repository-owned seed terminology to a reusable
  catalog-owned bootstrap while preserving full adoption as a supported path.

## Spec changes

### `data/spec/iwe-bootstrap`

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

Adoption SHALL preserve pre-existing consumer knowledge and send partial or
incompatible bootstrap destinations to explicit reconciliation. Updates SHALL
never invoke bootstrap or apply scaffold changes to consumer memory, and SHALL
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

#### Scenario: the bundled scaffold changes

- **WHEN** an agentdev update changes bootstrap assets
- **THEN** template update mode does not apply those changes to consumer memory
  and does not rerun onboarding
```

## Verification

- Run `uv run pytest .agents/plugins/agentdev/tests/test_iwe_bootstrap.py`.
- Run `uv run pytest docs/knowledge/tests/test_iwe_seed.py`.
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

- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:107` — current
  full-adoption seed and onboarding handoff
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:824`
  — current source-checkout-dependent seeding procedure
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:859`
  — current setup-then-map onboarding sequence
- `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md:9` — setup's assumption
  that a blank workspace already exists
- `docs/knowledge/tests/test_iwe_seed.py:26` — publisher-root scaffold source
  constants
- `docs/knowledge/tests/test_iwe_seed.py:57` — isolated consumer workspace
  fixture
- `.iwe/config.toml:10` — root-relative IWE workspace path contract
- `templates/iwe/README.md:7` — current seed ownership and maintenance boundary
- `docs/knowledge/data/spec/template-consumption.md:279` — current reusable seed
  requirement
- `docs/knowledge/data/spec/template-consumption.md:292` — current fresh IWE
  adoption requirement
