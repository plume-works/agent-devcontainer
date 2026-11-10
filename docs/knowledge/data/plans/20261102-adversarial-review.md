---
type: plan
created: 2026-11-02
release:
- features/agentdev-iwe-workflow-skills
description: Add an adversarial review — a report-only catalog agent and its entry skill — that looks for ways to defeat a plan's design or its implemented code, runs only when a plan task or the user asks, and leaves Verify a conformance check.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
stage: done
completed: 2026-11-04
released: 2.1.0
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

- [x] The agent's tools are `Bash, Read, Grep, Glob`; its description names the
  `iwe-adversarial-review` skill as its only dispatcher.
  - **Evidence:** Commit 04a8965 adds `iwe-adversarial-reviewer.agent.md` with
    `tools: Bash, Read, Grep, Glob` and a description that names the
    `iwe-adversarial-review` skill as its only dispatcher;
    `uv run validate_agent_files --recommend . --require-marketplace claude` on
    that commit: 0 errors, 0 warnings.
- [x] Its inputs are the plan key, the target (`plan` or `code`), and quoted
  approvals; anything else in the prompt is not evidence.
  - **Evidence:** Commit 04a8965, `## Inputs` of
    `iwe-adversarial-reviewer.agent.md`: plan key, target `plan` or `code`, and
    quoted approvals, with any other prompt content not evidence;
    `uv run validate_agent_files --recommend . --require-marketplace claude` on
    that commit: 0 errors, 0 warnings.
- [x] The plan rubric and the code rubric are as `## Approach` describes; every
  code finding names the plan claim it defeats, or `none`, with `path:line`
  evidence or the label "unverified".
  - **Evidence:** Commit 04a8965, `## Steps` step 2 and `## Report` of
    `iwe-adversarial-reviewer.agent.md`: the plan and code rubrics from
    `## Approach`, each finding with a **Defeats** claim or `none` and
    `path:line` evidence or "unverified";
    `uv run validate_agent_files --recommend . --require-marketplace claude` on
    that commit: 0 errors, 0 warnings.
- [x] It edits nothing, commits nothing, dispatches no agent, and runs a command
  whose effects reach beyond the working tree only under a quoted approval that
  names it.
  - **Evidence:** Commit 04a8965, `## Rules` of
    `iwe-adversarial-reviewer.agent.md`: no edit, commit, or dispatch, and a
    command reaching beyond the working tree only under a quoted approval naming
    it; the agent has no `Edit`, `Write`, or `Agent` tool;
    `uv run validate_agent_files --recommend . --require-marketplace claude` on
    that commit: 0 errors, 0 warnings.

### Task 2: The entry skill

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-adversarial-review/SKILL.md`; Modify:
`.agents/plugins/agentdev/README.md`

- [x] The skill builds the conversation-free prompt, dispatches
  `iwe-adversarial-reviewer`, and re-posts its report verbatim.
  - **Evidence:** Commit 6de0ec2 adds `skills/iwe-adversarial-review/SKILL.md`:
    steps 2-4 build a prompt of plan key, target, and quoted approvals only,
    dispatch `iwe-adversarial-reviewer` forwarding no conversation turns, and
    re-post its report verbatim;
    `uv run validate_agent_files --recommend . --require-marketplace claude` on
    that commit: 0 errors, 0 warnings.
- [x] Its description limits it to an explicit request or a plan task that runs
  it.
  - **Evidence:** Commit 6de0ec2, `description` of
    `skills/iwe-adversarial-review/SKILL.md`: use only on an explicit request
    for a named plan or a plan task that runs it, never while planning;
    `uv run validate_agent_files --recommend . --require-marketplace claude` on
    that commit: 0 errors, 0 warnings.
- [x] The README's skill table lists it.
  - **Evidence:** Commit 6de0ec2 adds the `/agentdev:iwe-adversarial-review` row
    to the Knowledge-graph workflow (IWE) skill table of
    `.agents/plugins/agentdev/README.md`, after `/agentdev:iwe-verify`.
- [x] `uv run validate_agent_files --recommend . --require-marketplace claude`
  reports no errors.
  - **Evidence:** Commit 6de0ec2:
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 62/62 skills valid, 0 errors, 0 warnings.

### Task 3: Plan and Implement rules for the review

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [x] The planner's `## Rules` says a plan may carry one task, closing or
  near-closing, that runs `/agentdev:iwe-adversarial-review <plan> code`, and
  that planning never invokes the skill.
  - **Evidence:** Commit bd354c4 adds a `## Rules` bullet to
    `iwe-planner.agent.md`: a plan may carry one closing or near-closing task
    that runs `/agentdev:iwe-adversarial-review <plan> code`, and planning never
    invokes that skill nor dispatches `iwe-adversarial-reviewer`, in either
    mode;
    `uv run validate_agent_files --recommend . --require-marketplace claude` on
    that commit: 0 errors, 0 warnings.
