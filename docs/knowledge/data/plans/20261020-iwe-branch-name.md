---
type: plan
created: 2026-10-20
description: Add the iwe-branch-name skill, which names a plan's work branches <impl|ship>/<plan-slug>/iteration-<N> and reads plan state at the remote default branch, and have the implementer name its first branch through it.
release:
- features/iwe-branch-name
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/git-new-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/skill-scripts/SKILL.md
- resource: .agents/plugins/agentdev/bin/result_codes.py
---

# iwe-branch-name skill

## Context

A plan's work spans several pull requests — one or more for implementation, one
for shipping — and each needs a fresh branch off the default branch. This
repository squash-merges and deletes the head branch on merge, so after a merge
nothing on the remote records which iteration comes next, and hand-picked names
drift (`impl-opencode-container-iter2`, `opencode-web-coder-autostart-impl`).
The implementer names its only branch after the bare plan slug
(`iwe-implementer.agent.md` step 4), which leaves no room for a second
iteration.

Feature: [iwe-branch-name](../features/iwe-branch-name.md). The first planned
consumer after the implementer is [Clean up the local checkout after
pr-merge](../backlog/pr-merge-post-merge-cleanup.md), which stays out of this
plan.

## Approach

A new `iwe-branch-name` skill owns the name shape and the lookups behind it,
through one stdlib-only Python script, `agent-code/iwe-branch-name.py`,
following the `skill-scripts` contract through the plugin's
`bin/result_codes.py` (the way `iwe-map`'s `stale-map-docs.py` does). It creates
no branch: callers pass the name to `/agentdev:git-new-branch`.

**Name shape.** `<phase>/<slug>/iteration-<N>`, `phase` ∈ `impl`, `ship`; `slug`
is the plan key's file name without its `YYYYMMDD-` prefix; `N` ≥ 1. The suffix
is always present. Git cannot hold a ref beside another it would nest under
(`ship/foo` blocks `ship/foo/iteration-2`), and a name that always ends in
`iteration-<N>` is never a path prefix of another.

**Subcommands.**

- `parse <branch>` — splits a name into `PHASE`, `SLUG`, `ITERATION`; a name off
  the shape (including the pre-existing bare `<slug>` form) is
  `NOT_A_WORK_BRANCH`.
- `plan-state <plan-key|slug> [--remote <name>]` — fetches the remote's default
  branch, finds `data/plans/*-<slug>.md` in that tree, and reports `PLAN_KEY`
  and `PLAN_STATE`: `missing`, `cancelled`, `done`, `complete` (no `stage`,
  every task checkbox under `## Implementation Steps` ticked), or `incomplete`.
- `next <plan-key|slug> [--phase impl|ship] [--remote <name>]` — with `--phase`,
  the next name of that phase without reading the plan; without it, the phase
  follows `plan-state`: `complete` → `ship`, `incomplete` → `impl`,
  `done`/`cancelled`/`missing` → the default branch. Reports `NEXT`, `NEXT_KIND`
  (`default`, `impl`, `ship`), and `ITERATION` for a work branch.

**Next iteration** is one more than the highest `N` for that phase and slug
across local branches (`git for-each-ref`), the remote's branches
(`git ls-remote --heads`), and the repository's pull requests in any state
(`gh pr list --state all --search "head:<phase>/<slug>/"`), keeping only head
names that match the shape exactly. When `gh` cannot answer, `next` fails with
`GH_UNAVAILABLE` rather than return a number a merged PR may already hold.

**Library path and default branch** resolve as they do elsewhere in the plugin:
`[workspace].path` from `.iwe/config.toml` (as `stale-map-docs.py` reads it),
and the remote default branch through the shared `bin/git-default-branch.sh`
(`remote_default_branch`).

**Implementer.** Step 4 keeps its "only on the default branch" rule and names
the branch with `next <plan-key> --phase impl`. It passes the phase because a
plan written on the current checkout may not be on the remote default branch
yet, where `plan-state` would read it as `missing`.

Rejected: deriving `N` from the current branch alone — it has no answer on the
default branch, where the implementer starts, and misses iterations made in
other checkouts; tolerating a missing `gh` with a lower bound — a reused name
ends in `BRANCH_EXISTS` at best and a PR history mixed across iterations at
worst; letting the skill create the branch — branch creation stays in one place,
`git-new-branch`; a bare `ship/<slug>` for the first ship iteration — it nests
under nothing but blocks `ship/<slug>/iteration-2`.

Assumptions: one script with subcommands rather than one script per lookup (they
share fetch, plan resolution, and the shape regex); results are `SUCCESS 0`,
`SCRIPT_FAILURE 1`, `PREFLIGHT_ERROR 2`, `NOT_A_WORK_BRANCH 3`,
`AMBIGUOUS_PLAN 4`, `FETCH_FAILED 5`, `GH_UNAVAILABLE 6`, plus the shared signal
results.

## Implementation Steps

### Task 1: parse and plan-state, with tests

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py`,
`.agents/plugins/agentdev/tests/test_iwe_branch_name_parse.py`,
`.agents/plugins/agentdev/tests/test_iwe_branch_name_plan_state.py`

- [x] `parse` and `plan-state` follow the `skill-scripts` contract through
  `bin/result_codes.py` — `RESULT=` last on stdout, `--help` printing the
  results table with the codes listed in `## Approach` — and import only the
  standard library
  - **Evidence:** `test_help_prints_the_results_table`,
    `test_usage_error_is_a_preflight_error`, and
    `test_script_imports_only_the_standard_library` in
    `test_iwe_branch_name_parse.py` passed on 2026-10-25, in the commit that
    adds the script.
- [x] `parse` tests cover `impl` and `ship` names, multi-digit iterations, and
  `NOT_A_WORK_BRANCH` for a bare slug, `iteration-0`, a missing suffix, and an
  unknown phase
  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests/test_iwe_branch_name_parse.py`
    passed on 2026-10-25 (`test_parse_splits_a_work_branch`,
    `test_parse_rejects_a_name_off_the_shape`).
- [x] `plan-state` tests, against a local bare-repository remote with made-up
  plans, cover each of `missing`, `cancelled`, `done`, `complete`, and
  `incomplete`; a plan changed only in the working tree being read from the
  remote default branch; lookup by plan key and by slug; `AMBIGUOUS_PLAN` for a
  slug two dated plans share; `FETCH_FAILED` for an unreachable remote
  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests/test_iwe_branch_name_plan_state.py`
    passed on 2026-10-25.

### Task 2: next, with tests

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py`;
Create: `.agents/plugins/agentdev/tests/test_iwe_branch_name_next.py`

- [x] `next` computes the iteration from local branches, remote branches, and a
  `gh pr list` stub, and picks the phase from `--phase` or from `plan-state`
  - **Evidence:** `test_next_counts_each_source` and
    `test_next_follows_the_plan_state` in `test_iwe_branch_name_next.py` passed
    on 2026-10-25; `next 20261020-iwe-branch-name --phase impl` in this
    repository printed `NEXT=impl/iwe-branch-name/iteration-1`.
- [x] Tests cover: `iteration-1` when nothing exists; the highest of a local, a
  remote-only, and a PR-only iteration plus one; names off the shape and the
  other phase ignored; `--phase` used for a plan missing on the remote; each
  plan state mapped to its `NEXT_KIND`; `GH_UNAVAILABLE` for a missing and for
  an unauthenticated `gh`
  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests/test_iwe_branch_name_next.py`
    passed on 2026-10-25.

### Task 3: Skill definition

**Files:** Create: `.agents/plugins/agentdev/skills/iwe-branch-name/SKILL.md`

- [x] SKILL.md with a discovery description, the name shape and why the suffix
  is always present, the three subcommands, the `RESULT`-keyed decision table,
  and the rule that callers create the branch through `/agentdev:git-new-branch`
  - **Evidence:**
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reported 63/63 skills valid, 0 errors, on 2026-10-25.

### Task 4: Catalog listings

**Files:** Modify: `.agents/plugins/agentdev/README.md`, `README.md`,
`docs/knowledge/AGENTS.md`

- [x] `iwe-branch-name` rows in the plugin README's IWE table, the root README's
  skill table, and the `## Workspace skills` table of the workspace operating
  manual
  - **Evidence:** the rows are at `.agents/plugins/agentdev/README.md:152`,
    `README.md:296`, and `docs/knowledge/AGENTS.md:227` as of 2026-10-25;
    `prettier` and `iwe normalize` passed in the commit that adds them.

### Task 5: Implementer names its branch through iwe-branch-name

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [x] Step 4 names the work branch with
  `/agentdev:iwe-branch-name next <plan-key> --phase impl` and creates it
  through `/agentdev:git-new-branch`; on any other branch it still continues
  where it is
  - **Evidence:** `iwe-implementer.agent.md` step 4 as of 2026-10-25;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reported 0 errors.

### Task 6: git-new-branch defers plan branch names

**Files:** Modify: `.agents/plugins/agentdev/skills/git-new-branch/SKILL.md`

- [x] The "Choose the Name" row for an IWE plan points at
  `/agentdev:iwe-branch-name` instead of suggesting `<slug>`
  - **Evidence:** `git-new-branch/SKILL.md` "Choose the Name" table as of
    2026-10-25; `prettier` and `validate_agent_files` passed.

### Task 7: Refresh the codebase map

**Files:** Modify: the `data/codebase/` documents `agent-code/stale-map-docs.py`
reports stale after Tasks 1–6

- [x] `/agentdev:iwe-map` refresh mode re-reads every map document the new skill
  and the edited files make stale, and `stale-map-docs.py` reports none
  - **Evidence:** `stale-map-docs.py` reported `RESULT=SUCCESS` with 28 docs
    fresh on 2026-10-25, after refreshing the four docs Tasks 1–6 made stale, in
    the commit that refreshes them.

## Spec changes

`data/spec/iwe-branch-name` (new):

``` markdown
## ADDED Requirements

### Requirement: Plan work branches carry phase, slug, and iteration

The iwe-branch-name skill SHALL name a plan's work branch
`<phase>/<slug>/iteration-<N>`, where `phase` is `impl` or `ship`, `slug` is the
plan key's file name without its `YYYYMMDD-` prefix, and `N` is a positive
integer, and SHALL always include the iteration suffix.

#### Scenario: First implementation branch

- **WHEN** no branch or pull request of phase `impl` exists for plan
  `data/plans/20261020-foo`
- **THEN** the next `impl` name is `impl/foo/iteration-1`

#### Scenario: A name off the shape is not parsed

- **WHEN** `parse` receives `foo`, `impl/foo`, or `impl/foo/iteration-0`
- **THEN** it reports `NOT_A_WORK_BRANCH` and no phase, slug, or iteration

### Requirement: The next iteration follows every iteration already used

The skill SHALL compute the next `N` for a phase and slug as one more than the
highest `N` among local branches, the remote's branches, and the repository's
pull requests in any state whose names match the shape exactly, and SHALL fail
with `GH_UNAVAILABLE` rather than answer when the pull requests cannot be read.

#### Scenario: A merged iteration's branch was deleted

- **WHEN** `impl/foo/iteration-2` survives only as a merged pull request's head
  and `impl/foo/iteration-1` exists locally
- **THEN** the next `impl` name is `impl/foo/iteration-3`

#### Scenario: gh cannot answer

- **WHEN** `gh` is missing or unauthenticated
- **THEN** `next` reports `GH_UNAVAILABLE` and no name

### Requirement: Plan state is read at the remote default branch

The skill SHALL fetch the remote's default branch and read the plan there,
reporting `missing`, `cancelled`, `done`, `complete` when the plan has no
`stage` and every task checkbox is ticked, or `incomplete` otherwise, and SHALL
refuse a slug that matches more than one plan with `AMBIGUOUS_PLAN`.

#### Scenario: Local edits do not count

- **WHEN** a plan's last checkbox is ticked only in the working tree
- **THEN** `plan-state` reports `incomplete`

#### Scenario: Two plans share a slug

- **WHEN** `data/plans/20261001-foo` and `data/plans/20261020-foo` both exist at
  the remote default branch
- **THEN** a lookup by slug `foo` reports `AMBIGUOUS_PLAN`

### Requirement: The next name follows the plan's state

Without an explicit phase, `next` SHALL name the remote default branch for a
`done`, `cancelled`, or `missing` plan, the next `ship` iteration for a
`complete` plan, and the next `impl` iteration for an `incomplete` plan; with
`--phase`, it SHALL name the next iteration of that phase without reading the
plan. The skill SHALL NOT create, switch, or delete any branch.

#### Scenario: A complete plan moves to shipping

- **WHEN** plan `foo` is `complete` and `ship/foo/iteration-1` was used before
- **THEN** `next foo` reports `NEXT=ship/foo/iteration-2`

#### Scenario: A shipped plan returns to the default branch

- **WHEN** plan `foo` is `done`
- **THEN** `next foo` reports `NEXT_KIND=default` and the default branch's name
```

[iwe-workflow-skills](../spec/iwe-workflow-skills.md):

``` markdown
## MODIFIED Requirements

### Requirement: Implement starts work on its own branch

The Implement skill SHALL, when the checkout is on `main` or `master`, create
the work branch through the git-new-branch skill, named by the iwe-branch-name
skill's next `impl` iteration for the plan, before executing the first task,
and SHALL continue on the current branch otherwise.

#### Scenario: Implementation starts on main

- **WHEN** Implement begins plan `data/plans/<date>-<slug>` with `main` checked
  out
- **THEN** it creates branch `impl/<slug>/iteration-<N>`, with `N` from
  iwe-branch-name, through git-new-branch before executing any task

#### Scenario: Implementation starts on a feature branch

- **WHEN** Implement begins with a branch other than `main` or `master` checked
  out
- **THEN** it executes the plan on that branch without creating another
```

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_iwe_branch_name_parse.py .agents/plugins/agentdev/tests/test_iwe_branch_name_plan_state.py .agents/plugins/agentdev/tests/test_iwe_branch_name_next.py`
  passes; then `uv run pytest .agents/plugins/agentdev/tests` passes.
- `iwe-branch-name.py --help` prints the results table; `python-lint-check.sh`
  is clean on the script and tests.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  reports 0 errors.
- In this repository,
  `iwe-branch-name.py next 20261020-iwe-branch-name --phase impl` prints a name
  of the shape, and `plan-state` on a shipped plan reports `done`.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- pr-merge's post-merge cleanup — [backlog
  task](../backlog/pr-merge-post-merge-cleanup.md).
- pr-merge-stack's cleanup — [backlog
  task](../backlog/pr-merge-stack-post-merge-cleanup.md).
- Renaming or migrating branches named before this shape.
- Creating `ship/` branches from the ship skills; iwe-ship works on the current
  checkout as it does today.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:48` — step 4, "Start
  on a work branch"
- `.agents/plugins/agentdev/skills/git-new-branch/SKILL.md:36` — "Choose the
  Name"; table at line 41, IWE plan row at line 43
- `.agents/plugins/agentdev/bin/result_codes.py:89` — `run`
- `.agents/plugins/agentdev/bin/git-default-branch.sh:12` —
  `remote_default_branch`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:21` —
  plugin `bin/` import; `library_from_config` at line 446
- `.agents/plugins/agentdev/tests/conftest.py:22` — `plugin_root`;
  `plugin_tmp_path` at line 28
- `.agents/plugins/agentdev/tests/git_fixtures.py:37` — `stub_gh`
- `.agents/plugins/agentdev/README.md:143` — IWE skills table
- `README.md:298` — skill table, `iwe-weekly` row
- `docs/knowledge/AGENTS.md:229` — `## Workspace skills` table, `iwe-weekly` row
- `docs/knowledge/data/spec/iwe-workflow-skills.md:229` — "Implement starts work
  on its own branch"
