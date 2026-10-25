---
type: plan
created: 2026-10-20
description: Add the iwe-branch-name skill, which names a plan's work branches <impl|ship>/<plan-slug>/iteration-<N> and reads plan state at the remote default branch, and have the implementer name its first branch through it.
release:
- features/iwe-branch-name
generated:
  by: claude-code/opus-5.5
  at: 2026-10-25T00:00:00Z
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
drift (`impl-<slug>-iter2`, `<slug>-impl`). A branch named after the bare plan
slug leaves no room for a second iteration.

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

**Name shape.** `<phase>/<slug>/iter-<N>`, `phase` ∈ `impl`, `ship`; `slug` is
the plan key's file name without its `YYYYMMDD-` prefix; `N` ≥ 1. The suffix is
always present. Git cannot hold a ref beside another it would nest under
(`ship/foo` blocks `ship/foo/iter-2`), and a name that always ends in `iter-<N>`
is never a path prefix of another. The suffix is kept short because the slug
already makes up most of the name.

**Subcommands.**

- `parse <branch>` — splits a name into `PHASE`, `SLUG`, `ITERATION`; a name off
  the shape (including the pre-existing bare `<slug>` form) is
  `NOT_A_WORK_BRANCH`.
- `plan-state <plan-key|slug> [--remote <name>]` — fetches the remote's default
  branch, finds `data/plans/*-<slug>.md` in that tree, and reports `PLAN_KEY`
  and `PLAN_STATE`: `missing`, `cancelled`, `done`, `complete` (no `stage`, at
  least one task checkbox, and every task checkbox under
  `## Implementation Steps` or the older `## Tasks` heading ticked), or
  `incomplete`. A plan with no task checkboxes is `incomplete`, so `next` never
  routes it to `ship`. The two headings are the task sections the repository's
  plan-checkbox gate already reads.
- `next <plan-key|slug> [--phase impl|ship] [--remote <name>]` — with `--phase`,
  the next name of that phase without reading the plan; without it, the phase
  follows `plan-state`: `complete` → `ship`, `incomplete` → `impl`,
  `done`/`cancelled`/`missing` → the default branch. Reports `NEXT`, `NEXT_KIND`
  (`default`, `impl`, `ship`), and `ITERATION` for a work branch.

**Next iteration** is one more than the highest `N` for that phase and slug
across local branches (`git for-each-ref`), the remote's branches
(`git ls-remote --heads`), and the remote's pull requests in any state
(`gh pr list --repo <remote URL> --state all --search "head:<phase>/<slug>/"`),
keeping only head names that match the shape exactly. GitHub's `head:` search
matches by prefix, and `gh --repo` accepts the remote's HTTPS, SSH, or scp-style
URL as is, so branches and pull requests always come from the same repository; a
URL that names no GitHub repository fails the query. When `gh` cannot answer,
`next` fails with `GH_UNAVAILABLE` rather than return a number a merged PR may
already hold.

**Library path and default branch** resolve as they do elsewhere in the plugin:
`[workspace].path` from `.iwe/config.toml` (as `stale-map-docs.py` reads it),
and the remote default branch through the shared `bin/git-default-branch.sh`
(`remote_default_branch`).

**Implementer.** Step 4 keeps its "only on the default branch" rule and names
the branch with `next <plan-key> --phase impl`. It passes the phase because a
plan written on the current checkout may not be on the remote default branch
yet, where `plan-state` would read it as `missing`.

**End to end.** The agent-owned e2e suite (`scripts/e2e/iwe-workflows/`) covers
both Implement scenarios. A new `main_clone` fixture checks out `main` in a
clone backed by a bare remote beside it, with `origin/HEAD` set and a stub `gh`
first on the agent's `PATH` that lists no pull requests; Implement of a new
trivial fixture plan, `data/plans/20261025-e2e-branch`, must end on
`impl/e2e-branch/iter-1`, pushed to that remote. The existing `test_implement`,
which runs on the fixture's own `e2e-fixture` branch, also asserts the checkout
stays on that branch and gains no other. The start-on-main case runs on OpenCode
and Claude Code; Codex reads its installed catalog, not the clone's, so it
carries only the stay-put assertion.

Rejected: reusing the greet fixture plan for the start-on-main case — its task
conflicts with its spec outcome by design, so a run may stop before the branch
step and prove nothing; parsing the remote URL into `OWNER/REPO` before calling
`gh` — `gh --repo` already accepts every URL form a GitHub remote uses.

