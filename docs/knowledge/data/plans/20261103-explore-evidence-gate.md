---
type: plan
stage: done
completed: 2026-11-03
created: 2026-11-03
release:
- features/agentdev-iwe-workflow-skills
description: Make Explore propose a change only for a problem it can show has occurred, list imagined cases as not observed, and weigh a risk its own proposal creates against that proposal instead of opening it as a new question.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
released: 2.1.0
---

# Explore proposes only for observed problems

## Context

Explore checks every claim it makes about the existing system, but nothing
requires a problem to have occurred before Explore designs for it. Its stance
asks it to "challenge assumptions, reframe" and "surface risks", and the only
evidence rule — "Never raise a corner case the evidence does not show" — sits in
`## Settling open questions`, which applies after a proposal already exists.

Observed occurrence: the autonomy-loop exploration behind PR #651 proposed
rules, stop triggers, and open questions for cases no transcript showed, and
opened as open questions risks that existed only because of its own proposal.
The plans that came out of it kept only the changes backed by counted incidents.

The change refines the behavior the [agentdev IWE workflow
skills](../archive/1.0.0/features/agentdev-iwe-workflow-skills.md) feature
ships.

## Approach

Add an `Evidence-first` bullet at the top of `## The stance`, so the gate
applies before any proposal is formed. Add a rule under `## Rules` that treats a
risk created by Explore's own proposal as a cost of that proposal rather than a
new thread. Narrow `Honest about unknowns` to risks the evidence shows. All
three edits apply the wording the user approved, verbatim. The Explore
requirement in [IWE workflow skills](../spec/iwe-workflow-skills.md) gains the
matching sentence and scenario.

Rejected: extending the existing `Evidence before argument` interview rule. It
runs only once open questions exist, which is after the over-scoped proposal has
been written.

## Implementation Steps

### Task 1: Add the `Evidence-first` stance bullet

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`

- [x] Insert this bullet as the first bullet of `## The stance`, before
  `**Grounded, not theoretical**`, verbatim:

  ``` markdown
  - **Evidence-first** — a problem earns a proposal only by an observed
    occurrence: a transcript, commit, issue, failing run, or `file:line`. Before
    proposing anything, collect the occurrences and count them. Propose the
    smallest change that would have prevented those occurrences; a general rule
    needs several observed cases it explains. A case you can only imagine is
    listed under "not observed", never designed for.
  ```

  - **Evidence:** commit `2958893d` inserts the block as the first
    `## The stance` bullet; a byte comparison of the fenced block against
    `iwe-explore/SKILL.md` finds it exactly once, and
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes (61/61 skills valid, 0 errors, 0 warnings).

### Task 2: Narrow the `Honest about unknowns` bullet

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`

- [x] Apply this change to the `**Honest about unknowns**` bullet in
  `## The stance`, verbatim:

  ``` diff
  -- **Honest about unknowns** — surface risks, gaps, and what would need a
  -  spike to know. "We can't know this without trying" is a finding.
  +- **Honest about unknowns** — surface risks and gaps the evidence shows, and
  +  what would need a spike to know. "We can't know this without trying" is a
  +  finding.
  ```

  - **Evidence:** commit `9a4df5b4` replaces the `**Honest about unknowns**`
    bullet; a byte comparison finds the `+` side of the fenced diff exactly once
    in `iwe-explore/SKILL.md` and the `-` side absent, and
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes (61/61 skills valid, 0 errors, 0 warnings).

### Task 3: Add the proposal-costs rule

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`

- [x] Insert this bullet in `## Rules`, directly after the bullet that begins
  `Every claim about the existing system is checked`, verbatim:

  ``` markdown
  - **A proposal's own costs are not the system's problems.** A risk or open
    question that exists only because of something you proposed is weighed
    against that proposal — or drops it — never opened as a new thread. An open
    question survives only if its answer changes what gets built for an observed
    case.
  ```

  - **Evidence:** commit `1d31a3f3` inserts the block in `## Rules` directly
    after the `Every claim about the existing system is checked` bullet; a byte
    comparison finds the fenced block exactly once in `iwe-explore/SKILL.md`,
    and `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes (61/61 skills valid, 0 errors, 0 warnings).

### Task 4: Validate the catalog

**Files:** none

- [x] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
  - **Evidence:** at commit `1d31a3f3`, which holds all three
    `iwe-explore/SKILL.md` edits,
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    exits 0 (61/61 skills valid, 0 errors, 0 warnings).

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — the Explore requirement
gains the evidence-gate sentence and a scenario; its other five scenarios are
unchanged.

``` markdown
## MODIFIED Requirements

