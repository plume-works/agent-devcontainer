# Plan checkbox evidence Specification

## Purpose

A plan document is the record the next session builds on, and its checkboxes are
its most load-bearing claim. This specifies what a tick must carry, how tasks
must be sized so a tick can be honest, and the gate that enforces the shape.

The gate reads shape only — that a tick is accompanied by a claim. Whether the
claim is _true_ is Verify's judgment and a human's; no mechanical check can
supply it. Shape is what failed in [Plan checkbox
over-claiming](../../../docs/knowledge/data/bugs/plan-checkbox-over-claiming.md), where a blanket
substitution and a set of careful verifications produced identical bytes.

## Requirements

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

### Requirement: Plan tasks are sized so a tick can be honest

The Plan skill SHALL constrain task granularity so that one task is one outcome.
A task that could be described as half-done SHALL be split, and a task whose
evidence is external SHALL stand alone.

#### Scenario: A task bundles two outcomes

- **WHEN** a planned task could ever be described as half-done
- **THEN** Plan splits it, preventing a tick earned by the half done locally
  from reading as a claim about the half that was not

#### Scenario: A task's evidence is external

- **WHEN** a task's evidence is a CI run, a deploy, a review, or a published
  artifact
- **THEN** it is planned as its own task, because the session writing the code
  cannot close it

### Requirement: Plans record narrative verification evidence

A plan SHALL have a specified home for evidence about the work as a whole:
`## Verification results`, following `## Verification`, written as the work
happens rather than reconstructed at the end, and omitted until there is
something to record.

#### Scenario: A plan accumulates verification evidence

- **WHEN** a session runs a plan's verification commands or discovers something
  that changes what the plan claims
- **THEN** it records the result under `## Verification results` rather than
  improvising a section per plan

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

### Requirement: The checkbox format is mechanically gated

A test SHALL audit every plan document and report every violation with
`path:line`, not only the first. It SHALL run from the repository's test suite,
from a pre-commit hook when a plan changes, and in the knowledge-base CI job.

#### Scenario: An active plan has an unsupported tick

- **WHEN** a plan with no `stage` in frontmatter has a ticked task whose
  indented `- **Evidence:**` child is absent or empty
- **THEN** the gate fails and names the offending `path:line`

#### Scenario: A completed plan still has open work

- **WHEN** a plan carries `stage: done` and any task is still `- [ ]`
- **THEN** the gate fails and names the offending `path:line`

#### Scenario: A closed plan lacks evidence lines

- **WHEN** a plan carries `stage: done` and its ticked tasks have no evidence
  children
- **THEN** the gate passes, because closed plans are historical records and
  backfilling evidence into them would be inventing it

#### Scenario: A plan uses the older task heading

- **WHEN** a plan heads its checkboxes `## Tasks` rather than
  `## Implementation Steps`
- **THEN** the gate audits it, because silently skipping a whole document is the
  invisibility this contract exists to remove

#### Scenario: A checkbox appears outside the task section

- **WHEN** a checkbox appears under another section, such as a format example
  under `## Approach`, or inside a fenced code block
- **THEN** the gate does not treat it as a task

## Rationale

### Evidence names a check, never a commit id

Every reader of evidence — the `plan-checkboxes` gate, Verify, and the Ship run
that repeats Verify — runs before merge, so a commit id buys nothing they need,
while rebase, squash merge, and amend rewrite it. A check Verify can re-run lets
Verify judge a tick the same way every time. With nothing left that must name a
commit, a task's code, its tick, and its evidence land in one commit.

Rejected:

- **Keep commit ids.** They cost a second commit per task and a revision round
  whenever the named hash is wrong.
- **The PR number.** It survives squash but names the whole change, so Verify
  has nothing per task to repeat.
- **A test id only.** Docs, config, and external work have no test.
- **Free text checked for shape only.** Verify's judgment flips between runs
  when a line names nothing it can repeat.