Rejected: deriving `N` from the current branch alone — it has no answer on the
default branch, where the implementer starts, and misses iterations made in
other checkouts; tolerating a missing `gh` with a lower bound — a reused name
ends in `BRANCH_EXISTS` at best and a PR history mixed across iterations at
worst; letting the skill create the branch — branch creation stays in one place,
`git-new-branch`; a bare `ship/<slug>` for the first ship iteration — it nests
under nothing but blocks `ship/<slug>/iter-2`.

Rejected suffixes: `iteration-<N>` — ten characters on every name for no added
meaning; `t<N>` — reads as plan Task N; `take<N>` — implies the previous branch
was discarded, where an iteration builds on the merged one; `v<N>` — reads as a
release version; a bare `<N>` — says nothing about what the number counts; a
flat `<slug>-<N>` — ambiguous beside slugs that end in digits; `pr<N>` and
`#<N>` — read as a pull request number, and `#` starts a shell comment.

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

### Task 8: plan-state reads both task headings and refuses an empty plan

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py`,
`.agents/plugins/agentdev/tests/test_iwe_branch_name_plan_state.py`,
`.agents/plugins/agentdev/tests/test_iwe_branch_name_next.py`

- [x] `task_checkboxes` reads `## Implementation Steps` and `## Tasks`, and
  `classify_plan` reports `incomplete` for a plan with no task checkboxes
  - **Evidence:** `test_plan_state_classifies_the_plan` in
    `test_iwe_branch_name_plan_state.py` passed on 2026-10-25 with the
    `## Tasks` and empty-plan cases.
- [x] `plan-state` tests cover a ticked plan under `## Tasks` as `complete`, an
  unticked one as `incomplete`, and a plan with no task checkboxes as
  `incomplete`; a `next` test shows that plan named `impl`, not `ship`
  - **Evidence:** `uv run pytest` on the three `test_iwe_branch_name_*.py`
    modules passed (46 tests) on 2026-10-25, including
    `test_next_names_impl_for_a_plan_without_tasks`.

### Task 9: next reads pull requests from the remote's repository

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py`,
`.agents/plugins/agentdev/tests/test_iwe_branch_name_next.py`

- [x] `pull_request_heads` passes `--repo <URL of --remote>` to `gh pr list`
  - **Evidence:** `test_next_reads_pull_requests_of_the_remote` passed on
    2026-10-25; in this repository `next 20261020-iwe-branch-name --phase impl`
    still printed `NEXT=impl/iwe-branch-name/iteration-1` through the real `gh`.
- [x] `next` tests show the stub `gh` receiving `--repo` with the URL of the
  remote `--remote` names, for `origin` and for a second remote
  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests/test_iwe_branch_name_next.py`
    passed (19 tests) on 2026-10-25, with `origin` and `upstream` cases.

