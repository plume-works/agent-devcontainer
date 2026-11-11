---
type: plan
created: 2026-11-03
release: internal
description: Add a checker CLI that a pre-commit hook runs over bug and plan documents, failing a done bug with no Fix section and a Ship review section whose shape is not the fixed one, in every pre-commit mode.
sources:
- resource: .pre-commit-config.yaml
- resource: .iwe/schemas/bug.yaml
- resource: docs/knowledge/data/plans/20261102-bug-lifecycle-and-sections.md
---

# Gate done bugs and Ship reviews in pre-commit

## Context

`iwe-shipper` writes a done bug's `## Fix` in its step 6 and re-checks it in
step 7, but nothing mechanical refuses a done bug without one. [Bug lifecycle
stages and sections](20261102-bug-lifecycle-and-sections.md) decided that
nothing enforces a done bug's `## Fix`: "no schema rule, CI check, or refusal
gate". The repository owner reversed that decision: a done bug's `## Fix` is
enforced mechanically.

`iwe` 0.29.3 accepts conditionals in a document schema only inside
`frontmatter`; a document-level `if`/`then` or `anyOf` in
`.iwe/schemas/bug.yaml` fails with "unknown keyword". The bug schema therefore
cannot require `## Fix` only when `stage: done`, and the gate is a CLI instead.

