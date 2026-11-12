---
type: plan
created: 2026-11-03
release: internal
description: Backfill a Ship review on every plan already shipped, repairing what the graph can still fix through iwe-shipper's fix operation, then make the ship-records CLI require the section on every done plan.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md
- resource: scripts/check-ship-records.py
rank: 500
---

# Backfill Ship reviews on shipped plans

## Context

[Review every ship against Ship's obligations](20261103-ship-review.md) stamps
each plan Ship ships from then on with a `## Ship review`, and [Gate done bugs
and Ship reviews in pre-commit](20261103-ship-records-gate.md) checks that
section's shape wherever it exists. 96 plans were at `stage: done` before
either, with no `## Ship review`. The repository owner decided to backfill them
all, which also exercises `iwe-ship-reviewer` on real plans, and then to require
the section on every done plan.

Those plans shipped under older Ship rules. The repository owner decided that a
backfill repairs every gap the graph can still fix, and marks `N/A` only history
that cannot change: whether Verify reported zero CRITICAL, and whether the ship
commit edited a hub, release page, or `data/log.md`.

## Approach

`iwe-ship-reviewer` ship mode gains a backfill flag. Under it, the Verify item
and the hub-edit item take `N/A: shipped before Ship review` when the plan's
history holds no evidence for them; every other item is checked as in ship mode.
The `ship-records` CLI accepts that exact reason on those two items and on no
other.

A backfill run goes plan by plan, through the loop `/agentdev:iwe-ship` runs:
`iwe-ship-reviewer` in ship mode with the backfill flag; on a gap list,
`iwe-shipper` with the operation `fix`, for at most 3 rounds. A plan whose gaps
outlast the rounds is reported, not stamped. Once every done plan carries a
`## Ship review`, the CLI requires the section on every plan at `stage: done`.

Rejected: `N/A: shipped before Ship review` on any item that fails. It would
stamp graph state that can still be repaired, such as a bug with no `## Fix` or
a feature never set to `implemented`.

## Implementation Steps

### Task 1: The reviewer backfills

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md`

- [ ] Ship mode with the backfill flag marks the Verify and hub-edit items
  `N/A: shipped before Ship review` when the plan's history has no evidence for
  them, and checks every other item as ship mode does.

### Task 2: The CLI accepts the backfill reason

**Files:** Modify: `scripts/check-ship-records.py`,
`scripts/tests/test_check_ship_records.py`

- [ ] The CLI passes `N/A: shipped before Ship review` on the Verify and
  hub-edit items, and still fails it, or any other `N/A`, on the plan-stage
  item.

### Task 3: Every shipped plan is reviewed

**Files:** Modify: every plan at `stage: done` under
`docs/knowledge/data/plans/`, and the bug, feature, and spec documents their
gaps name

- [ ] Every plan at `stage: done` ends with a `## Ship review` written by
  `iwe-ship-reviewer`, after `iwe-shipper` `fix` rounds repaired its gaps, and
  `uv run pre-commit run ship-records --all-files` passes.
- [ ] Every plan whose gaps outlasted 3 fix rounds is repaired or reported to
  the repository owner, with its gaps.

### Task 4: The CLI requires the section

**Files:** Modify: `scripts/check-ship-records.py`,
`scripts/tests/test_check_ship_records.py`

- [ ] The CLI fails a plan at `stage: done` with no `## Ship review`, and
  `uv run pre-commit run ship-records --all-files` passes on the graph.

### Task 5: CI passes with the requirement

- [ ] The pull request's `pre-commit` job in Primary checks, and the `ci.yml`
  pre-commit run with `--all-files`, pass with the `ship-records` hook.

## Spec changes

[Pre-commit gate](../spec/pre-commit-gate.md) — the requirement that [Gate done
bugs and Ship reviews in pre-commit](20261103-ship-records-gate.md) adds now
requires the section and accepts the backfill reason.

``` markdown
## MODIFIED Requirements

### Requirement: Ship records are gated in pre-commit

A pre-commit hook SHALL run a checker CLI over every bug and plan document
pre-commit passes it, at commit time, over a commit range, and with
`--all-files`. The CLI SHALL fail a bug at `stage: done` that has no `## Fix`
heading, a plan at `stage: done` that has no `## Ship review` section, and a
plan whose `## Ship review` section differs from the fixed structure, and SHALL
report every violation with `path:line`. It SHALL accept
`N/A: shipped before Ship review` on the Verify item and the hub-edit item, and
no `N/A` on the plan-stage item.

#### Scenario: a done bug has no Fix

- **WHEN** a commit stages a bug document at `stage: done` with no `## Fix`
- **THEN** the hook fails and names the document.

#### Scenario: an open bug has no Fix

- **WHEN** a bug document at `stage: pending` or `stage: planned` has no
  `## Fix`
- **THEN** the hook passes it.

#### Scenario: a done plan has no Ship review

- **WHEN** a plan document at `stage: done` has no `## Ship review`
- **THEN** the hook fails and names the document.

#### Scenario: a Ship review is malformed

- **WHEN** a plan's `## Ship review` misses an item, reorders the items, leaves
  one unticked, or marks the Verify, plan-stage, or hub-edit item `N/A` with
  any other reason, or the plan-stage item `N/A` at all
- **THEN** the hook fails and names the line.

#### Scenario: a backfilled review lacks history

- **WHEN** a plan's Verify or hub-edit item reads
  `N/A: shipped before Ship review`
- **THEN** the hook passes that item.

#### Scenario: CI checks every file

- **WHEN** CI runs pre-commit with `--all-files`
- **THEN** the hook checks every bug and plan document.
```

## Depends on

- [Gate done bugs and Ship reviews in pre-commit](20261103-ship-records-gate.md)
- [Review every ship against Ship's obligations](20261103-ship-review.md)

## Verification

- `uv run pytest scripts/tests/test_check_ship_records.py`
- `uv run pre-commit run ship-records --all-files`
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Re-running Verify on a shipped plan.
- Changing a shipped plan's intent sections; a backfill writes only
  `## Ship review` and the repairs its gaps name.

## Key references

- `.pre-commit-config.yaml › "id: plan-checkboxes"` — the `plan-checkboxes`
  hook, beside which [Gate done bugs and Ship reviews in
  pre-commit](20261103-ship-records-gate.md) adds the `ship-records` hook
- `.github/workflows/ci.yml › "run: uv run pre-commit run --all-files"` —
  pre-commit with `--all-files`
- `.github/workflows/primary-checks.yml › "uv run pre-commit run --from-ref"` —
  pre-commit over the pull request's range
- `docs/knowledge/data/spec/pre-commit-gate.md#requirement-ci-runs-the-pre-commit-hooks-as-the-lint-gate`
  — Requirement: CI runs the pre-commit hooks as the lint gate