### Task 10: Skill text states the task-heading, empty-plan, and remote-repository rules

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-branch-name/SKILL.md`,
the `--help` text in
`.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py`

- [x] SKILL.md states the `complete` definition with both headings and the
  empty-plan rule, and that pull requests come from the `--remote` repository
  - **Evidence:** `validate_agent_files` reported 0 errors and `prettier` passed
    on 2026-10-25; `test_iwe_branch_name_parse.py` (help table) passed.

### Task 11: e2e clone on main with a remote and a stub gh

**Files:** Create:
`scripts/e2e/iwe-workflows/fixtures/plans/20261025-e2e-branch.md`,
`scripts/e2e/iwe-workflows/fixtures/bin/gh`; Modify:
`scripts/e2e/iwe-workflows/clone.py`, `scripts/e2e/iwe-workflows/conftest.py`,
`scripts/e2e/iwe-workflows/harness_opencode.py`,
`scripts/e2e/iwe-workflows/harness_claude.py`,
`scripts/tests/test_e2e_iwe_workflows_clone.py`

- [x] The fixture repository carries the active `e2e-branch` fixture plan, whose
  one task writes `e2e/branch.txt`, and `test_e2e_iwe_workflows_clone.py` passes
  with it listed among the fixture plans
  - **Evidence:** `test_fixtures_are_the_only_active_plans` passed on 2026-10-25
    with `FIXTURE_PLANS` listing `plans/20261025-e2e-branch.md`.
- [x] A `main_clone` fixture provides a clone on `main` whose `origin` is a bare
  repository beside it holding `main`, with `origin/HEAD` set, and whose agent
  `PATH` starts with a stub `gh` that answers `pr list` with no pull requests;
  an offline test in `test_e2e_iwe_workflows_clone.py` pins that layout
  - **Evidence:** `test_main_clone_has_a_remote_and_a_stub_gh` passed on
    2026-10-25, running the clone's own `iwe-branch-name.py next` through the
    stub to `NEXT=impl/e2e-branch/iteration-1`;
    `uv run pytest scripts/tests/test_e2e_iwe_workflows_clone.py scripts/tests/test_e2e_live_gate.py`
    passed (31 tests).
- [x] The OpenCode and Claude Code harnesses run the agent with that `PATH`, and
  Claude Code may run the catalog's bundled skill scripts without a prompt
  - **Evidence:** `harness_opencode.isolated_env` and
    `harness_claude.run_claude` take the PATH from `Clone.agent_path`, and
    `allowed_tools` allows the catalog's skill scripts by relative,
    `./`-relative, and absolute path, as of 2026-10-25;
    `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py -k implement`
    passed both tests on 2026-10-25 in the commit that adds the relative forms.

### Task 12: e2e scenarios for both Implement branch rules

**Files:** Modify: `scripts/e2e/iwe-workflows/scenarios.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_codex.py`

- [x] OpenCode and Claude Code each have a `test_implement_on_main` that runs
  Implement of `data/plans/20261025-e2e-branch` in `main_clone` and asserts the
  checkout ends on `impl/e2e-branch/iteration-1` and that branch exists on the
  bare remote
  - **Evidence:** `test_implement_on_main` in `test_iwe_workflows_opencode.py`
    and `test_iwe_workflows_claude.py` as of 2026-10-25; `python-lint-check.sh`
    clean and `uv run pytest scripts/e2e` without `E2E_RUN_LIVE` collected and
    skipped all 18 tests. The live result is Task 13.
- [x] `test_implement` on all three harnesses also asserts the checkout is still
  on `e2e-fixture` and no local branch was added
  - **Evidence:** `test_implement` in all three `test_iwe_workflows_*.py`
    modules asserts `branch() == FIXTURE_BRANCH` and
    `local_branches() == [FIXTURE_BRANCH]` as of 2026-10-25; lint clean.

### Task 13: Live e2e run

**Files:** none

- [x] `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows -k "implement" -n 3`
  passes on OpenCode and Claude Code, and the Codex `test_implement` passes or
  is skipped by its own catalog check
  - **Evidence:** on 2026-10-25 the live run passed OpenCode `test_implement`
    and `test_implement_on_main`; Claude Code's two passed with `6e5ec3c`. Codex
    `test_implement` was reported passing by the user from the checkout
    `/workspaces/agent-devcontainer-wortree-3` after
    `reinstall-agentdev-codex.sh`; that run's commit was not recorded.

### Task 14: Refresh the codebase map again

**Files:** Modify: the `data/codebase/` documents `agent-code/stale-map-docs.py`
reports stale after Tasks 8–12

- [x] `/agentdev:iwe-map` refresh mode re-reads every map document Tasks 8–12
  make stale, and `stale-map-docs.py` reports none
  - **Evidence:** `stale-map-docs.py` reported `RESULT=SUCCESS` on 2026-10-25
    after refreshing the agentdev catalog, skills, and tests docs, in the commit
    that refreshes them.

### Task 15: The script names and parses the iter-<N> suffix

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py`,
`.agents/plugins/agentdev/tests/test_iwe_branch_name_parse.py`,
`.agents/plugins/agentdev/tests/test_iwe_branch_name_next.py`

- [x] `WORK_BRANCH`, the `NEXT=` line, the `--help` text, and the
  `NOT_A_WORK_BRANCH` message use `<phase>/<slug>/iter-<N>`
  - **Evidence:** `iwe-branch-name.py` lines 24, 62, 81, 386, and 448 in the
    commit that renames the suffix; `python-lint-check.sh` clean on 2026-10-25.
- [x] `parse` and `next` tests use `iter-<N>` names, and a `parse` test reports
  `NOT_A_WORK_BRANCH` for an `iteration-<N>` name; a `next` test shows an
  `iteration-<N>` branch is not counted
  - **Evidence:** `uv run pytest` on the three `test_iwe_branch_name_*.py`
    modules passed (49 tests) on 2026-10-25, including the
    `impl/focus-timer/iteration-1` case of
    `test_parse_rejects_a_name_off_the_shape` and the `iteration-3` head in
    `test_next_ignores_names_off_the_shape_and_the_other_phase`.