### Requirement: Explore remains an adaptive thinking mode

The Explore skill SHALL investigate the project graph and codebase without
editing application code, SHALL remain adaptive and patient as the problem takes
shape, and SHALL offer capture or a phase handoff without pressuring the user to
formalize unfinished thinking. Explore SHALL propose a change only for a problem
it can show has occurred, SHALL list a case it can only imagine as not observed
rather than design for it, and SHALL weigh a risk its own proposal creates
against that proposal rather than open it as a new question. When the user
approves specific text, Explore SHALL persist it verbatim outside the
conversation and reproduce it verbatim in the handoff, and SHALL never
paraphrase it. Once the problem has open questions, Explore SHALL settle them
with the user one at a time — one topic per turn and one decision per question,
in the user's names and design — and SHALL record each answer verbatim as it is
given.

#### Scenario: Exploration starts from an open-ended idea

- **WHEN** the user asks to explore an idea without committing to implementation
- **THEN** Explore follows relevant questions and tradeoffs, grounds claims in
  current project evidence, and ends with the current understanding and an
  optional next step

#### Scenario: Exploration starts from a GitHub issue

- **WHEN** the user invokes Explore with an issue URL, an `OWNER/REPO#N`
  reference, or an issue number
- **THEN** Explore reads the issue and all of its comments into `./.tmp/` before
  investigating, verifies the issue's claims against the code and the graph
  rather than adopting them, never edits the issue, and carries the issue URL
  into any handoff to Plan

#### Scenario: Exploration starts during implementation

- **WHEN** the user invokes Explore because an active implementation task
  exposed a complication
- **THEN** Explore reads the active plan and task, investigates without editing
  code, and hands any resulting decision, scope change, or new work back to the
  skill that owns plan execution

#### Scenario: The user approves specific wording

- **WHEN** the user agrees to specific text — wording for a document, a snippet,
  a message — that a later plan or edit will apply
- **THEN** Explore writes it verbatim to `.tmp/approved-wording-<slug>.md`
  before continuing, names that file in the handoff, and reproduces the text
  verbatim rather than describing it

#### Scenario: The exploration has open questions

- **WHEN** the problem being explored has more than one open question
- **THEN** Explore names one topic and stays on it until the user settles it,
  asks one decision at a time as numbered options with a recommendation, keeps
  the user's names and design unless changing them is the question asked,
  settles a question about system behavior with evidence before asking it,
  records each answer verbatim in `.tmp/approved-wording-<slug>.md` — marked
  approved only on an explicit yes — and opens the next topic only after the
  current one is settled

#### Scenario: Exploration proposes a change

- **WHEN** Explore is about to propose a change to the system
- **THEN** it first collects and counts the observed occurrences of the problem,
  proposes the smallest change that would have prevented them, lists any case
  it can only imagine under "not observed", and opens no thread or open
  question for a risk that exists only because of its own proposal
```

## Verification

- Task 4's catalog validation passes.
- `iwe-explore/SKILL.md` contains each of the three approved blocks byte for
  byte, compared against the fenced blocks in Tasks 1-3.

## Out of scope

- The Plan, Implement, Verify, and Ship rulebooks. This plan changes only
  Explore.
- A test that reads `SKILL.md` to check its wording. `AGENTS.md` `### Tests`
  does not count a check of file contents as coverage.

## Key references

- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#the-stance` —
  `## The stance`
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#the-stance › "— before proposing directions, check what"`
  — `**Grounded, not theoretical**`, the current first stance bullet
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#the-stance › "— surface risks, gaps, and what would need a"`
  — `**Honest about unknowns**`
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#settling-open-questions › "When a choice hinges on how the system behaves"`
  — `**Evidence before argument**`, the interview-time evidence rule
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#rules` — `## Rules`
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#rules › "Every claim about the existing system is checked against the"`
  — `Every claim about the existing system is checked`
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-explore-remains-an-adaptive-thinking-mode`
  — `Requirement: Explore remains an adaptive thinking mode`
