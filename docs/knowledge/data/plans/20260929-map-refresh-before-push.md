---
type: plan
created: 2026-09-29
description: Make every agent push run the codebase-map staleness check first and refresh a stale map before the branch leaves the machine, and tell the AI review not to report map staleness, which the CI step already owns.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-29T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-open/scripts/push-branch.sh
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py
- resource: .github/workflows/validate-agent-files.yml
---

# Refresh the codebase map before pushing and keep its staleness out of AI reviews

## Context

The only automatic run of `stale-map-docs.py` is the
`Check codebase map docs against their sources` step of
`validate-agent-files.yml`; `/agentdev:iwe-map` runs it on demand. No skill that
pushes a branch runs it, so a pull request that moves code under a
`data/codebase/` doc reaches CI stale, fails that step, and is repaired by a
second push after an `/agentdev:iwe-map` refresh.

`pr-review` has no exclusion for map staleness, so the AI review can report it
as a finding, restating what the CI step already asserts. That breaks the rule
in [Evidence and outstanding work](../concept/evidence-and-outstanding-work.md):
an artifact asserts only what nothing else already asserts.

## Approach

`push-branch.sh` becomes the single agent push path and runs `stale-map-docs.py`
immediately before it pushes. A stale map stops the push with a new `MAP_STALE`
result; `pr-open` answers it by running the `/agentdev:iwe-map` refresh,
committing through `/agentdev:git-commit`, and rerunning the push. A repository
without an IWE map is not gated: no `.iwe/config.toml` at the repository root,
or `NO_MAP_DOCS` from the check, pushes as before. A `--skip-map-check` flag
lets a push through anyway; skills pass it only when the user asks for that push
explicitly, and CI still fails the stale map.

`update-branch`, `pr-feedback-resolution`, and `pr-merge` push through
`push-branch.sh` instead of a bare `git push`, so the gate covers every agent
push rather than only `pr-open`'s.

The check runs only on the two paths that push (`ACTION=push` and
`ACTION=push-with-upstream`); `ACTION=none` pushes nothing and is not gated.

`pr-review` gains one explicit exclusion beside the existing import-ordering
one, naming the CI step that owns map staleness.

Rejected: a CI job that runs the refresh and pushes a commit onto the pull
request branch. It needs a model call on every pull request and a write-capable
token in CI. Also rejected: a pre-commit or pre-push hook, which detects
staleness but cannot refresh it, since the refresh re-reads code and needs a
model.

`stale-map-docs.py` fingerprints working-tree contents, and a pushing skill can
hold uncommitted changes outside what it pushes. The gate therefore runs the
check inside a temporary detached worktree at the commit being pushed, under
`./.tmp/`, and removes it afterwards, so the verdict describes exactly what
leaves the machine.

## Implementation Steps

### Task 1: Gate `push-branch.sh` on map freshness

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-open/scripts/push-branch.sh` Create:
`.agents/plugins/agentdev/tests/test_push_branch_map_check.py`

- [x] Before each of the two push commands, run the sibling
  `../../iwe-map/scripts/stale-map-docs.py` inside a temporary detached worktree
  at the commit being pushed, remove the worktree afterwards, and print a
  `MAP_CHECK=<fresh|skipped|stale|failed|overridden>` line.
  - **Evidence:** commit "feat(pr-open): gate push-branch.sh on a fresh codebase
    map" (`check_map_freshness`);
    `test_uncommitted_edit_does_not_change_the_verdict` and
    `test_check_worktree_is_removed` pass.
- [x] Declare `6=MAP_STALE` (the check ended `STALE_FOUND`; its per-doc lines go
  to stderr) and `7=MAP_CHECK_FAILED` (`BROKEN_METADATA`, `PREFLIGHT_ERROR` with
  a config present, `SCRIPT_FAILURE`, or a signal); neither pushes.
  - **Evidence:** same commit; `RESULT_CODES` and `--help` list both;
    `test_stale_map_is_not_pushed_to_existing_upstream` and
    `test_stale_map_is_not_pushed_with_upstream` pass.
- [x] Skip the check (`MAP_CHECK=skipped`) when `.iwe/config.toml` is absent
  from the repository root, when the check script is absent, or when it reports
  `NO_MAP_DOCS`.
  - **Evidence:** same commit; the config is looked up in the commit being
    pushed, the root the check runs against;
    `test_repository_without_iwe_config_is_not_gated` passes.
- [x] Add `--skip-map-check`, which pushes without running the check and prints
  `MAP_CHECK=overridden`; document it and both new results in `usage()`.
  - **Evidence:** same commit; `test_skip_map_check_pushes_a_stale_map` passes.
- [x] Tests with a fixture repository that has an IWE library and one map doc:
  fresh map pushes; stale map returns `MAP_STALE` and the remote ref is
  unchanged; `--skip-map-check` pushes a stale map; a repository with no
  `.iwe/config.toml` pushes; `ACTION=none` does not run the check; both push
  paths (existing upstream and `push-with-upstream`) are gated; an uncommitted
  edit under a mapped source does not change the verdict for the pushed commit.
  - **Evidence:** same commit adds `tests/test_push_branch_map_check.py`;
    `uv run pytest .agents/plugins/agentdev/tests`: 112 passed, and 7 of the 8
    new tests fail against the ungated script.

### Task 2: Teach `pr-open` to refresh on `MAP_STALE`

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-open/SKILL.md`