### Task 16: Skill text names the iter-<N> suffix

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-branch-name/SKILL.md`

- [x] The description, `## The Name Shape`, and the `NOT_A_WORK_BRANCH` row use
  `iter-<N>`, and `validate_agent_files` reports 0 errors
  - **Evidence:**
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reported 63/63 skills valid, 0 errors, on 2026-10-25, in the commit that
    renames the suffix in SKILL.md.

### Task 17: e2e expects iter-1

**Files:** Modify: `scripts/e2e/iwe-workflows/scenarios.py`,
`scripts/tests/test_e2e_iwe_workflows_clone.py`

- [x] `BRANCH_WORK` is `impl/e2e-branch/iter-1`, and
  `test_main_clone_has_a_remote_and_a_stub_gh` expects
  `NEXT=impl/e2e-branch/iter-1`; the offline e2e tests pass
  - **Evidence:**
    `uv run pytest scripts/tests/test_e2e_iwe_workflows_clone.py scripts/tests/test_e2e_live_gate.py`
    passed (31 tests) and `uv run pytest scripts/e2e` without `E2E_RUN_LIVE`
    skipped all 18 on 2026-10-25, in the commit that sets `BRANCH_WORK`.

### Task 18: Live e2e run with iter-1

**Files:** none

- [x] `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows -k "implement" -n 3`
  passes `test_implement_on_main` on OpenCode and Claude Code with the checkout
  ending on `impl/e2e-branch/iter-1`
  - **Evidence:** on 2026-10-25 the live run at `102144e` passed
    `test_implement` and `test_implement_on_main` on Claude Code and, with the
    OpenCode web UI started, on OpenCode.

### Task 19: Refresh the codebase map for the suffix

**Files:** Modify: the `data/codebase/` documents `agent-code/stale-map-docs.py`
reports stale after Tasks 15–17

- [x] `/agentdev:iwe-map` refresh mode re-reads every stale map document,
  including the `iter-<N>` shape in
  `data/codebase/agents/plugins/agentdev/skills`, and `stale-map-docs.py`
  reports none
  - **Evidence:** `stale-map-docs.py` reported `RESULT=SUCCESS` on 2026-10-25
    after refreshing the agentdev catalog, skills, and tests docs, in the commit
    that refreshes them.

## Spec changes

`data/spec/iwe-branch-name` (new):

``` markdown
## ADDED Requirements

### Requirement: Plan work branches carry phase, slug, and iteration

The iwe-branch-name skill SHALL name a plan's work branch
`<phase>/<slug>/iter-<N>`, where `phase` is `impl` or `ship`, `slug` is the
plan key's file name without its `YYYYMMDD-` prefix, and `N` is a positive
integer, and SHALL always include the iteration suffix.

#### Scenario: First implementation branch

- **WHEN** no branch or pull request of phase `impl` exists for plan
  `data/plans/20261020-foo`
- **THEN** the next `impl` name is `impl/foo/iter-1`

#### Scenario: A name off the shape is not parsed

- **WHEN** `parse` receives `foo`, `impl/foo`, or `impl/foo/iter-0`
- **THEN** it reports `NOT_A_WORK_BRANCH` and no phase, slug, or iteration

### Requirement: The next iteration follows every iteration already used

The skill SHALL compute the next `N` for a phase and slug as one more than the
highest `N` among local branches, the remote's branches, and the pull requests
in any state of the repository the remote's URL names, counting only names that
match the shape exactly, and SHALL fail with `GH_UNAVAILABLE` rather than answer
when those pull requests cannot be read.

#### Scenario: A merged iteration's branch was deleted

- **WHEN** `impl/foo/iter-2` survives only as a merged pull request's head
  and `impl/foo/iter-1` exists locally
- **THEN** the next `impl` name is `impl/foo/iter-3`

#### Scenario: gh cannot answer

- **WHEN** `gh` is missing or unauthenticated, or the remote's URL names no
  repository `gh` can read
- **THEN** `next` reports `GH_UNAVAILABLE` and no name

#### Scenario: Pull requests come from the remote's repository

- **WHEN** `next` runs with `--remote upstream`
- **THEN** it reads pull requests of the repository `upstream`'s URL names, not
  of `gh`'s default repository

### Requirement: Plan state is read at the remote default branch

The skill SHALL fetch the remote's default branch and read the plan there,
reporting `missing`, `cancelled`, `done`, `complete` when the plan has no
`stage`, has at least one task checkbox under `## Implementation Steps` or
`## Tasks`, and every such checkbox is ticked, or `incomplete` otherwise, and
SHALL refuse a slug that matches more than one plan with `AMBIGUOUS_PLAN`.

