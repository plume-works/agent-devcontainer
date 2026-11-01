---
type: plan
created: 2026-11-01
release:
- features/agentdev-iwe-workflow-skills
- bugs/ship-ignores-unshipped-dependency
description: Let Implement start a plan whose dependency has not shipped by stacking its branch on the dependency's open pull requests, and make Ship refuse a plan until every dependency has shipped.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T14:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py
---

# Build on an unshipped dependency, ship after it

## Context

Implement stops on any `## Depends on` plan that is not `stage: done`, so a plan
waits for its dependency's whole lifecycle — implementation, review, merge, and
ship — before its own work can start. Ship has the opposite gap: it never reads
`## Depends on`, so a plan can ship before its prerequisite ([Bug: Ship ships a
plan whose prerequisite has not
shipped](../bugs/ship-ignores-unshipped-dependency.md)).

[Manual stacked pull requests](../features/manual-stacked-prs.md) make it safe
to build on an open pull request. This plan lets [the IWE workflow
skills](../features/agentdev-iwe-workflow-skills.md) use them: implementation
may run ahead of an unshipped dependency, shipping may not.

The maintainer decided that a branch whose candidate predecessors sit in
different chains is based on all of them, with one `Depends-on:` trailer each,
and gets no pull request while more than one of them is unmerged, because such a
pull request cannot show a clean diff.

## Approach

When Implement creates a plan's work branch, each `## Depends on` plan that is
not `stage: done` resolves to the top of its open pull requests — its
`iwe/<slug>/iter-*` heads, walked down their bases as `pr-restack-all`, from the
dependency plan, walks a chain. The plan's own open earlier iterations are
candidates too. With no candidate the branch is cut from `main`; with candidates
the branch is cut through `git-new-branch --depends-on`, once per candidate that
is not already below another candidate in the same chain. A dependency that is
not shipped and has no open pull request still stops Implement. `pr-open`
refuses a pull request while more than one dependency is unmerged, as the
dependency plan specifies.

Ship gains the check the bug names: before Verify, every `## Depends on` plan
must be `stage: done` at the remote default branch, or Ship returns a blocker
report naming it and changes nothing.

The candidate lookup is a script in the plugin's `bin/`, next to the other
shared code, so the implementer runs it rather than re-deriving it.

Rejected: keeping the implementer gate and letting plans wait — it serializes
every dependent plan behind a full ship cycle.

## Implementation Steps

### Task 1: Find a plan's predecessor pull requests

**Files:** Create: `.agents/plugins/agentdev/bin/plan_predecessors.py`,
`.agents/plugins/agentdev/tests/test_plan_predecessors.py`

- [ ] `plan_predecessors.py <plan-key>` reads the plan's `## Depends on` and
  each dependency's state at the remote default branch, and prints the pull
  requests to pass to `git-new-branch --depends-on`: for each unshipped
  dependency and for the plan's own open earlier iterations, the top of their
  open `iwe/<slug>/iter-*` pull requests, dropping any that sits below another
  in the same chain; it stops on an unshipped dependency with no open pull
  request
- [ ] Tests cover no dependency, a shipped dependency, one open dependency, two
  dependencies in one chain, two in different chains, the plan's own open
  iteration, and an unshipped dependency without a pull request, with the pull
  request lookup behind one replaceable function

### Task 2: Implement stacks on an unshipped dependency

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`,
`.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md`

- [ ] Step 3 accepts an unshipped dependency that has an open pull request and
  stops only on one without; step 4 runs Task 1's script and passes each printed
  pull request to `git-new-branch --depends-on`, or cuts from `main` when none
  is printed
- [ ] `iwe-implement-all` no longer says a plan stops at an unshipped
  dependency, and dispatches a dependent plan once its dependency has an open
  pull request

### Task 3: Ship refuses a plan before its dependencies ship

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`,
`docs/knowledge/data/bugs/ship-ignores-unshipped-dependency.md`

- [ ] Normal shipping, before Verify, reads every `## Depends on` plan's stage
  at the remote default branch and returns a Ship blocker report naming each
  plan that is not `stage: done`, with no mutation
