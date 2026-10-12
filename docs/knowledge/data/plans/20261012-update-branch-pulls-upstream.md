---
type: plan
created: 2026-10-12
description: Make update-branch bring in the commits the branch's own upstream gained on the remote — fast-forward or merge — before it merges the base, with each merge stopping on conflicts and a rerun continuing.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-12T21:11:49Z
sources:
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.sh
- resource: .agents/plugins/agentdev/skills/git-merge-resolve/agent-code/git-merge-resolve.sh
- resource: .agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.sh
---

# Update branch pulls its upstream before merging the base

## Context

`update-branch.sh` fetches the remote, then merges `<remote>/<base>` into the
local `HEAD`. It never looks at the branch's own upstream, although the fetch
already refreshed it. When the remote branch holds commits the local one lacks —
pushed from another checkout or Codespace, an autofix bot, GitHub's "Update
branch" button — the base merge lands on a stale `HEAD`, and `pr-open`'s
`push-branch.sh` then refuses the push as `NOT_FAST_FORWARD` (diverged). The
branch needs a second merge, and conflicts already resolved once may come back.
When the remote branch already contains the base, the up-to-date check still
compares against the local `HEAD` and makes a merge nobody needed.

## Approach

Insert an upstream sync between the fetch and the up-to-date check. The upstream
is the branch's configured upstream, read from `git for-each-ref`
(`%(upstream:short)`) so a deleted one is still named:

| Case                                  | `UPSTREAM_ACTION` | Effect                                               |
| ------------------------------------- | ----------------- | ---------------------------------------------------- |
| No upstream configured                | `untracked`       | Skip                                                 |
| Upstream is the base ref              | `base`            | Skip; the base merge covers it                       |
| Upstream branch absent on its remote  | `gone`            | Warn on stderr and continue to the base merge        |
| Upstream already contained in `HEAD`  | `none`            | Nothing                                              |
| `HEAD` is an ancestor of the upstream | `fast-forward`    | `git merge --ff-only <upstream>`                     |
| Diverged                              | `merge`           | Merge through `git-merge-resolve.sh`, a merge commit |

When the upstream's remote differs from `--remote`, it is fetched too; a failed
fetch is `FETCH_FAILED`. "Gone" is decided by
`git ls-remote --exit-code --heads <upstream-remote> <upstream-branch>`
returning `2`; any other failure of that command is `FETCH_FAILED`. An upstream
on the local repository (`branch.<name>.remote` is `.`) is synced like any
other, without a fetch or an existence check.

Both merges run `git-merge-resolve.sh` as a child process instead of `exec`: the
script forwards the helper's stdout except its `RESULT=` line, then maps the
helper's exit code onto its own result (`0` continue, `4` `MERGE_CONFLICTS`, `2`
`PREFLIGHT_ERROR`, anything else `SCRIPT_FAILURE`). The helper's `3` (already
merged) cannot occur: the script calls it only after its own ancestry checks. A
conflicted merge stops the run; the helper's `SOURCE=` line names which merge
stopped. After the agent resolves and commits it, a rerun finds that merge
already done and continues to the next one. The up-to-date check moves after the
sync, so it compares the base against the synced `HEAD`. The run reports
`ALREADY_UP_TO_DATE` only when it created no merge commit; a fast-forward alone
does not count.

Exit codes are unchanged. New output keys: `UPSTREAM` (empty for `untracked`)
and `UPSTREAM_ACTION`.

Rejected: `git pull --rebase` onto the upstream — it rewrites local commits and
contradicts the skill's merge-based contract; fast-forward only with a new
`UPSTREAM_DIVERGED` stop — a local fix plus a remote commit is a supported case,
and it would always bounce back to the agent; keeping `exec` for the base merge
— two merges would then report through two different paths.

## Implementation Steps

### Task 1: Upstream sync in the update script

**Files:** Modify:
`.agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.sh`,
`.agents/plugins/agentdev/tests/test_update_branch.py`

