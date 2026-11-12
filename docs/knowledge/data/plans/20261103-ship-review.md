---
type: plan
created: 2026-11-03
release:
- features/ship-review
description: Add the iwe-ship-reviewer catalog agent with a plan mode and a ship mode, give iwe-shipper a fix operation, and have every route that ships a plan review the result and fix its gaps up to three times, stamping the plan with a Ship review checklist.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/657
stage: done
completed: 2026-11-11
released: 3.0.0
---

# Review every ship against Ship's obligations

## Context

[Ship review](../archive/3.0.0/features/ship-review.md) is the feature this plan
delivers. `iwe-shipper` step 6 requires a `## Fix` on each bug its plan's
`release` lists, but step 7 only re-inspects that section, does not refuse to
commit without it, and no fresh-context check confirms Ship's obligations after
the ship commit. The repository owner decided:

- `iwe-shipper` enforces a listed bug's `## Fix`.
- A new catalog agent, `iwe-ship-reviewer`, checks Ship's obligations from a
  fresh context, in a plan mode and a ship mode drawn from the steps of
  `iwe-shipper.agent.md`.
- In ship mode it runs after `iwe-shipper` commits. `/agentdev:iwe-ship` owns
  the loop: on a gap it re-dispatches `iwe-shipper` with a fix operation that
  does only the named gaps and never re-runs Verify, up to 3 times.
- A shipped plan carries the result as a `## Ship review` section with a fixed
  structure, every item `confirmed` or `N/A`.

## Approach

`iwe-ship-reviewer` is report-only in plan mode. In ship mode it reads the
shipped plan, the documents its `release` lists, the specs its `## Spec changes`
names, and the ship commit's diff, and checks each item of the structure below.
When every item is `confirmed` or `N/A`, it appends `## Ship review` as the
plan's last section and commits it; otherwise it writes nothing and returns the
failing items as a gap list.

`iwe-shipper` gains the operation `fix`, whose prompt quotes the gap list. It
performs only the operations the gaps name, runs no Verify, repeats no step the
gap list does not name, validates, and commits. Its step 7 refuses to commit a
ship while a bug its `release` lists has no `## Fix`.

`/agentdev:iwe-ship`, after `iwe-shipper` reports a shipped plan, dispatches
`iwe-ship-reviewer` in ship mode with the plan key. On a gap list it dispatches
`iwe-shipper` with `fix` and the gaps quoted, then reviews again, for at most 3
fix rounds, and reports the remaining gaps if any are left.

Rejected: `iwe-shipper` dispatching `iwe-ship-reviewer` as its last step. The
repository owner put the loop in `/agentdev:iwe-ship`.

Assumptions:

- `iwe-ship-reviewer` commits its own `## Ship review`, because it is the only
  writer of that section.
- `/agentdev:iwe-plan` answering a Ship blocker report runs the same loop itself
  after it dispatches `iwe-shipper`, because `/agentdev:iwe-ship` is
  explicit-only (spec/iwe-workflow-skills, Requirement: Ship and Implement start
  only from an explicit request or a named dispatcher).

## Implementation Steps

### Task 1: The reviewer agent

**Files:** Create: `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md`

- [x] The agent takes a plan key and a mode. Plan mode reports, changing
  nothing, whether the plan's `release` is `internal` or names existing
  documents, every listed bug is at `stage: planned`, every listed feature is
  `accepted`, and `## Spec changes` uses one of its three forms with complete
  post-change requirements in any delta.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md#inputs` and
    `#plan-mode`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`.
- [x] Ship mode checks each item of the structure below and, when all hold,
  appends the section verbatim in shape and commits it; when any fails, it
  writes nothing and returns the failing items.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md#ship-mode` and
    `#report`.

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

### Task 2: The Shipper enforces Fix and takes a fix operation

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`

- [x] Step 7 refuses to commit, returning a Ship blocker report, while a bug the
  plan's `release` lists has no `## Fix`.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "While a bug `release` lists has no"`.
- [x] The operation `fix`, with the gap list quoted, performs only the
  operations the gaps name, runs no Verify, validates, and commits.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#the-fix-operation` and
    `#inputs`.

### Task 3: Ship runs the review loop

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md`,
`.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [x] `/agentdev:iwe-ship` dispatches `iwe-ship-reviewer` in ship mode after a
  shipped plan, dispatches `iwe-shipper` with `fix` on a gap list for at most 3
  rounds, and reports the reviewer's outcome and any remaining gaps.
  - **Evidence:**
    `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md#review-loop` and
    `#steps › "Review a shipped plan."`.