#### Scenario: Local edits do not count

- **WHEN** a plan's last checkbox is ticked only in the working tree
- **THEN** `plan-state` reports `incomplete`

#### Scenario: A plan with no task checkboxes is not complete

- **WHEN** a plan has no `stage` and no task checkbox
- **THEN** `plan-state` reports `incomplete`

#### Scenario: The older task heading counts

- **WHEN** a plan without `stage` lists every task ticked under `## Tasks`
- **THEN** `plan-state` reports `complete`

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

- **WHEN** plan `foo` is `complete` and `ship/foo/iter-1` was used before
- **THEN** `next foo` reports `NEXT=ship/foo/iter-2`

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
- **THEN** it creates branch `impl/<slug>/iter-<N>`, with `N` from
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
- `uv run pytest scripts/tests/test_e2e_iwe_workflows_clone.py scripts/tests/test_e2e_live_gate.py`
  passes, and `uv run pytest scripts/e2e` with `E2E_RUN_LIVE` unset reports
  every test skipped.
- `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows -k "implement" -n 3`
  passes on OpenCode and Claude Code.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- pr-merge's post-merge cleanup — [backlog
  task](../backlog/pr-merge-post-merge-cleanup.md).
- pr-merge-stack's cleanup — [backlog
  task](../backlog/pr-merge-stack-post-merge-cleanup.md).
- Renaming or migrating branches named before this shape.
- Creating `ship/` branches from the ship skills; iwe-ship keeps working on the
  current checkout.
- The start-on-main e2e case on Codex.
- A pull-request lookup for a remote that is not on GitHub.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py:260`
  — `task_checkboxes`; `classify_plan` at line 281, `pull_request_heads` at line
  335; `WORK_BRANCH` at line 81, the `NEXT=` line at line 386, the
  `NOT_A_WORK_BRANCH` message at line 448, and the `--help` shape at lines 24
  and 62
- `.agents/plugins/agentdev/tests/test_iwe_branch_name_parse.py:23` —
  `test_parse_splits_a_work_branch`; `test_parse_rejects_a_name_off_the_shape`
  at line 43
- `.agents/plugins/agentdev/tests/test_iwe_branch_name_next.py:106` —
  `test_next_ignores_names_off_the_shape_and_the_other_phase`
- `.agents/plugins/agentdev/skills/iwe-branch-name/SKILL.md:16` — the name
  shape; description at line 3, `NOT_A_WORK_BRANCH` row at line 78
- `scripts/e2e/iwe-workflows/scenarios.py:11` — `BRANCH_WORK`
- `scripts/tests/test_e2e_iwe_workflows_clone.py:126` —
  `test_main_clone_has_a_remote_and_a_stub_gh`; expected `NEXT=` at line 149
- `docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md:109` — the
  name shape in the codebase map
- `scripts/e2e/iwe-workflows/clone.py:31` — `_ACTIVE_LINKS`; `FIXTURE_PLANS` at
  line 23, `build_fixture_repo` at line 129, `make_clone` at line 233
- `scripts/e2e/iwe-workflows/conftest.py:55` — `base_clone`
- `scripts/e2e/iwe-workflows/harness_opencode.py:60` — `isolated_env`;
  `start_server` at line 265
- `scripts/e2e/iwe-workflows/harness_claude.py:20` — `allowed_tools`;
  `run_claude` at line 112
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:75`,
  `test_iwe_workflows_claude.py:70`, `test_iwe_workflows_codex.py:104` —
  `test_implement`
- `scripts/tests/test_e2e_iwe_workflows_clone.py:43` —
  `test_fixtures_are_the_only_active_plans`
- `docs/knowledge/tests/test_plan_checkboxes.py:31` — `TASK_SECTIONS`, the two
  task headings
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
- `README.md:299` — skill table, `iwe-weekly` row
- `docs/knowledge/AGENTS.md:230` — `## Workspace skills` table, `iwe-weekly` row
- `docs/knowledge/data/spec/iwe-workflow-skills.md:229` — "Implement starts work
  on its own branch"