- [x] The implementer runs that task once; a finding that defeats a plan claim
  takes the code route, and any other finding is filed through
  `/agentdev:iwe-capture` and named in the report.
  - **Evidence:** Commit bd354c4 adds `## The adversarial review task` to
    `iwe-implementer.agent.md`: the orchestrator runs the task once per plan; a
    finding that names a plan claim takes the code route, and one that names
    none is filed through `/agentdev:iwe-capture` and named in the report;
    `uv run validate_agent_files --recommend . --require-marketplace claude` on
    that commit: 0 errors, 0 warnings.

### Task 4: Record the decision

**Files:** Create: `docs/knowledge/data/architecture/adversarial-review.md`;
Modify: `docs/knowledge/data/architecture.md`

- [x] The document states why adversarial review is separate from Verify, its
  two targets, who may start it, and the three alternatives rejected in
  `## Approach`.
  - **Evidence:** Commit 86c1f62 adds `data/architecture/adversarial-review.md`:
    `## Decision` states why the review is separate from Verify, its `plan` and
    `code` targets, and who may start it; `## Rejected alternatives` lists the
    three from `## Approach`; `iwe schema validate` passes on that commit.
- [x] `data/architecture.md` links it at its sorted position.
  - **Evidence:** Commit 86c1f62 links `architecture/adversarial-review.md` from
    `data/architecture.md` between `actions-approval-permission` and
    `agent-auth-persistence`; `iwe normalize` and `iwe schema validate` pass on
    that commit.

### Task 5: Observe a code review on both harnesses

**Closed by:** the maintainer, observing one session on Claude Code and one on
OpenCode with the default test models, on a plan whose code defeats one of its
own claims.

- [x] `/agentdev:iwe-adversarial-review <plan> code` dispatches one
  `iwe-adversarial-reviewer` whose report names the defeated claim, and the
  checkout has no new commit and a clean worktree.
  - **Evidence:** Maintainer observation on fixture plan
    `data/plans/20261104-slug-guard-fixture` (branch
    `scratch/adversarial-review-fixture`, whose code accepts the `a/b` slug its
    requirement refuses). Claude Code 2.1.318 (cloud, `claude-opus-5-5`),
    session `session_01Q7BhLsjCAGNdn2tLU8PM6G`: one `Agent` dispatch of
    `agentdev:iwe-adversarial-reviewer` with a prompt of only plan key, target
    `code`, and approvals; the reviewer made three read-only `Bash` calls and no
    edit or dispatch; its report names "Slugs cannot leave the plans directory"
    with `scripts/slug_guard.py`; `git status --porcelain` empty before and
    after. OpenCode (`openai/gpt-6.1-sol`), session
    `ses_e5825cbeeffenHmG7Bgao3qB4h`: one `subagent` call to
    `iwe-adversarial-reviewer` with the same three-line prompt; its report names
    the same requirement and the "A nested slug is refused" scenario with
    `scripts/slug_guard.py`; the session's worktree snapshot is unchanged with
    no files changed.

### Task 6: Observe planning leaving the review alone on both harnesses

**Closed by:** the maintainer, observing one session on Claude Code and one on
OpenCode with the default test models.

- [x] `/agentdev:iwe-plan` asked to plan a small change loads no
  `iwe-adversarial-review` skill and dispatches no `iwe-adversarial-reviewer`.
  - **Evidence:** Maintainer observation on branch
    `scratch/adversarial-review-fixture`, request
    `/agentdev:iwe-plan Plan a change so that is_safe_slug in scripts/slug_guard.py also rejects backslashes.`
    Claude Code 2.1.318 (cloud, `claude-opus-5-5`), session
    `session_01Q7BhLsjCAGNdn2tLU8PM6G` after `/clear`: create mode wrote
    `data/plans/20261104-slug-guard-backslash` and `iwe schema validate` passed;
    across its 21 tool calls the only `Skill` load was `agentdev:iwe-audit`,
    inside the Durable Knowledge Auditor, and the only `Agent` dispatch was
    `agentdev:Durable Knowledge Auditor`. OpenCode (`openai/gpt-6.1-sol`),
    session `ses_e5821c2aeffdP6vszCpTPCvBCj`: create mode wrote
    `data/plans/20261104-slug-guard-backslashes` and `iwe schema validate`
    printed no violations; the only skills loaded were `iwe-plan` and
    `git-commit`, and the only `subagent` call was `durable-knowledge-auditor`.
    Neither session loaded `iwe-adversarial-review` or dispatched
    `iwe-adversarial-reviewer`.

## Spec changes

[IWE workflow skills](../../../../openspec/specs/iwe-workflow-skills/spec.md) —
one requirement is added.

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

- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md` — the entry-skill shape
  to follow
- `.agents/plugins/agentdev/README.md#knowledge-graph-workflow-iwe › "| Pre-ship gate and drift audit: graph claims checked"`
  — skill table, `/agentdev:iwe-verify` row
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#rules` — `## Rules`
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#capturing-what-implementation-turns-up`
  — `## Capturing what implementation turns up`
- `docs/knowledge/data/architecture.md#-architecture › "Actions approval"` —
  first entry, `actions-approval-permission`
