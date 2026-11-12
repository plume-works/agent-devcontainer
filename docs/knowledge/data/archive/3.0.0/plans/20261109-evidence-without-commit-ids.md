---
type: plan
created: 2026-11-09
release:
- features/agentdev-iwe-workflow-skills
description: Plan task evidence names a check Verify can repeat — a test id or command, a file and anchor, or a CI run or PR — instead of a commit id, and a task's tick lands in the same commit as its code.
sources:
- resource: docs/knowledge/data/spec/plan-checkbox-evidence.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: docs/knowledge/AGENTS.md
stage: done
completed: 2026-11-09
---

# Plan task evidence without commit ids

## Context

[Make plan task evidence survive history
rewrites](../backlog/resilient-task-evidence.md) asked how evidence should be
named once rebase, squash merge, and amend rewrite the commit ids it cites. This
plan settles it by removing commit ids from evidence.

Evidence exists to fix [Plan checkbox
over-claiming](../../1.0.0/bugs/plan-checkbox-over-claiming.md): a bulk tick has
to write a separate claim per box, and Verify gets something concrete to test
before Ship. Every reader of evidence — the `plan-checkboxes` gate, Verify, and
the Ship run that repeats Verify — runs before merge; nothing reads a shipped
plan's evidence after merge. The commit-id rule added by [Command-result
evidence is judged
inconsistently](../../2.0.0/bugs/command-result-evidence-ambiguous.md) asks a
tick to name the commit holding its code, which forces the code and the tick
into separate commits, because a commit cannot name its own hash.

The change reaches every workspace user and template consumer through [agentdev
IWE workflow skills](../../1.0.0/features/agentdev-iwe-workflow-skills.md) and
the bootstrap copy of the operating manual.

Every decision below is the maintainer's.

## Approach

A ticked task's `- **Evidence:**` line names a check Verify can repeat in the
current tree, by kind, in the maintainer's approved wording (Task 1). A commit
id on its own is not evidence. With nothing left that must name a commit, the
tick and its evidence line land in the same commit as the code they describe,
replacing the code-first, tick-second rule. Verify re-runs a named test or
command and treats one that fails or no longer exists as an unsupported tick.

The residue rule stays: raw command stdout, an ephemeral identifier, and an
uncommitted `.tmp/` harness are not evidence. The `plan-checkboxes` gate keeps
checking shape only.

Rejected alternatives:

- **Keep commit ids.** Nothing reads evidence after merge, and the rule costs a
  second commit per task and a revision round whenever the named hash is wrong.
- **The PR number.** It survives squash, but it points at the whole change, so
  Verify still has nothing per task to repeat.
- **A test id only.** Docs, config, and external work have no test; each needs
  its own kind of evidence anyway.
- **Free text checked for shape only.** Verify's judgment flips between runs
  when a line names nothing it can repeat, which is the defect [Command-result
  evidence is judged
  inconsistently](../../2.0.0/bugs/command-result-evidence-ambiguous.md)
  records.

Assumption: a line that names a commit alongside a valid check still counts, so
ticked tasks in active plans need no rewrite.

## Implementation Steps

### Task 1: The rule in the operating manual

**Files:** Modify: `docs/knowledge/AGENTS.md`, `docs/knowledge/CHANGELOG.md`,
and their copies under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/`

The approved wording for what an evidence line names:

``` markdown
* Code: a test id (`path::name`) or a command, which Verify re-runs against the current tree.
* Docs or config with no test: the file and anchor that changed.
* External work: the CI run or the PR that closes it, which must stand alone.
```

- [x] The **A ticked task carries the evidence that closed it** bullet in
  `docs/knowledge/AGENTS.md` names what evidence is with the approved wording
  above, verbatim as nested bullets; states that a commit id on its own is not
  evidence; and states that the tick and its evidence line land in the same
  commit as the code they describe. The sentences requiring the commit and the
  code-first, tick-second order are gone. The bootstrap copy stays
  byte-identical.
  - **Evidence:**
    `docs/knowledge/AGENTS.md#conventions › "A commit id on its own is not evidence"`
    and its three nested bullets;
    `cmp docs/knowledge/AGENTS.md .agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/AGENTS.md`
    reports no difference; commit e1d299c3.
- [x] `docs/knowledge/CHANGELOG.md` gains a `### Changed` entry under
  `## [Unreleased]`: evidence names a check Verify can repeat instead of a
  commit, the tick lands with its code, and nothing needs migrating. The
  bootstrap copy stays byte-identical.
  - **Evidence:**
    `docs/knowledge/CHANGELOG.md#changed › "Plan task evidence names a check Verify can repeat, not a commit"`;
    `cmp docs/knowledge/CHANGELOG.md .agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/CHANGELOG.md`
    reports no difference; commit e1d299c3.