- [ ] The bug's `## Fix` names this plan

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md):

``` markdown
## MODIFIED Requirements

### Requirement: Implement starts work on its own branch

The Implement skill SHALL, when the checkout is on `main` or `master`, create
the work branch through the git-new-branch skill, named by the iwe-branch-name
skill's next `impl` iteration for the plan, before executing the first task, and
SHALL continue on the current branch otherwise. The branch SHALL be cut from
`main` when no `## Depends on` plan is unshipped and the plan has no open
earlier iteration; otherwise it SHALL be cut with `--depends-on` for the top
open pull request of each such dependency and earlier iteration, leaving out any
that sits below another in the same chain.

#### Scenario: Implementation starts on main

- **WHEN** Implement begins plan `data/plans/<date>-<slug>` with `main` checked
  out and every dependency shipped
- **THEN** it creates branch `iwe/<slug>/iter-<N>-impl`, with `N` from
  iwe-branch-name, from `main` through git-new-branch before executing any task

#### Scenario: Implementation starts on a feature branch

- **WHEN** Implement begins with a branch other than `main` or `master` checked
  out
- **THEN** it executes the plan on that branch without creating another

#### Scenario: Dependency in review

- **WHEN** a `## Depends on` plan is not shipped and has an open pull request
- **THEN** the work branch is created with `--depends-on` for that pull request

#### Scenario: Dependencies in two chains

- **WHEN** two unshipped dependencies have open pull requests in different
  chains
- **THEN** the work branch is created with `--depends-on` for both

## ADDED Requirements

### Requirement: Implement stops on a dependency with nothing to build on

The Implement skill SHALL stop before creating a branch when a `## Depends on`
plan is not `stage: done` and has no open pull request, and SHALL name it.

#### Scenario: Unshipped dependency without a pull request

- **WHEN** a dependency is not shipped and none of its work branches has an
  open pull request
- **THEN** Implement stops and names the dependency

### Requirement: Ship waits for every dependency

The Ship skill SHALL, before Verify in normal shipping, read the stage of every
plan in the plan's `## Depends on` at the remote default branch, and SHALL
return a Ship blocker report naming each one that is not `stage: done`, making
no state change.

#### Scenario: Dependency not shipped

- **WHEN** Ship runs on a plan whose dependency is still active
- **THEN** it returns a blocker report naming the dependency and leaves the plan
  active

#### Scenario: Dependency blocked earlier in a ship-all run

- **WHEN** iwe-ship-all ships a dependency that comes back blocked, then a plan
  depending on it
- **THEN** the dependent plan is not shipped
```

## Depends on

[Replace gh stack with manual stacked pull
requests](20261101-manual-stacked-prs.md) — supplies
`git-new-branch --depends-on` and `pr-open`'s refusal while more than one
dependency is unmerged.

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_plan_predecessors.py`
  passes.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- Reading `iwe-implementer.agent.md` steps 3–4 and `iwe-shipper.agent.md` step 3
  against the spec delta finds every scenario covered.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Ship ordering inside `iwe-ship-all` beyond the Shipper's own check.
- Restacking a plan branch after its dependency merges; `pr-restack-all` and the
  rewritten `pr-merge-stack` of the dependency plan own that.

## Key references

Verified anchor points (line numbers as of 2026-11-01):

- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:45` — step 3, Check
  `## Depends on`
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:48` — step 4, Start
  on a work branch
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:49` — step 1, select the
  operation and inspect current state
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:71` — step 3, Run Verify
  for normal shipping
- `.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md:16` — a plan stops
  at its own dependency check
- `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md:13` — dispatch in
  dependency order
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py:283`
  — `read_plan_state`
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py:327`
  — `pull_request_heads`
- `docs/knowledge/data/spec/iwe-workflow-skills.md:231` — Requirement: Implement
  starts work on its own branch
- `docs/knowledge/data/bugs/ship-ignores-unshipped-dependency.md:48` — `## Fix`