The same CLI checks the `## Ship review` section that [Review every ship against
Ship's obligations](20261103-ship-review.md) appends to a shipped plan, wherever
the section exists.

## Approach

A standard-library Python CLI, `scripts/check-ship-records.py`, takes document
paths as arguments, checks each, and prints every violation as `path:line` with
the rule it breaks, exiting non-zero when there is any:

- A bug document at `stage: done` has a `## Fix` heading.
- A plan document that has a `## Ship review` section has the fixed shape below:
  the reviewer line, then the nine items in order, each ticked, each ending in
  `— confirmed` (with `: <evidence>` where the item takes evidence) or
  `— N/A: <reason>`. The items about Verify, the plan's own stage, and hub edits
  never take `N/A`.

A `ship-records` hook in `.pre-commit-config.yaml` runs it with
`pass_filenames: true` on files matching `^docs/knowledge/data/(bugs|plans)/`.
Pre-commit then hands it the staged files at commit time, the changed files for
a `--from-ref`/`--to-ref` range as `.github/workflows/primary-checks.yml` runs
it, and every matching file with `--all-files` as `.github/workflows/ci.yml`
runs it.

Rejected:

- A pytest file like the `plan-checkboxes` and `no-status-field` hooks. The
  repository owner chose a CLI; it is the program under test, and the tests run
  it on made-up documents.
- Requiring `## Fix` on every bug in the schema. Open bugs have none.

Assumption: the CLI lives in `scripts/`, because the gate guards this
repository's graph; shipping it to consumers through the catalog is out of
scope.

## Implementation Steps

### Task 1: The CLI gates a done bug's Fix

**Files:** Create: `scripts/check-ship-records.py`,
`scripts/tests/test_check_ship_records.py`

- [x] Given bug documents, the CLI fails a `stage: done` bug without `## Fix`,
  passes one with it, and passes a `pending`, `planned`, or `cancelled` bug
  without it; it reports every violation, not only the first. Tests run the CLI
  on made-up documents under the test scratch root.
  - **Evidence:**
    `uv run pytest scripts/tests/test_check_ship_records.py -k bug` —
    `test_done_bug_without_fix_fails`, `test_done_bug_with_fix_passes`,
    `test_open_or_cancelled_bug_without_fix_passes`,
    `test_every_violation_is_reported`.

### Task 2: The CLI checks the Ship review shape

**Files:** Modify: `scripts/check-ship-records.py`,
`scripts/tests/test_check_ship_records.py`

- [x] Given plan documents, the CLI passes a plan with no `## Ship review`,
  passes one whose section matches the structure below, and fails, naming the
  line, a missing or reordered item, an unticked item, an item ending in neither
  `confirmed` nor `N/A:`, and `N/A` on the Verify, plan-stage, or hub-edit item.
  - **Evidence:**
    `uv run pytest scripts/tests/test_check_ship_records.py -k "plan or review or item"`
    — `test_plan_without_ship_review_passes`,
    `test_well_formed_ship_review_passes`,
    `test_missing_item_fails_naming_the_section`,
    `test_reordered_items_fail_naming_the_line`,
    `test_unticked_item_fails_naming_the_line`,
    `test_item_with_neither_ending_fails`, `test_na_on_a_mandatory_item_fails`.

The approved structure, verbatim (`|` separates the two endings an item can
take):

``` markdown
## Ship review

Reviewed by `iwe-ship-reviewer` on <YYYY-MM-DD>.

- [x] Verify reported zero CRITICAL — confirmed: <Verify's verdict line>
- [x] Every `## Spec changes` operation is in its spec — confirmed: <spec keys> | N/A: `## Spec changes` is None
- [x] Every spec the plan created is linked from `data/spec.md` — confirmed: <keys> | N/A: no spec created
- [x] Every spec the plan retired was removed with `iwe delete` — confirmed: <keys> | N/A: no spec retired
- [x] The plan is `stage: done` with `completed` and no `rank` — confirmed: <completed date>
- [x] Every feature in `release` is `stage: implemented` — confirmed: <keys> | N/A: `release` lists no feature
- [x] Every bug in `release` is `stage: done` with no `rank` — confirmed: <keys> | N/A: `release` lists no bug
- [x] Every bug in `release` has a `## Fix` that links this plan — confirmed: <keys> | N/A: `release` lists no bug
- [x] Ship edited no hub, release page, or `data/log.md` — confirmed
```

### Task 3: Pre-commit runs the CLI

**Files:** Modify: `.pre-commit-config.yaml`

- [x] A `ship-records` hook runs `uv run scripts/check-ship-records.py` with
  `pass_filenames: true` on `^docs/knowledge/data/(bugs|plans)/.*\.md$`, and
  `uv run pre-commit run ship-records --all-files` passes on the current graph.
  - **Evidence:** `.pre-commit-config.yaml › "id: ship-records"`;
    `uv run pre-commit run ship-records --all-files` passes.

### Task 4: CI runs the hook

- [x] The pull request's `pre-commit` job in Primary checks passes with the
  `ship-records` hook in its output.
  - **Evidence:** PR #815, Primary checks `pre-commit` job
    https://github.com/plume-works/agent-devcontainer/actions/runs/43065396149/job/130678882483
    — `ship-records ... Passed`.

## Spec changes

[Pre-commit gate](../spec/pre-commit-gate.md) — a new requirement for the hook.

``` markdown
## ADDED Requirements

### Requirement: Ship records are gated in pre-commit

A pre-commit hook SHALL run a checker CLI over every bug and plan document
pre-commit passes it, at commit time, over a commit range, and with
`--all-files`. The CLI SHALL fail a bug at `stage: done` that has no `## Fix`
heading, and a plan whose `## Ship review` section differs from the fixed
structure, and SHALL report every violation with `path:line`.

#### Scenario: a done bug has no Fix

- **WHEN** a commit stages a bug document at `stage: done` with no `## Fix`
- **THEN** the hook fails and names the document.

#### Scenario: an open bug has no Fix

- **WHEN** a bug document at `stage: pending` or `stage: planned` has no
  `## Fix`
- **THEN** the hook passes it.

#### Scenario: a Ship review is malformed

- **WHEN** a plan's `## Ship review` misses an item, reorders the items, leaves
  one unticked, or marks the Verify, plan-stage, or hub-edit item `N/A`
- **THEN** the hook fails and names the line.

#### Scenario: CI checks every file

- **WHEN** CI runs pre-commit with `--all-files`
- **THEN** the hook checks every bug and plan document.
```

## Verification

- `uv run pytest scripts/tests/test_check_ship_records.py`
- `uv run pre-commit run ship-records --all-files`
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Requiring `## Ship review` on every done plan: [Backfill Ship reviews on
  shipped plans](20261103-backfill-ship-reviews.md).
- Checking that a `## Fix` describes the shipped fix; `iwe-ship-reviewer` judges
  content.
- Shipping the CLI to template consumers through the catalog.

## Key references

- `.pre-commit-config.yaml › "id: plan-checkboxes"` — the `plan-checkboxes`
  hook; `.pre-commit-config.yaml › "id: banned-frontmatter-keys"` — the
  `banned-frontmatter-keys` hook;
  `.pre-commit-config.yaml › "id: iwe-schema-validate"` — `iwe-schema-validate`
- `.iwe/schemas/bug.yaml › "header: { const: Fix }"` — `Fix` at `minContains: 0`
- `.github/workflows/primary-checks.yml › "uv run pre-commit run --from-ref"` —
  pre-commit over the pull request's range
- `.github/workflows/ci.yml › "run: uv run pre-commit run --all-files"` —
  pre-commit with `--all-files`
- `scripts/tests/scratch.py` — `TMP_ROOT`, the test scratch root
- `docs/knowledge/data/spec/pre-commit-gate.md#requirement-ci-runs-the-pre-commit-hooks-as-the-lint-gate`
  — Requirement: CI runs the pre-commit hooks as the lint gate