### Task 2: Planner rule

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [x] Step 4's `## Implementation Steps` bullet says a ticked checkbox's
  `- **Evidence:**` child names what closed it, listing the three kinds in the
  approved wording from Task 1, and drops "a check and its result count only
  together with the commit that holds the change they check".
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "once ticked, it carries an indented"`
    and its three nested bullets;
    `grep -c 'together with the commit' .agents/plugins/agentdev/agents/iwe-planner.agent.md`
    prints 0; commit 355740d0.

### Task 3: Implementer rules

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [x] Step 6 closes a task in one commit holding the code, the tick, and the
  evidence line, which names one of the three kinds in the approved wording from
  Task 1; the residue list drops "a check cited without that commit" and keeps
  the rest. Step 8, step 3 of `## Running the loop`, and the `## Rules` bullet
  on commit order state the same-commit rule; the `## Rules` bullets on one box
  per edit and one task per commit stay.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#steps › "The code, the tick, and its evidence line land together in one commit"`,
    `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#steps › "its code, tick, and evidence line in one commit"`,
    `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#running-the-loop › "the task's evidence line in one commit"`,
    and
    `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#rules › "A task's code, its checkbox flip, and its evidence line land in one commit"`;
    `grep -cE 'cited without that commit|code committed first|committed before its checkbox|naming that commit|commit, test run' .agents/plugins/agentdev/agents/iwe-implementer.agent.md`
    prints 0.

### Task 4: Verifier rule

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-verifier.agent.md`

- [x] The **Completeness** bullet reports a ticked task as a CRITICAL,
  recommendation "untick it", when its evidence line is missing or empty, names
  nothing of the three kinds in Task 1's approved wording, or names a test or
  command that fails or no longer exists when Verify re-runs it in the current
  tree. "A check and its result count only together with the commit" and "a
  check cited without that commit" are gone; the rest of the residue list and
  the CI-job sentence stay.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#steps › "names a test or command that fails or no longer exists"`
    and
    `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#steps › "A commit id on its own is not evidence"`;
    `grep -cE 'together with the commit|cited without that commit' .agents/plugins/agentdev/agents/iwe-verifier.agent.md`
    prints 0.

### Task 5: Record the decision

**Files:** Create:
`docs/knowledge/data/archive/3.0.0/architecture/evidence-without-commit-ids.md`;
Modify: `docs/knowledge/data/architecture.md`

- [x] The architecture document records the decision, its reason (every reader
  of evidence runs before merge), the same-commit rule, and the rejected
  alternatives from `## Approach`, with sources naming this plan and the backlog
  task; `data/architecture.md` links it at its sorted position.
  - **Evidence:**
    `docs/knowledge/data/archive/3.0.0/architecture/evidence-without-commit-ids.md#decision`,
    `docs/knowledge/data/archive/3.0.0/architecture/evidence-without-commit-ids.md#why`,
    `docs/knowledge/data/archive/3.0.0/architecture/evidence-without-commit-ids.md#same-commit-rule`,
    and
    `docs/knowledge/data/archive/3.0.0/architecture/evidence-without-commit-ids.md#alternatives-rejected`;
    the inclusion link `[Evidence without commit ids]` in
    `docs/knowledge/data/architecture.md`; `iwe schema validate` passes.

### Task 6: Observe Verify re-running named checks

- [x] The Verify run on this plan re-runs the test or command each ticked task
  names and reports none of them as an unsupported tick for lacking a commit.
  - **Closed by:** the maintainer, reading that Verify report.
  - **Evidence:** the maintainer confirmed the `Ready to ship` Verify report
    saved by
    `.agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py lookup data/plans/20261109-evidence-without-commit-ids`,
    which re-ran each named check and reported no tick as unsupported for
    lacking a commit.

## Spec changes

[Plan checkbox evidence](../../../spec/plan-checkbox-evidence.md):

