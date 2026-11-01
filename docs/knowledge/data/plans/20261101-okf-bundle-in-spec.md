---
type: plan
created: 2026-11-01
release: internal
description: Restore the spec's OKF requirement — the graph stays an OKF v0.2 bundle and diverges only where OKF costs merges or upkeep — and block OKF's optional `status` with a pre-commit check.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T18:00:00Z
sources:
- resource: docs/knowledge/data/spec/iwe-workflow-skills.md
- resource: .pre-commit-config.yaml
- resource: .iwe/schemas/okf.yaml
---

# Keep the graph an OKF bundle in the spec

## Context

[Conflict-free knowledge layout](20261031-kb-conflict-free-layout.md) replaced
the [IWE workflow skills](../spec/iwe-workflow-skills.md) requirement "Workflow
improvements preserve the IWE and OKF model" with "Workflow improvements
preserve the IWE model". That recorded a divergence the maintainer did not
intend: the graph is not leaving OKF, it departs from OKF only where OKF costs
merges or upkeep. `data/index.md`, the `okf`, `okf-index`, and `okf-log`
schemas, and the OKF text in the workspace manuals are already restored; the
spec is the one place that still says otherwise.

The one divergence is OKF's optional `status`: `stage` is the lifecycle field,
so no document sets `status`. Nothing enforces that today — `okf.yaml` does not
declare `status` and accepts undeclared fields, and
`test_no_schema_declares_status` checks the schemas only. The maintainer chose a
small pre-commit check to block it.

No feature document claims an OKF stance, so no feature changes. Nothing a
workspace user or template consumer sees changes either: the restored bundle
ships with the conflict-free layout, and this plan aligns the spec and enforces
a rule the manuals already state, so `release` is `internal`.

## Approach

A pytest module reads the frontmatter of every document under
`docs/knowledge/data/` and under the bootstrap scaffold's `docs/knowledge/data/`
and fails, naming each document, when one carries a `status` key. A local
pre-commit hook runs it whenever a graph or scaffold document changes; the
pre-commit job is the CI gate, so CI enforces the same rule.

A schema-level rejection was the alternative. `okf.yaml` would need to forbid
one property while still accepting every other undeclared one, and the
maintainer asked for a pre-commit test instead.

## Implementation Steps

### Task 1: A check rejects `status` in any graph document

**Files:** Create: `docs/knowledge/tests/test_no_status_field.py`

- [x] A document under `docs/knowledge/data/` or the bootstrap scaffold's
  `docs/knowledge/data/` that carries `status` in its frontmatter fails the
  test, and the failure names that document
  - **Evidence:** commit 319d2820; `test_a_status_key_is_named` passed, and with
    `status: deprecated` added to `features/codex-full-access-config.md`
    `test_no_document_sets_status[workspace]` failed naming that file
- [x] The test passes on the current graph and scaffold
  - **Evidence:** commit 319d2820;
    `uv run pytest docs/knowledge/tests/test_no_status_field.py` passed (3
    tests)

### Task 2: Pre-commit runs the check

**Files:** Modify: `.pre-commit-config.yaml`

- [x] A local `no-status-field` hook runs `test_no_status_field.py` whenever a
  Markdown file under `docs/knowledge/data/` or the scaffold's
  `docs/knowledge/data/` is committed, and
  `pre-commit run no-status-field --all-files` passes
  - **Evidence:** commit 05de23a8; `pre-commit run no-status-field --all-files`
    passed, and `pre-commit run no-status-field --files` on
    `features/codex-full-access-config.md` with `status` added failed naming it

### Task 3: CI passes on the pull request

- [ ] The pre-commit and knowledge-base checks pass on the pull request for this
  branch

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — contract-heavy: the
requirement that names the graph's model changes, and a scenario set comes with
it.

``` markdown
## REMOVED Requirements

### Requirement: Workflow improvements preserve the IWE model

Replaced by "Workflow improvements preserve the IWE and OKF model": the graph
stays an OKF v0.2 bundle, and this wording recorded a divergence the workspace
did not make. The scenario "Unaffected skills are exercised", retired with the
earlier OKF requirement, stays retired: Setup and Weekly changed when hubs
became flat lists.

## ADDED Requirements

### Requirement: Workflow improvements preserve the IWE and OKF model

The strengthened skills SHALL continue to use IWE's single-plan-document
workflow, graph links, durable specs, existing stage conventions, provenance
requirements, and schema validation. Risk-scaled spec deltas SHALL remain
embedded planning content without introducing OpenSpec change bundles, stores,
separate delta files, archive moves, or a claimed programmatic delta application
engine. The graph SHALL remain a conformant OKF v0.2 bundle — `data/index.md`
lists the hubs, `data/log.md` stays date-grouped, and the `okf`, `okf-index`,
and `okf-log` schemas check every document — and SHALL diverge from OKF only
where OKF costs merges or upkeep. The one divergence SHALL be that no document
under `data/` sets OKF's optional `status`, because `stage` is the lifecycle
field; a pre-commit check SHALL reject a document that sets it.

#### Scenario: Updated skills write project memory

- **WHEN** an updated skill creates or meaningfully changes an IWE document
- **THEN** it follows the existing OKF metadata, graph membership,
  normalization, validation, and commit requirements defined by the workspace

#### Scenario: A document sets status

- **WHEN** a document under `data/` carries a `status` field
- **THEN** the pre-commit check fails and names the document

#### Scenario: A reserved file loses its OKF shape

- **WHEN** `data/index.md` or `data/log.md` departs from the shape its OKF
  schema defines
- **THEN** `iwe schema validate` fails and names the file
```

## Depends on

- [Conflict-free knowledge layout](20261031-kb-conflict-free-layout.md) ships
  first: it retires `status` from the schemas and the graph, which this check
  then keeps out.

## Verification

- `uv run pytest docs/knowledge/tests/test_no_status_field.py` passes, and fails
  naming the document when a scratch copy of the graph gains `status`.
- `pre-commit run no-status-field --all-files` passes.
- `iwe normalize` leaves the tree unchanged and `iwe schema validate` exits 0.

## Out of scope

- Feature documents: none claims an OKF stance.
- The text of the shipped [Conflict-free knowledge
  layout](20261031-kb-conflict-free-layout.md) plan, which stays as recorded.
- Rejecting `status` in a schema.

## Key references

Verified anchor points (line numbers as of 2026-11-01):

- `docs/knowledge/data/spec/iwe-workflow-skills.md:781` — Requirement: Workflow
  improvements preserve the IWE model
- `.pre-commit-config.yaml:154` — `plan-checkboxes`, the local pytest hook to
  follow
- `.pre-commit-config.yaml:164` — `iwe-schema-validate`
- `docs/knowledge/tests/test_rank_and_base_schemas.py:132` —
  `test_no_schema_declares_status`
- `.iwe/schemas/okf.yaml:3` — the OKF frontmatter schema, which accepts
  undeclared fields
- `.iwe/config.toml:110` — `[schemas.okf]` binding