- [x] Tests, written first against a local bare-repository remote with
  `git_fixtures` helpers, fail before the script change and cover: behind only
  (branch fast-forwarded to its upstream, then the base merged); behind an
  upstream that already contains the base (fast-forward, `ALREADY_UP_TO_DATE`,
  no merge commit); diverged without conflicts (upstream merge commit, then the
  base merged); diverged with conflicts (`MERGE_CONFLICTS`, `SOURCE=` the
  upstream, base not merged), then a rerun after the resolution is committed
  merges the base; upstream gone (warning on stderr, base merged,
  `UPSTREAM_ACTION=gone`); upstream is the base ref (`UPSTREAM_ACTION=base`,
  base merged once); upstream on a second remote (that remote fetched, its
  commits brought in)
  - **Evidence:** commit "feat(update-branch): bring in the branch's upstream
    before the base"; the nine new tests failed against the previous script, and
    two more cover the base-merge conflict `SOURCE` and an unreachable upstream
    remote (`FETCH_FAILED`) from the spec delta.
- [x] `update-branch.sh` implements the Approach table, the second-remote fetch,
  the non-`exec` helper calls with result mapping, the moved up-to-date check,
  and the `UPSTREAM` / `UPSTREAM_ACTION` keys; `--help` lists the new keys and
  the rerun rule; `shellcheck -x` is clean; the two existing tests still pass
  - **Evidence:** commit "feat(update-branch): bring in the branch's upstream
    before the base"; `uv run pytest .agents/plugins/agentdev/tests` 139 passed
    (`test_update_branch.py` 11); `shellcheck -x update-branch.sh` clean.

### Task 2: Skill definition

**Files:** Modify: `.agents/plugins/agentdev/skills/update-branch/SKILL.md`

- [x] The frontmatter `description` becomes:

  ``` text
  'Update the current Git feature branch: fetch, bring in the commits its own upstream gained on the remote, then merge the remote base branch. Use when asked to sync a feature branch, bring a branch up to date with `origin/main`, refresh a stale PR branch, or unblock CI after base-branch drift. Keywords: update branch, pull branch, sync with origin/main, fetch and merge main, refresh feature branch.'
  ```

  - **Evidence:** commit "docs(update-branch): describe the upstream sync in the
    skill"; SKILL.md frontmatter carries the text verbatim.

- [x] `## Safety Rules` gains rule 5:

  ``` markdown
  5. NEVER rebase or reset to bring in the upstream; diverged history is merged.
  ```

  - **Evidence:** commit "docs(update-branch): describe the upstream sync in the
    skill"; rule 5 present in SKILL.md `## Safety Rules`.

- [x] The `## Bundled Script` bullet list is replaced by the following, and the
  rest of the section (options, `RESULT=` line) stays:

  ``` markdown
  - checks repository, branch, and working-tree preconditions
  - fetches the configured remote, and the upstream's remote when it differs
  - brings in the branch's own upstream first — a fast-forward when the branch
    is only behind it, a merge when the two diverged
  - detects a branch that already contains the base ref
  - merges the base ref through the `git-merge-resolve` bundled script

  The upstream is the branch's configured upstream. The script reports its sync
  as `UPSTREAM_ACTION`:

  | UPSTREAM_ACTION | When                                                  |
  | --------------- | ----------------------------------------------------- |
  | `none`          | The branch already contains its upstream              |
  | `fast-forward`  | The branch was only behind its upstream               |
  | `merge`         | The branch and its upstream diverged                  |
  | `untracked`     | The branch has no upstream yet                        |
  | `base`          | The upstream is the base ref; the base merge covers it |
  | `gone`          | The upstream branch no longer exists on its remote    |

  On `gone` the script prints a warning and continues; the push in Workflow 3
  recreates the remote branch.
  ```

  - **Evidence:** commit "docs(update-branch): describe the upstream sync in the
    skill"; bullets, `UPSTREAM_ACTION` table, and `gone` note present in
    SKILL.md `## Bundled Script`.

