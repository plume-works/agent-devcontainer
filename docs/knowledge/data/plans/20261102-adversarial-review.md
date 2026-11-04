---
type: plan
created: 2026-11-02
release:
- features/agentdev-iwe-workflow-skills
description: Add an adversarial review — a report-only catalog agent and its entry skill — that looks for ways to defeat a plan's design or its implemented code, runs only when a plan task or the user asks, and leaves Verify a conformance check.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-03T19:30:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
rank: 187
---

# Add an adversarial review for plans and their code

## Context

[Make the Implement loop converge](20261102-autonomy-loop.md) makes Verify a
conformance check: it reports only against the plan's contract. Looking for ways
to defeat a design or its code is still worth doing for some plans — a trust
check, an integrity check — but it is a different question with its own rubric,
and inside every Verify round it keeps the loop from converging.

The maintainer decided that adversarial review is a separate agent. The planner
may add it as a closing or near-closing task for a plan that warrants it, and a
person may run it on a plan before the plan is finalized. Plan never invokes it.
It joins the [IWE workflow skills in the agentdev
catalog](../features/agentdev-iwe-workflow-skills.md).

## Approach

A catalog agent, `iwe-adversarial-reviewer`, holds the rubric and runs from a
fresh context as a report-only leaf. An entry skill,
`/agentdev:iwe-adversarial-review <plan> <plan|code>`, builds a prompt carrying
only the plan key, the target, and the user's approvals quoted verbatim,
dispatches the agent, and re-posts its report — the shape `/agentdev:iwe-verify`
already uses.

Against the **plan**, the agent looks for claims the design cannot keep,
scenarios the plan misses, and limits a promise does not state. Against the
**code**, it looks for ways to defeat the implemented behaviour, and names for
each finding the plan claim it defeats, or none.

The skill is model-invocable so the Implement loop can run it when a plan task
says so; the planner rulebook forbids invoking it during planning. In the
Implement loop, a finding that defeats a plan claim takes the code route; any
other finding is filed through `/agentdev:iwe-capture`. The review runs once per
plan.

Rejected:

- **Extend the Durable Knowledge Auditor.** It would hold two unrelated rubrics,
  durable text and design attacks.
- **Run it inside every Verify round.** That is the non-convergence this
  separation removes.
- **Make the skill explicit-only.** The Implement loop could not run a planned
  review task.

## Implementation Steps

### Task 1: The adversarial reviewer agent

**Files:** Create:
`.agents/plugins/agentdev/agents/iwe-adversarial-reviewer.agent.md`

- [ ] The agent's tools are `Bash, Read, Grep, Glob`; its description names the
  `iwe-adversarial-review` skill as its only dispatcher.
- [ ] Its inputs are the plan key, the target (`plan` or `code`), and quoted
  approvals; anything else in the prompt is not evidence.
- [ ] The plan rubric and the code rubric are as `## Approach` describes; every
  code finding names the plan claim it defeats, or `none`, with `path:line`
  evidence or the label "unverified".
- [ ] It edits nothing, commits nothing, dispatches no agent, and runs a command
  whose effects reach beyond the working tree only under a quoted approval that
  names it.

### Task 2: The entry skill

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-adversarial-review/SKILL.md`; Modify:
`.agents/plugins/agentdev/README.md`

- [ ] The skill builds the conversation-free prompt, dispatches
  `iwe-adversarial-reviewer`, and re-posts its report verbatim.
- [ ] Its description limits it to an explicit request or a plan task that runs
  it.
- [ ] The README's skill table lists it.
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude`
  reports no errors.

### Task 3: Plan and Implement rules for the review

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [ ] The planner's `## Rules` says a plan may carry one task, closing or
  near-closing, that runs `/agentdev:iwe-adversarial-review <plan> code`, and
  that planning never invokes the skill.
- [ ] The implementer runs that task once; a finding that defeats a plan claim
  takes the code route, and any other finding is filed through
  `/agentdev:iwe-capture` and named in the report.

### Task 4: Record the decision

**Files:** Create: `docs/knowledge/data/architecture/adversarial-review.md`;
Modify: `docs/knowledge/data/architecture.md`

- [ ] The document states why adversarial review is separate from Verify, its
  two targets, who may start it, and the three alternatives rejected in
  `## Approach`.
- [ ] `data/architecture.md` links it at its sorted position.

### Task 5: Observe a code review on both harnesses

**Closed by:** the maintainer, observing one session on Claude Code and one on
OpenCode with the default test models, on a plan whose code defeats one of its
own claims.

- [ ] `/agentdev:iwe-adversarial-review <plan> code` dispatches one
  `iwe-adversarial-reviewer` whose report names the defeated claim, and the
  checkout has no new commit and a clean worktree.

### Task 6: Observe planning leaving the review alone on both harnesses

**Closed by:** the maintainer, observing one session on Claude Code and one on
OpenCode with the default test models.

- [ ] `/agentdev:iwe-plan` asked to plan a small change loads no
  `iwe-adversarial-review` skill and dispatches no `iwe-adversarial-reviewer`.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — one requirement is
added.

``` markdown
## ADDED Requirements

### Requirement: Adversarial review runs only when asked

The adversarial review SHALL be defined once, as the catalog agent
`iwe-adversarial-reviewer`, which `/agentdev:iwe-adversarial-review` dispatches
from a fresh context with a prompt carrying only the plan key, the target
(`plan` or `code`), and the user's approvals quoted verbatim. The agent SHALL
edit nothing and dispatch no agent, and every finding against code SHALL name
the plan claim it defeats, or none. The review SHALL run only on a person's
request or a plan task that runs it; Plan SHALL never invoke it. In the
Implement loop, a finding that defeats a plan claim SHALL take the code route,
and any other finding SHALL be filed through `/agentdev:iwe-capture`.

#### Scenario: A plan task runs the review

- **WHEN** Implement reaches a task that runs
  `/agentdev:iwe-adversarial-review <plan> code` and the report names a
  defeated plan claim
- **THEN** the orchestrator fixes it under the Implement rules, and files every
  finding that names no plan claim

#### Scenario: A person reviews a plan

- **WHEN** the user runs `/agentdev:iwe-adversarial-review <plan> plan`
- **THEN** the agent reports the plan's weaknesses and changes nothing

#### Scenario: Planning does not start the review

- **WHEN** `/agentdev:iwe-plan` creates or revises a plan
- **THEN** it neither loads `/agentdev:iwe-adversarial-review` nor dispatches
  `iwe-adversarial-reviewer`
```

## Depends on

- [Make the Implement loop converge](20261102-autonomy-loop.md)

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
- Tasks 5 and 6 are observation tasks the maintainer closes; Ship waits for
  them.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Adding a review task to any existing plan.
- Changing Verify; that is the dependency's work.

## Key references

Verified anchor points (line numbers as of 2026-11-04):

- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:1` — the entry-skill
  shape to follow
- `.agents/plugins/agentdev/README.md:182` — skill table, `/agentdev:iwe-verify`
  row
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md:248` — `## Rules`
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:198` —
  `## Capturing what implementation turns up`
- `docs/knowledge/data/architecture.md:18` — first entry,
  `actions-approval-permission`
