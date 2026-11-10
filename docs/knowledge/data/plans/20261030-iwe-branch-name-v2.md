---
type: plan
created: 2026-10-30
release:
- features/iwe-branch-name
description: Rename a plan's work branches to iwe/<slug>/iter-<N>-<phase>, with one iteration counter shared by both phases so the numbers run in order across the plan's whole lifecycle.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-branch-name/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
stage: done
completed: 2026-10-30
released: 2.0.0
---

# iwe-branch-name v2: one iteration counter per plan

## Context

[iwe-branch-name](../../../../openspec/specs/iwe-branch-name/spec.md) names a
plan's work branches `<phase>/<slug>/iter-<N>` and counts `N` separately for
`impl` and `ship`. The names therefore cannot say in which order a plan's pull
requests happened: an `impl/foo/iter-3` opened after `ship/foo/iter-1` sorts and
reads the same as one opened before it. The maintainer wants one sequence per
plan, so that `N` is the plan's Nth work branch across its whole lifecycle.

Feature: [iwe-branch-name](../features/iwe-branch-name.md). Builds on the done
plan [iwe-branch-name skill](20261020-iwe-branch-name.md).

## Approach

**Name shape.** `iwe/<slug>/iter-<N>-<phase>`, `phase` ∈ `impl`, `ship`; `slug`
is unchanged (the plan key's file name without `YYYYMMDD-`); `N` ≥ 1. The shape
regex becomes `iwe/([^/]+)/iter-([1-9][0-9]*)-(impl|ship)`, matched in full. The
fixed `iwe/` prefix keeps every plan branch in one namespace, so a branch named
after a bare slug never blocks a work branch; only a ref named exactly `iwe` or
`iwe/<slug>` could, and the tooling makes neither. The name still ends in
`iter-<N>-<phase>`, so no work branch is a path prefix of another.

```
iwe/foo/iter-1-impl
iwe/foo/iter-2-impl
iwe/foo/iter-3-ship
iwe/foo/iter-4-impl   ← ship exposed a gap
iwe/foo/iter-5-ship
```

**One counter.** `next` returns one more than the highest `N` among every
`iwe/<slug>/iter-<N>-<phase>` name of that slug, in either phase, across local
branches, the remote's branches, and the remote's pull requests in any state.
The pull-request query searches `head:iwe/<slug>/`. `--phase`, or the plan
state, picks only the suffix; it no longer narrows the count. Two checkouts
racing may both use one `N` in different phases; the maximum still orders every
later name after both.

**Fresh start.** Names in the v1 shape (`impl/<slug>/iter-<N>`,
`ship/<slug>/iter-<N>`) are not work branches: `parse` reports
`NOT_A_WORK_BRANCH` for them and `next` does not count them. A plan already in
flight restarts at `iter-1`. No branch is renamed or migrated.

Output keys (`PHASE`, `SLUG`, `ITERATION`, `NEXT`, `NEXT_KIND`, the `PLAN_*`
keys) and every result code stay as they are; callers that only pass `NEXT` to
`git-new-branch` need no change.

Rejected: `<slug>/iter-<N>-<phase>` with no prefix — a branch named after a bare
slug blocks every work branch of that plan; phase-first with a shared counter
(`impl/foo/iter-3`) — the phase prefix reads as a per-phase count; still
counting v1 names so plans in flight keep their sequence — the maintainer chose
a clean break over carrying two shapes.

## Implementation Steps

### Task 1: The script names, parses, and counts the v2 shape

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py`,
`.agents/plugins/agentdev/tests/test_iwe_branch_name_parse.py`,
`.agents/plugins/agentdev/tests/test_iwe_branch_name_next.py`

- [x] `parse` splits `iwe/<slug>/iter-<N>-<phase>` and reports
  `NOT_A_WORK_BRANCH` for v1 names (`impl/foo/iter-1`), for
  `iwe/foo/iter-0-impl`, `iwe/foo/iter-01-impl`, `iwe/foo/iter-1`, and
  `iwe/foo/iter-1-review`; the docstring, usage text, and error message name the
  v2 shape
  - **Evidence:** commit 14aec99; `test_parse_splits_a_work_branch` and
    `test_parse_rejects_a_name_off_the_shape` in `test_iwe_branch_name_parse.py`
    pass
- [x] `next` prints `NEXT=iwe/<slug>/iter-<N>-<phase>`, counts used iterations
  of both phases for the slug, ignores v1 names, and searches pull requests with
  `head:iwe/<slug>/`; tests cover a `ship` name following an `impl` iteration
  (`iwe/foo/iter-2-impl` used → `next --phase ship` gives `iwe/foo/iter-3-ship`)
  and v1 names being ignored
  - **Evidence:** commit 14aec99; `test_next_counts_both_phases`,
    `test_next_ignores_names_off_the_shape`, and
    `test_next_starts_at_iteration_one` (the `head:iwe/<slug>/` search) in
    `test_iwe_branch_name_next.py` pass
- [x] `uv run pytest .agents/plugins/agentdev/tests/test_iwe_branch_name_parse.py .agents/plugins/agentdev/tests/test_iwe_branch_name_next.py .agents/plugins/agentdev/tests/test_iwe_branch_name_plan_state.py`
  passes
  - **Evidence:** commit 14aec99; the three files pass, 55 tests

### Task 2: Skill and implementer text name the v2 shape

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-branch-name/SKILL.md`,
`.agents/plugins/agentdev/agents/iwe-implementer.agent.md`,
`.agents/plugins/agentdev/README.md`, `docs/knowledge/AGENTS.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/AGENTS.md`

- [x] `SKILL.md` frontmatter description, `## The Name Shape`, the `next`
  bullet, and the `NOT_A_WORK_BRANCH` row describe
  `iwe/<slug>/iter-<N>-<phase>`, the shared counter, and v1 names as not work
  branches; the "Never rename or migrate" rule stays
  - **Evidence:** commit 2a5aa41 rewrites the description, `## The Name Shape`,
    the `parse` and `next` bullets, and the `NOT_A_WORK_BRANCH` row; the "Never
    rename or migrate" rule is unchanged
- [x] `iwe-implementer.agent.md` step 4 still names the branch through
  `next <plan-key> --phase impl`; any wording that implies a per-phase count is
  removed
  - **Evidence:** step 4 at commit 2a5aa41 still calls
    `/agentdev:iwe-branch-name next <plan-key> --phase impl` and has no
    per-phase count wording, so the file needed no change
- [x] The `/agentdev:iwe-branch-name` rows in
  `.agents/plugins/agentdev/README.md`, `docs/knowledge/AGENTS.md`, and
  `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/AGENTS.md`
  say the skill names a plan's next `iwe/` iteration branch
  - **Evidence:** commits 2a5aa41 and 7b3d305 (the bootstrap asset re-synced to
    its source byte for byte)
- [x] `validate_agent_files` reports 0 errors for the catalog
  - **Evidence:** commit 7b3d305;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reports 68/68 skills valid, 0 errors

### Task 3: End-to-end fixtures expect the v2 name

**Files:** Modify: `scripts/e2e/iwe-workflows/scenarios.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py`,
`scripts/tests/test_e2e_iwe_workflows_clone.py`

- [x] `BRANCH_WORK` is `iwe/e2e-branch/iter-1-impl`; both e2e tests assert
  `head:iwe/e2e-branch/` in the recorded `gh` calls; the clone test expects
  `NEXT=iwe/e2e-branch/iter-1-impl`
  - **Evidence:** commit 0694aca
- [x] `uv run pytest scripts/tests/test_e2e_iwe_workflows_clone.py` passes
  - **Evidence:** commit 0694aca; 8 tests pass

### Task 4: The live start-on-main e2e run ends on the v2 branch

**Files:** none

- [x] The Claude Code and OpenCode start-on-main Implement e2e tests pass,
  ending on `iwe/e2e-branch/iter-1-impl` pushed to the fixture remote
  - **Evidence:** at commit 6a46988,
    `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_implement_on_main scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_implement_on_main`
    — 2 passed

### Task 5: Project memory names the v2 shape

**Files:** Modify: `docs/knowledge/data/features/iwe-branch-name.md`,
`docs/knowledge/data/backlog/pr-merge-post-merge-cleanup.md`,
`docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md`

- [x] The feature's description and `## Behaviour` describe the v2 shape and the
  shared counter, and its edge cases say v1 names are ignored
  - **Evidence:** commit f3ad06e
- [x] The backlog item's dependency sentence and diagram use
  `iwe/<slug>/iter-N-ship` and `iwe/<slug>/iter-N-impl`
  - **Evidence:** commit f3ad06e, which also updates the nesting constraint's
    `iwe/<slug>/iter-1-ship` example
- [x] The codebase map's `iwe-branch-name.py` paragraph is refreshed through
  `/agentdev:iwe-map`; `iwe normalize` and `iwe schema validate` pass
  - **Evidence:** commit f3ad06e refreshes the five stale map docs; after it,
    `stale-map-docs.py` ends `RESULT=SUCCESS` and `iwe schema validate` passes

## Spec changes

[iwe-branch-name](../../../../openspec/specs/iwe-branch-name/spec.md):

``` markdown
## MODIFIED Requirements

### Requirement: Plan work branches carry phase, slug, and iteration

The iwe-branch-name skill SHALL name a plan's work branch
`iwe/<slug>/iter-<N>-<phase>`, where `slug` is the plan key's file name without
its `YYYYMMDD-` prefix, `N` is a positive integer, and `phase` is `impl` or
`ship`, and SHALL always include the `iwe/` prefix and the iteration suffix.

#### Scenario: First implementation branch

- **WHEN** no branch or pull request named `iwe/foo/iter-<N>-<phase>` exists for
  plan `data/plans/20261020-foo`
- **THEN** the next `impl` name is `iwe/foo/iter-1-impl`

#### Scenario: A name off the shape is not parsed

- **WHEN** `parse` receives `foo`, `impl/foo/iter-1`, `iwe/foo/iter-1`, or
  `iwe/foo/iter-0-impl`
- **THEN** it reports `NOT_A_WORK_BRANCH` and no phase, slug, or iteration

### Requirement: The next iteration follows every iteration already used

The skill SHALL compute the next `N` for a slug as one more than the highest
`N` of either phase among local branches, the remote's branches, and the pull
requests in any state of the repository the remote's URL names, counting only
names that match the shape exactly, and SHALL fail with `GH_UNAVAILABLE` rather
than answer when those pull requests cannot be read.

#### Scenario: A merged iteration's branch was deleted

- **WHEN** `iwe/foo/iter-2-impl` survives only as a merged pull request's head
  and `iwe/foo/iter-1-impl` exists locally
- **THEN** the next `impl` name is `iwe/foo/iter-3-impl`

#### Scenario: Iterations run in order across phases

- **WHEN** `iwe/foo/iter-2-impl` was used before
- **THEN** the next `ship` name is `iwe/foo/iter-3-ship`

#### Scenario: Names from before the iwe/ shape are not counted

- **WHEN** only `impl/foo/iter-4` exists for plan `foo`
- **THEN** the next `impl` name is `iwe/foo/iter-1-impl`

#### Scenario: gh cannot answer

- **WHEN** `gh` is missing or unauthenticated, or the remote's URL names no
  repository `gh` can read
- **THEN** `next` reports `GH_UNAVAILABLE` and no name

#### Scenario: Pull requests come from the remote's repository

- **WHEN** `next` runs with `--remote upstream`
- **THEN** it reads pull requests of the repository `upstream`'s URL names, not
  of `gh`'s default repository

### Requirement: The next name follows the plan's state

Without an explicit phase, `next` SHALL name the remote default branch for a
`done`, `cancelled`, or `missing` plan, the next `ship` iteration for a
`complete` plan, and the next `impl` iteration for an `incomplete` plan; with
`--phase`, it SHALL name the next iteration of that phase without reading the
plan. The skill SHALL NOT create, switch, or delete any branch.

#### Scenario: A complete plan moves to shipping

- **WHEN** plan `foo` is `complete` and `iwe/foo/iter-1-ship` was used before
- **THEN** `next foo` reports `NEXT=iwe/foo/iter-2-ship`

#### Scenario: A shipped plan returns to the default branch

- **WHEN** plan `foo` is `done`
- **THEN** `next foo` reports `NEXT_KIND=default` and the default branch's name
```

The requirement "Plan state is read at the remote default branch" is unchanged.

[iwe-workflow-skills](../../../../openspec/specs/iwe-workflow-skills/spec.md):
the scenario "Implementation starts on main" SHALL read "**THEN** it creates
branch `iwe/<slug>/iter-<N>-impl`, with `N` from iwe-branch-name, through
git-new-branch before executing any task"; the requirement's SHALL statement is
unchanged.

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_iwe_branch_name_parse.py .agents/plugins/agentdev/tests/test_iwe_branch_name_next.py .agents/plugins/agentdev/tests/test_iwe_branch_name_plan_state.py scripts/tests/test_e2e_iwe_workflows_clone.py`
- The Claude Code and OpenCode start-on-main e2e tests in
  `scripts/e2e/iwe-workflows/`.
- `grep -rnE '(impl|ship)/(<|\{|e2e|foo)|<impl\|ship>|impl/. or .ship/' .agents scripts docs/knowledge`
  finds no v1 shape outside done plans, the log, and this plan's rejected
  alternatives.
- `validate_agent_files` reports 0 errors; `iwe normalize` and
  `iwe schema validate` pass.

## Out of scope

- Renaming, deleting, or migrating any existing `impl/…` or `ship/…` branch.
- Reading v1 names for the count, or accepting them in `parse`.
- The post-merge cleanup itself
  ([backlog](../backlog/pr-merge-post-merge-cleanup.md)); only its stated name
  shape changes here.
- Plan-state classification, result codes, and output keys.

## Key references

- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py::USAGE`
  — module docstring naming the shape
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py::USAGE`
  — `NOT_A_WORK_BRANCH` row of the usage table
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py::WORK_BRANCH`
  — `WORK_BRANCH` regex
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py::parse_work_branch`
  — `parse_work_branch` (group order follows the regex)
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py::pull_request_heads`
  — `pull_request_heads`, `head:` search
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py::next_iteration`
  — `next_iteration`, the `(phase, slug)` filter
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py::run_next`
  — `run_next` printing `NEXT`
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py::run_parse`
  — `run_parse` error message
- `.agents/plugins/agentdev/tests/test_iwe_branch_name_parse.py › "iwe/focus-timer/iter-1-impl', 'impl', 'focus-timer', '1')"`
  — accepted and rejected names
- `.agents/plugins/agentdev/tests/test_iwe_branch_name_next.py::test_next_ignores_names_off_the_shape`
  — `test_next_ignores_names_off_the_shape_and_the_other_phase`, whose
  other-phase expectation inverts
- `.agents/plugins/agentdev/tests/test_iwe_branch_name_next.py::test_next_with_phase_does_not_need_the_plan`
  — `test_next_follows_the_plan_state`
- `.agents/plugins/agentdev/skills/iwe-branch-name/SKILL.md › "Name the next work branch for an IWE plan —"`
  — description, `## The Name Shape`, and the `NOT_A_WORK_BRANCH` row
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#steps › "/agentdev:iwe-branch-name next <plan-key> --phase impl"`
  — step 4 `next` call
- `.agents/plugins/agentdev/README.md#knowledge-graph-workflow-iwe › "iteration branch. |"`,
  `docs/knowledge/AGENTS.md#workspace-skills › "iteration branch, never creates it |"`,
  `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/AGENTS.md#workspace-skills › "iteration branch, never creates it |"`
  — skill table rows naming `impl/` or `ship/`
- `scripts/e2e/iwe-workflows/scenarios.py::BRANCH_WORK` — `BRANCH_WORK`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_implement_on_main`
  and
  `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_implement_on_main`
  — `head:` assertions
- `scripts/tests/test_e2e_iwe_workflows_clone.py::test_main_clone_has_a_remote_and_a_stub_gh`
  — `NEXT` assertion
- `docs/knowledge/data/spec/iwe-workflow-skills.md#scenario-implementation-starts-on-main › "iwe/<slug>/iter-<N>-impl"`
  — "Implementation starts on main" scenario
- `docs/knowledge/data/backlog/pr-merge-post-merge-cleanup.md#clean-up-the-local-checkout-after-pr-merge › "and the lookup of a plan's state at the"`
  and its stated name shape
- `docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md#how-it-works › "names a plan's work branches"`
  — map paragraph
