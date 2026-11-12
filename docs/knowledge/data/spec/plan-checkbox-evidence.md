---
type: spec
description: A ticked plan checkbox must carry the evidence that closed it, tasks must be atomic, and a mechanical gate enforces the shape on every commit and CI run.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: docs/knowledge/tests/test_plan_checkboxes.py
- resource: py_packages/validate_agent_files/README.md
- resource: docs/knowledge/AGENTS.md
---

# Plan checkbox evidence

## Purpose

A plan document is the record the next session builds on, and its checkboxes are
its most load-bearing claim. This specifies what a tick must carry, how tasks
must be sized so a tick can be honest, and the gate that enforces the shape.

The gate reads shape only — that a tick is accompanied by a claim. Whether the
claim is *true* is Verify's judgment and a human's; no mechanical check can
supply it. Shape is what a check can hold: a blanket substitution and a set of
careful verifications produce identical bytes, and only the evidence line tells
them apart.

## Requirements

### Requirement: A ticked task carries the evidence that closed it

Every ticked `- [x]` task under a plan's task section SHALL carry an indented
`- **Evidence:**` child naming what closed it, specifically enough that a later
session can repeat the check: for code, a test id (`path::name`) or a command,
which Verify re-runs against the current tree; for docs or config with no test,
the file and anchor that changed; for external work, the CI run or the PR that
closes it, which stands alone. A commit id on its own SHALL NOT count as
evidence, and neither SHALL residue: raw command stdout transcribed as evidence,
an ephemeral identifier, or an uncommitted `.tmp/` harness. Plan SHALL specify
the format, Implement SHALL write the evidence line in the same edit that ticks
the box and commit it together with the change it describes, and the convention
SHALL be recorded where every session loads it rather than only where a skill is
invoked.

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

#### Scenario: Evidence cites residue

- **WHEN** a ticked task's evidence line quotes command output, names an
  ephemeral identifier, or cites a script under `.tmp/` that is not committed
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

The Plan skill SHALL constrain task granularity so that one task is one outcome
and one checkbox is one observation. A task that could be described as half-done
SHALL be split, a task whose evidence is external SHALL stand alone, and a
checkbox that joins independently observable events SHALL be split into one
checkbox per event. Plan's coherence check SHALL ask, for every checkbox, which
single observation closes it.

#### Scenario: A task bundles two outcomes

- **WHEN** a planned task could ever be described as half-done
- **THEN** Plan splits it, preventing a tick earned by the half done locally
  from reading as a claim about the half that was not

#### Scenario: A task's evidence is external

- **WHEN** a task's evidence is a CI run, a deploy, a review, or a published
  artifact
- **THEN** it is planned as its own task, because the session writing the code
  cannot close it

#### Scenario: A checkbox joins independent observations

- **WHEN** a checkbox's outcome needs two or more events observed separately,
  such as a passing run and a failing run
- **THEN** Plan splits it into one checkbox per event, so each can be ticked
  with its own evidence as it is observed

#### Scenario: An event may never occur on its own

- **WHEN** a checkbox's observation is a failure or cancellation path that
  normal operation may never produce
- **THEN** the checkbox names how the event is provoked

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

#### Scenario: A task is left unticked

- **WHEN** an unticked `- [ ]` task carries no `**Closed by:**` line
- **THEN** Verify reports a CRITICAL naming three routes out — complete the
  task, tick it if it is already done, or drop it through Plan's revise mode,
  which treats dropping a task as a material scope change and asks the user —
  and takes none of them

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

### Evidence names a check Verify can repeat, never a commit id

A ticked task's evidence names a test id or command, a file and anchor, or a CI
run or PR, and Verify re-runs a named test or command in the current tree. Every
reader of evidence — the `plan-checkboxes` gate, Verify, and the Ship run that
repeats Verify — runs before merge, and nothing reads a shipped plan's evidence
after it. A commit id buys none of those readers anything, while rebase, squash
merge, and amend rewrite it; a check Verify can re-run lets Verify judge a tick
the same way every time. With nothing left that must name a commit, a task's
code, its tick, and its evidence line land in one commit. Evidence lines sit
outside the plan-mode durable-knowledge audit, so Implement and Verify apply its
residue vocabulary at that surface themselves: transcribed stdout, an ephemeral
identifier, or an uncommitted `.tmp/` harness names nothing a later session can
repeat.

Rejected:

- **Keeping commit ids.** Nothing reads evidence after merge, and the rule costs
  a second commit per task and a revision round whenever the named hash is
  wrong.
- **The PR number.** It survives a squash, but it names the whole change, so
  Verify still has nothing per task to repeat.
- **A test id only.** Docs, config, and external work have no test, and each
  needs its own kind of evidence anyway.
- **Free text checked for shape only.** Verify's judgment flips between runs
  when a line names nothing it can repeat.

### Honest ticks come from the artifact's shape, not more prose rules

A tick is honest only when it carries an evidence line, because rules telling
Implement when it may tick were already written and were violated anyway. A
find-and-replace can flip every box in a file; it cannot write the evidence line
each tick needs.

Rejected:

- **Another round of prose rules in the Implement rulebook.** The rules that
  would have prevented over-claiming already existed; more of the same changes
  nothing a sweep can bypass.

### The gate is a knowledge-base test, not a validator extension

The checkbox gate is `docs/knowledge/tests/test_plan_checkboxes.py`, run by
pytest, because plan documents are this workspace's knowledge graph, not agent
files.

Rejected:

- **Extending `validate_agent_files`.** That package validates skills, agents,
  and prompts in any repository and must stay usable with no knowledge of this
  one's graph.

### Checkbox granularity is the planner's rule

One observation per checkbox is a planning rule, so `iwe-planner` owns it.

Rejected:

- **The Durable Knowledge Auditor flags bundled checkboxes in its plan scope.**
  That audit asks one question, durable-knowledge residue, and a second gate
  would widen it.