``` markdown
## MODIFIED Requirements

### Requirement: A ticked task carries the evidence that closed it

Every ticked `- [x]` task under a plan's task section SHALL carry an indented
`- **Evidence:**` child naming what closed it, specifically enough that a later
session can repeat the check: for code, a test id (`path::name`) or a command,
which Verify re-runs against the current tree; for docs or config with no test,
the file and anchor that changed; for external work, the CI run or the PR that
closes it, which stands alone. A commit id on its own SHALL NOT count as
evidence. Plan SHALL specify the format, Implement SHALL write the evidence line
in the same edit that ticks the box and commit it together with the change it
describes, and the convention SHALL be recorded where every session loads it
rather than only where a skill is invoked.

#### Scenario: A task is completed

- **WHEN** a task's complete specified behavior is implemented and its required
  tests and checks pass
- **THEN** one edit ticks the box and writes its `- **Evidence:**` child naming
  what closed it

#### Scenario: Evidence names only a commit

- **WHEN** a ticked task's evidence line names a commit and no test, command,
  file and anchor, CI run, or PR
- **THEN** it is residue rather than evidence, and Verify reports it as a ticked
  task without usable evidence

#### Scenario: Evidence cannot be named

- **WHEN** a session would tick a box but cannot name a test, command, file and
  anchor, CI run, or PR behind it
- **THEN** the box stays unticked, and the inability to name evidence is treated
  as the check working rather than as a formatting obstacle

#### Scenario: Work is partial or its evidence fails

- **WHEN** a task is only partially implemented, contains deferred behavior, or
  its required tests or checks do not pass
- **THEN** the box stays unticked and carries no evidence line

#### Scenario: Several boxes would be ticked at once

- **WHEN** more than one checkbox would change state
- **THEN** each is a separate edit, because a blanket `- [ ]` → `- [x]`
  substitution is itself the defect and produces bytes indistinguishable from
  verified ticks

#### Scenario: A tick lands in a commit

- **WHEN** a task closes
- **THEN** its code, the checkbox flip, and its evidence line land in one commit

### Requirement: Verify audits ticked and unticked boxes asymmetrically

The Verify skill SHALL treat an unsupported tick as a CRITICAL finding with the
recommendation "untick it", alongside its existing CRITICAL for an unchecked
task, and SHALL state the asymmetry that justifies auditing both. Verify SHALL
re-run each test or command a ticked task names, in the current tree.

#### Scenario: A ticked task has no usable evidence

- **WHEN** a ticked `- [x]` task's `- **Evidence:**` line is missing or empty,
  or names no test, command, file and anchor, CI run, or PR
- **THEN** Verify reports a CRITICAL recommending that the box be unticked

#### Scenario: A named check fails or is gone

- **WHEN** a ticked task's evidence names a test or command that fails, or no
  longer exists, when Verify re-runs it in the current tree
- **THEN** Verify reports a CRITICAL recommending that the box be unticked

#### Scenario: The two failures are weighed

- **WHEN** Verify reports on checkbox state
- **THEN** it records that an unchecked box which is actually done is a nuisance
  the next session clears, while a checked box that is not done is a false
  premise the next session builds on
```

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- `cmp` of `docs/knowledge/AGENTS.md` and `docs/knowledge/CHANGELOG.md` against
  their copies under
  `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/` reports
  no difference.
- In `docs/knowledge/AGENTS.md`, `iwe-planner.agent.md`,
  `iwe-implementer.agent.md`, and `iwe-verifier.agent.md`,
  `grep -nE 'together with the commit|cited without that commit|code committed first|committed before its checkbox|naming that commit|commit, test run'`
  finds nothing.
- `uv run scripts/check-anchors.py` exits 0.
- `uv run pytest docs/knowledge/tests` passes.
- `iwe normalize && git diff --exit-code` and `iwe schema validate` pass.

## Out of scope

- Checkbox granularity — [Plan tasks bundle independent
  observations](../bugs/plan-tasks-bundle-independent-observations.md) — and the
  `plan-checkboxes` gate, which keeps checking shape only; both belong to [Plans
  as ephemeral implementation documents; stories as the planned
  work](../../../backlog/ephemeral-plans-and-stories.md).
- The template progress document `template-consume` writes, which is a separate
  consumer-owned record.
- Rewriting evidence in shipped plans, or in active plans' ticked tasks.
- Re-checking evidence after merge.

## Key references

- `docs/knowledge/data/spec/plan-checkbox-evidence.md#requirement-a-ticked-task-carries-the-evidence-that-closed-it`
  — the first modified requirement
- `docs/knowledge/data/spec/plan-checkbox-evidence.md#requirement-verify-audits-ticked-and-unticked-boxes-asymmetrically`
  — the second modified requirement
- `docs/knowledge/AGENTS.md#conventions › "A ticked task carries the evidence that closed it"`
  — the workspace rule
- `docs/knowledge/CHANGELOG.md#unreleased` — the scaffold changelog
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "once ticked, it carries an indented"`
  — step 4, the evidence format
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#steps › "Closing it is then a single edit that ticks"`
  — step 6, closing a task
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#steps › "its code, tick, and evidence line in one commit"`
  — step 8
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#running-the-loop › "the code, the test, and the task's evidence line in one commit"`
  — loop step 3, the code route
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#rules › "A task's code, its checkbox flip, and its evidence line land in one commit"`
  — the commit-order rule
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#steps › "names a test or command that fails or no longer exists"`
  — the Completeness rule
- `docs/knowledge/data/architecture.md` — the architecture hub