- [x] `iwe-planner` step 8, after it re-dispatches `iwe-shipper` for a Ship
  blocker report and the plan ships, runs the same review loop.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "run the review loop of"`.

### Task 4: The loop closes a real gap

- [x] `/agentdev:iwe-ship` on a scratch plan whose `release` lists a bug, with
  the Shipper's `## Fix` removed before the review, ends with the bug's `## Fix`
  written by a `fix` round and a `## Ship review` that passes the `ship-records`
  hook.
  - **Evidence:** [PR
    #820](https://github.com/plume-works/agent-devcontainer/pull/820)
    `## Verification` records the end-to-end run on a scratch plan: the
    `ship-records` hook refused removing the bug's `## Fix`, a `fix` round
    restored it, and the `## Ship review` passed `ship-records`.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — a new requirement for
the review.

``` markdown
## ADDED Requirements

### Requirement: Every ship is reviewed against Ship's obligations

`iwe-shipper` SHALL NOT commit a ship while a bug its plan's `release` lists has
no `## Fix`. After `iwe-shipper` ships a plan, `/agentdev:iwe-ship` and Plan revise
mode answering a Ship blocker report
SHALL dispatch `iwe-ship-reviewer` in ship mode with
the plan key. When it reports gaps, they SHALL dispatch `iwe-shipper` with the
operation `fix` and the gaps quoted, which SHALL perform only those operations
without running Verify, and review again, for at most 3 fix rounds.
`iwe-ship-reviewer` SHALL append the `## Ship review` checklist to the plan only
when every item is `confirmed` or `N/A`.

#### Scenario: a ship meets every obligation

- **WHEN** `iwe-ship-reviewer` finds every obligation met
- **THEN** the plan ends with a `## Ship review` whose every item is ticked
  `confirmed` or `N/A`.

#### Scenario: a ship leaves a gap

- **WHEN** `iwe-ship-reviewer` reports a listed bug with no `## Fix`
- **THEN** `iwe-shipper` runs `fix` for that gap alone, without Verify, and the
  plan is reviewed again.

#### Scenario: gaps outlast three rounds

- **WHEN** a gap remains after 3 fix rounds
- **THEN** Ship reports the gap and the plan has no `## Ship review`.

#### Scenario: a plan is reviewed before implementation

- **WHEN** `iwe-ship-reviewer` runs in plan mode
- **THEN** it reports whether the plan gives Ship what it needs and changes
  nothing.
```

## Depends on

- [Nest agent dispatch to depth 5 on both
  harnesses](20261103-nested-dispatch-depth.md)
- [Gate done bugs and Ship reviews in pre-commit](20261103-ship-records-gate.md)

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
- The Task 4 run on a scratch plan, with `uv run pre-commit run ship-records`
  over the scratch plan.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Running plan mode on plan edits: [The iwe-plan-review
  skill](20261103-plan-review-skill.md).
- Backfilling `## Ship review` on plans already shipped: [Backfill Ship reviews
  on shipped plans](20261103-backfill-ship-reviews.md).
- `iwe-shipper` dispatching `iwe-verifier`: [The Shipper dispatches
  Verify](20261103-shipper-dispatches-verifier.md).

## Key references

- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#inputs` — `## Inputs`;
  `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "Apply frontmatter transitions idempotently.** A work"`
  — step 6, Apply frontmatter transitions;
  `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "Validate, commit, and report.** Run"`
  — step 7, Validate, commit, and report;
  `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#report` — `## Report`
- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md#steps › "with that prompt and wait for its report."`
  — step 2, Dispatch `iwe-shipper`;
  `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md#steps › "Re-post its report verbatim.** When it reports"`
  — step 3, Re-post its report
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "Validate, close the issue, re-ship a blocked plan, and"`
  — step 8 re-dispatches `iwe-shipper` for a Ship blocker report
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-ship-and-implement-start-only-from-an-explicit-request-or-a-named-dispatcher`
  — Requirement: Ship and Implement start only from an explicit request or a
  named dispatcher

## Ship review

Reviewed by `iwe-ship-reviewer` on 2026-11-11.

- [x] Verify reported zero CRITICAL — confirmed: Ready to ship
  data/plans/20261103-ship-review
- [x] Every `## Spec changes` operation is in its spec — confirmed:
  data/spec/iwe-workflow-skills
- [x] Every spec the plan created is linked from `data/spec.md` — N/A: no spec
  created
- [x] Every spec the plan retired was removed with `iwe delete` — N/A: no spec
  retired
- [x] The plan is `stage: done` with `completed` and no `rank` — confirmed:
  2026-11-11
- [x] Every feature in `release` is `stage: implemented` — confirmed:
  data/features/ship-review
- [x] Every bug in `release` is `stage: done` with no `rank` — N/A: `release`
  lists no bug
- [x] Every bug in `release` has a `## Fix` that links this plan — N/A:
  `release` lists no bug
- [x] Ship edited no hub, release page, or `data/log.md` — confirmed