- [x] In the `## Workflow 2: Handle the Result` table, these three rows replace
  their current versions; the other rows stay:

  ``` markdown
  | `SUCCESS`            | `0`  | The update created a merge commit                                     | Continue. The delegated [git-merge-resolve](../git-merge-resolve/SKILL.md) completion workflow still requires reformatting and targeted validation before push. |
  | `ALREADY_UP_TO_DATE` | `3`  | The branch already contains the base ref; no merge commit was needed | Report that the branch is already up to date. A fast-forward to its upstream may have moved it; there is nothing new to push.                                   |
  | `MERGE_CONFLICTS`    | `4`  | A merge stopped on conflicts; `SOURCE` names the ref being merged     | Invoke and complete the [git-merge-resolve](../git-merge-resolve/SKILL.md) conflict-resolution and completion workflows, then rerun Workflow 1.                |
  ```

  - **Evidence:** commit "docs(update-branch): describe the upstream sync in the
    skill"; the `SUCCESS`, `ALREADY_UP_TO_DATE`, and `MERGE_CONFLICTS` rows
    replaced, other rows unchanged.

- [x] A subsection follows the table:

  ``` markdown
  ### Rerun After a Conflict

  Each run stops at the first conflicted merge, so one run never resolves two.
  After git-merge-resolve commits a resolution, run Workflow 1 again: when the
  conflict was in the upstream merge, the rerun goes on to merge the base.
  Repeat until the script returns `SUCCESS` or `ALREADY_UP_TO_DATE`. An
  `ALREADY_UP_TO_DATE` that follows a resolved conflict still leaves a new merge
  commit on the branch — continue to Workflow 3.
  ```

  - **Evidence:** commit "docs(update-branch): describe the upstream sync in the
    skill"; `### Rerun After a Conflict` precedes `## Workflow 3` in SKILL.md.

- [x] `## Completion Criteria` replaces its first bullet with:

  ``` markdown
  - The configured remote, and the upstream's remote when it differs, were fetched
  - The branch's upstream, when it has one, was fast-forwarded or merged before
    the base
  ```

  - **Evidence:** commit "docs(update-branch): describe the upstream sync in the
    skill"; both bullets replace the former first bullet.

- [x] `## Troubleshooting` gains the row:

  ``` markdown
  | Upstream reported `gone`  | Remote branch deleted, often after its PR merged | Confirm the PR is still open before Workflow 3 recreates the branch |
  ```

  - **Evidence:** commit "docs(update-branch): describe the upstream sync in the
    skill"; the `gone` row ends the `## Troubleshooting` table.

- [x] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  reports no errors

  - **Evidence:** commit "docs(update-branch): describe the upstream sync in the
    skill";
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    62/62 skills valid, 0 errors, 0 warnings.

## Spec changes

Creates `spec/update-branch`:

``` markdown
## ADDED Requirements

### Requirement: update-branch brings in the branch's upstream before the base

The update-branch skill SHALL bring the commits of the current branch's
configured upstream into the branch before it merges the base ref — by
fast-forward when the branch is only behind the upstream, by a merge commit
when they diverged — and SHALL NOT rebase, reset, or force-push to do so. It
SHALL decide whether the branch is already up to date only after that sync.

#### Scenario: The branch is behind its upstream

- **WHEN** `origin/X` holds commits the local branch `X` lacks and `X` has no
  commits `origin/X` lacks
- **THEN** `X` is fast-forwarded to `origin/X` before `origin/main` is merged
- **AND** `UPSTREAM_ACTION` is `fast-forward`

#### Scenario: The branch and its upstream diverged

- **WHEN** `X` and `origin/X` each hold commits the other lacks
- **THEN** `origin/X` is merged into `X` with a merge commit before
  `origin/main` is merged
- **AND** `UPSTREAM_ACTION` is `merge`

#### Scenario: The upstream already contains the base

- **WHEN** `X` is behind `origin/X` and `origin/X` already contains
  `origin/main`
- **THEN** `X` is fast-forwarded and no merge commit is created
- **AND** the skill reports `ALREADY_UP_TO_DATE`

#### Scenario: The branch has no upstream

- **WHEN** `X` has no configured upstream
- **THEN** the base is merged as before and `UPSTREAM_ACTION` is `untracked`

#### Scenario: The upstream is the base ref

- **WHEN** `X` tracks `origin/main` and `origin/main` is the base ref
- **THEN** no separate upstream sync runs, the base is merged once, and
  `UPSTREAM_ACTION` is `base`

#### Scenario: The upstream branch is gone

- **WHEN** `X` tracks `origin/X` and `origin/X` no longer exists on the remote
- **THEN** a warning is printed, the base is merged, and `UPSTREAM_ACTION` is
  `gone`

#### Scenario: The upstream lives on another remote

- **WHEN** `X` tracks `fork/X` and the base remote is `origin`
- **THEN** `fork` is fetched too and `fork/X` is brought in before
  `origin/main` is merged
- **AND** a failed fetch of `fork` is reported as `FETCH_FAILED`

### Requirement: Each conflicted merge stops the run and a rerun continues

The update-branch skill SHALL stop at the first merge that conflicts, report
`MERGE_CONFLICTS` with `SOURCE` naming the ref being merged, and leave any
later merge undone. A rerun after the resolution is committed SHALL treat the
resolved merge as done and continue with the next one.

#### Scenario: The upstream merge conflicts

- **WHEN** merging `origin/X` into `X` conflicts
- **THEN** the skill reports `MERGE_CONFLICTS` with `SOURCE=origin/X`
- **AND** `origin/main` is not merged in that run

#### Scenario: Rerun after resolving the upstream merge

- **WHEN** the upstream conflict is resolved and committed and the skill runs
  again
- **THEN** `UPSTREAM_ACTION` is `none` and `origin/main` is merged

#### Scenario: The base merge conflicts

- **WHEN** the upstream sync succeeds and merging `origin/main` conflicts
- **THEN** the skill reports `MERGE_CONFLICTS` with `SOURCE=origin/main`
```

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_update_branch.py` — all
  tests pass, the seven new ones included.
- `shellcheck -x .agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.sh`
  is clean.
- `update-branch.sh --help` lists `UPSTREAM`, `UPSTREAM_ACTION`, and the rerun
  rule.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  reports no errors.
- `uv run pytest .agents/plugins/agentdev/tests` passes, as `.agents/AGENTS.md`
  requires after editing a shipped script.

## Out of scope

- Changing `push-branch.sh` or its `NOT_FAST_FORWARD` handling.
- Editing the callers (`pr-open`, `pr-feedback-resolution`, `git-new-branch`);
  they follow update-branch's result table, which keeps its exit codes.
- Moving `spec/pr-merge-conflicts`' "update-branch accepts a calling skill's
  remote and base" requirement into `spec/update-branch`.
- Stack branches, which Workflow 0 already refuses.
- Changing `git-merge-resolve.sh`.

## Key references

Verified anchor points (line numbers as of 2026-10-12):

- `.agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.sh:10`
  — `RESULT_CODES` (unchanged)
- `.agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.sh:15`
  — `usage` help text
- `.agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.sh:90`
  — fetch of `--remote`
- `.agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.sh:104`
  — up-to-date check, to move after the sync
- `.agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.sh:113`
  — `exec` delegation to `git-merge-resolve.sh`, to replace
- `.agents/plugins/agentdev/skills/git-merge-resolve/agent-code/git-merge-resolve.sh:115`
  — `DESTINATION=` / `SOURCE=` output
- `.agents/plugins/agentdev/skills/git-merge-resolve/agent-code/git-merge-resolve.sh:129`
  — `git merge --no-ff`, result codes `0`/`2`/`4`
- `.agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.sh:179` —
  diverged-upstream refusal this plan prevents
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:3` — frontmatter
  `description`
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:31` —
  `## Safety Rules`
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:39` —
  `## Bundled Script`
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:82` —
  `## Workflow 2: Handle the Result`
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:113` —
  `## Completion Criteria`
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:121` —
  `## Troubleshooting`
- `.agents/plugins/agentdev/tests/test_update_branch.py:11` —
  `initialize_repository` fixture
- `.agents/plugins/agentdev/tests/git_fixtures.py:19` — `git` helper