- [x] Step 8 lists `MAP_STALE` and `MAP_CHECK_FAILED` with their actions:
  `MAP_STALE` → run `/agentdev:iwe-map` refresh mode, commit through
  `/agentdev:git-commit`, rerun `push-branch.sh`; `MAP_CHECK_FAILED` → stop and
  report the check's output verbatim.
  - **Evidence:** commit "docs(pr-open): refresh the map on MAP_STALE before
    pushing"; `validate_agent_files`: 56/56 skills valid.
- [x] State that `--skip-map-check` is passed only when the user explicitly asks
  to push with a stale map.
  - **Evidence:** same commit; step 8 states the override rule.

### Task 3: Route the other pushing skills through `push-branch.sh`

**Files:** Modify: `.agents/plugins/agentdev/skills/update-branch/SKILL.md`
Modify: `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md`
Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [x] `update-branch` replaces `git push origin HEAD` with `pr-open`'s
  `push-branch.sh` and its `MAP_STALE` handling.
  - **Evidence:** commit "docs(agentdev): push through push-branch.sh from
    update-branch, pr-feedback-resolution, and pr-merge";
    `validate_agent_files`: 56/56 skills valid.
- [x] `pr-feedback-resolution`'s "Push to PR branch" and `pr-merge`'s two
  commit-and-push instructions name `push-branch.sh` as the push.
  - **Evidence:** same commit; `grep -n "git push"` over the three `SKILL.md`
    files returns nothing.
- [ ] `pr-merge`'s private `pr-merge-worktree/<pr>` branch gets
  `origin/<head-branch>` as its upstream when it is created, so `push-branch.sh`
  pushes to the pull request head and never under the private name.
  - **Evidence:** same commit; `branch --set-upstream-to=origin/<head-branch>`
    follows the worktree's `switch -c`.

### Task 4: Exclude map staleness from the AI review

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [x] Insert this approved line verbatim right after the "IGNORE import
  ordering…" bullet in the Compliance focus list:
  - **Evidence:** commit "docs(pr-review): leave stale codebase-map docs to the
    CI check"; `pr-review/SKILL.md:44` matches the fenced line below byte for
    byte.

``` markdown
- IGNORE stale codebase-map docs (`data/codebase/` docs whose `source_digest` no longer matches their sources) — the `Check codebase map docs against their sources` CI step owns that check
```

### Task 5: Refresh project memory

**Files:** Modify: `docs/knowledge/data/codebase/` docs that `stale-map-docs.py`
reports stale after Tasks 1–4

- [ ] Run the `/agentdev:iwe-map` refresh over the docs this change makes stale;
  `stale-map-docs.py` ends `RESULT=SUCCESS`.

### Task 6: CI passes on the pull request

- [ ] Every check on the pull request's head is green, including
  `Validate agent files`. Closed by: the CI run on the current head.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — a new requirement beside
