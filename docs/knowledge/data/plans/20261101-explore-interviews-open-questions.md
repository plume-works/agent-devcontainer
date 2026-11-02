---
type: plan
created: 2026-11-01
release:
- features/agentdev-iwe-workflow-skills
description: Make Explore settle a problem's open questions with the user one at a time — one topic per turn, one decision per question, in the user's names and design, settled by evidence, with each answer recorded verbatim as it is given.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
rank: 50
---

# Explore settles open questions one at a time

## Context

The Explore skill's stance tells it to "Open several threads and let the user
follow what resonates", and the skill has no rule limiting a reply to one topic
or one decision, keeping the user's names and design, or recording each answer
as it is given. The user asked for Explore to run, by default, as a step-by-step
interview on the open questions: one topic at a time, one decision per question,
each answer recorded as it is given.

The change refines the behavior the [agentdev IWE workflow
skills](../features/agentdev-iwe-workflow-skills.md) feature ships.

## Approach

Replace the stance bullet that asks for several open threads with one that
surfaces the threads and follows them one at a time, and add a
`## Settling open questions` section that states the interview rules. Both are
skill text, applied verbatim from the approved wording. The Explore requirement
in [IWE workflow skills](../spec/iwe-workflow-skills.md) gains the matching
sentence and scenario.

Rejected: a separate interview skill or mode the user opts into. The user asked
for the interview as Explore's default, and a second entry point would leave the
default behavior unchanged.

## Implementation Steps

### Task 1: Replace the "Curious, not prescriptive" bullet

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`

- [ ] Replace the `**Curious, not prescriptive**` bullet in `## The stance` with
  this text, verbatim:

  ``` markdown
  - **Curious, not prescriptive** — ask the questions that emerge, challenge
    assumptions, reframe. Surface the open threads, then follow them one at a
    time; don't funnel toward a conclusion.
  ```

### Task 2: Add the `## Settling open questions` section

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`

- [ ] Insert this section after `## The stance`, before
  `## During implementation`, verbatim:

  ``` markdown
  ## Settling open questions

  Once the problem has open questions, interview the user — one at a time:

  - **One topic per turn.** Name it and stay on it until the user settles it;
    list what remains only when a topic closes. A finding that belongs to another
    topic is noted for later, not opened.
  - **One decision per question.** Numbered options, each with its consequence,
    your recommendation first. Use the structured-question tool where the choice
    fits it.
  - **The user's names and the user's design.** Changing either is its own
    question, never a silent substitution.
  - **Evidence before argument.** When a choice hinges on how the system behaves,
    settle it with a read-only replay or a scratch test, then ask. Never raise a
    corner case the evidence does not show.
  - **Record each answer as it is given** in `.tmp/approved-wording-<slug>.md`:
    the user's words verbatim, marked approved only on an explicit yes.
  ```

### Task 3: Validate the catalog

**Files:** none

- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — the Explore requirement
gains the interview rule and a scenario; its other four scenarios are unchanged.

``` markdown
## MODIFIED Requirements

### Requirement: Explore remains an adaptive thinking mode

The Explore skill SHALL investigate the project graph and codebase without
editing application code, SHALL remain adaptive and patient as the problem takes
shape, and SHALL offer capture or a phase handoff without pressuring the user to
formalize unfinished thinking. When the user approves specific text, Explore
SHALL persist it verbatim outside the conversation and reproduce it verbatim in
the handoff, and SHALL never paraphrase it. Once the problem has open questions,
Explore SHALL settle them with the user one at a time — one topic per turn and
one decision per question, in the user's names and design — and SHALL record
each answer verbatim as it is given.

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
```

## Verification

- `grep -n "Open several threads" .agents/plugins/agentdev/skills/iwe-explore/SKILL.md`
  prints nothing.
- The replaced bullet and the `## Settling open questions` section in
  `iwe-explore/SKILL.md` match the fenced blocks in Tasks 1 and 2 byte for byte.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- The rest of `iwe-explore/SKILL.md`: the issue intake,
  `## During implementation`, `## Capturing`, and `## Rules` keep their current
  text.
- The e2e Explore scenario in `scripts/e2e/iwe-workflows/scenarios.py`, which
  tests a different behavior.
- Interview behavior in any other skill, including Plan.

## Key references

Verified anchor points (line numbers as of 2026-11-01):

- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md:54` — `## The stance`
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md:64` — the
  `**Curious, not prescriptive**` bullet (through line 66)
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md:77` —
  `## During implementation`, the section the new one precedes
- `docs/knowledge/data/spec/iwe-workflow-skills.md:45` —
  `### Requirement: Explore remains an adaptive thinking mode`