"Map staleness reflects described content":

``` markdown
## ADDED Requirements

### Requirement: An agent push carries a fresh codebase map

The branch push helper shared by the pull request skills SHALL run the
codebase-map staleness check against the commit it pushes, SHALL refuse to push when the
check reports a stale map, and SHALL push without the check only when the
repository has no IWE map or the caller passes an explicit override. The AI
pull request review SHALL NOT report codebase-map staleness, which the CI
staleness check owns.

#### Scenario: A push would carry a stale map

- **WHEN** a pull request skill pushes a branch whose map docs the staleness
  check reports stale
- **THEN** the push helper pushes nothing and reports `MAP_STALE`, and the skill
  runs the Map refresh, commits it, and pushes again

#### Scenario: The repository has no map

- **WHEN** the repository root has no `.iwe/config.toml`, or the check reports
  no map docs
- **THEN** the push helper pushes without gating

#### Scenario: The user pushes a stale map on purpose

- **WHEN** the user explicitly asks to push while the map is stale
- **THEN** the skill passes the override, the helper pushes and reports the
  check as overridden, and CI still reports the stale map

#### Scenario: A review sees a stale map

- **WHEN** an AI review runs on a pull request whose map docs are stale
- **THEN** the review raises no finding about map staleness
```

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_push_branch_map_check.py`
  passes, and the existing plugin tests still pass
  (`uv run pytest .agents/plugins/agentdev/tests`).
- `shellcheck` passes on `push-branch.sh` through pre-commit.
- `push-branch.sh --help` lists `MAP_STALE`, `MAP_CHECK_FAILED`, and
  `--skip-map-check`.
- `grep -n "IGNORE stale codebase-map docs" .agents/plugins/agentdev/skills/pr-review/SKILL.md`
  returns the approved line, directly after the import-ordering bullet.
- `grep -n "git push"` over the three routed `SKILL.md` files returns no bare
  push instruction.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
- `stale-map-docs.py` ends `RESULT=SUCCESS`; `iwe normalize` and
  `iwe schema validate` pass.

## Out of scope

- A CI job that refreshes the map and pushes to the pull request branch.
- A pre-commit or pre-push hook for map staleness.
- Checking plan `## Key references` line anchors; `stale-map-docs.py` covers
  only `data/codebase/` digests, and the `pr-review` exclusion covers only map
  staleness.
- Configuring Greptile.
- Pushes a human makes outside the skills.

## Key references

Verified anchor points (line numbers as of 2026-09-30):

- `.agents/plugins/agentdev/skills/pr-open/scripts/push-branch.sh:9` —
  `RESULT_CODES+=` declared results
- `.agents/plugins/agentdev/skills/pr-open/scripts/push-branch.sh:17` —
  `usage()`
- `.agents/plugins/agentdev/skills/pr-open/scripts/push-branch.sh:86` —
  `check_map_freshness`, the map gate
- `.agents/plugins/agentdev/skills/pr-open/scripts/push-branch.sh:200` —
  `ACTION=push`, existing-upstream push path
- `.agents/plugins/agentdev/skills/pr-open/scripts/push-branch.sh:218` —
  `ACTION=push-with-upstream` path
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:207` —
  `### 8. Push the Branch`
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:244` — non-`SUCCESS`
  handling of `push-branch.sh`
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:89` — Workflow 3 push
  through the `pr-open` push helper
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:225` — "Push
  to PR branch" through the push helper
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:46` —
  `switch -c pr-merge-worktree/<pr>`, followed by its upstream at `:47`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:165` — "commit, and push
  the focused repair" through the push helper
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:179` — "Commit, then push
  with" the push helper
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:43` — "IGNORE import
  ordering" bullet
- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:122` — refresh mode
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:60` —
  `Results (RESULT / exit code)`
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:277` —
  `masked_hash`, reads working-tree contents
- `.github/workflows/validate-agent-files.yml:92` —
  `Check codebase map docs against their sources`
- `.agents/plugins/agentdev/tests/git_fixtures.py:11` — `FIXTURE_ENV` shared git
  fixture identity
