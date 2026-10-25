---
type: plan
created: 2026-10-23
release:
- bugs/pr-update-skips-review-eval
description: Make every push to a reviewed pull request run the re-review evaluation, enforce one AI review trigger per head SHA with a bundled script, and retire the pr-* skill logic that assumed comment-requested reviews ran invisibly on the default branch, deleting pr-discover-ai-responder.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-25T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-sync/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-discover-ai-responder/SKILL.md
- resource: .github/workflows/ai-responder.yml
- resource: docs/knowledge/data/spec/ai-review-gate.md
---

# PR skills drive the AI review lifecycle on the single review workflow

## Context

Fixes [Bug: PR updates skip the re-review
evaluation](../bugs/pr-update-skips-review-eval.md). The [AI review
gate](../spec/ai-review-gate.md) passes on any accepted review across later
pushes and leaves refreshing it to the author; `pr-eval-review-needed` is the
skill that makes that call. Only `pr-feedback-resolution` invokes it, so
`pr-sync` — which keeps a pull request's title and body in step with what the
branch changes, and handles no feedback — and `pr-merge`'s CI-fix pushes update
reviewed pull requests without ever asking. The once-per-head-SHA trigger rule
is prose held in conversation memory, so separate sessions double-trigger.

Absorbs [Simplify the pr-* skills for the single review
workflow](../backlog/simplify-pr-skills-single-review-workflow.md). Since [One
AI review workflow with a needs-coupled
gate](20260903-single-ai-review-workflow.md), an `@claude review` comment runs a
short `bridge` job (an `issue_comment` run filed on the default branch) that
dispatches `ai-responder.yml` on the pull request's head branch. That dispatched
run's `AI responder preflight`, `Claude PR Review Responder`, and
`ai-review-present` checks are filed on the head commit, so `gh pr checks` shows
the review while it runs, and `ai-review-present` needs the review job, so it
stays pending until the review finishes and resolves in the same run.
`pr-merge`, `pr-request-ai-review`, and `pr-discover-ai-responder` still carry
the logic for the earlier shape: workflow-filename discovery, run attribution by
log grep, watching runs by id, and the retired `Require AI Review` workflow
name.

The maintainer decided that no consumer repository runs the earlier two-workflow
shape, so the skills are simplified outright with no shape detection, and that
`pr-discover-ai-responder` is deleted. The workflow filename is fixed by
contract: the bridge dispatches `.github/workflows/ai-responder.yml` by path.

## Approach

Four changes:

1. **Callers.** `pr-open` gains step 10, run on every update-mode run regardless
   of what the push or the body edit changed: apply `pr-eval-review-needed`.
   `pr-sync` inherits it unchanged. `pr-merge` step 5 applies the eval after a
   CI-fix push, before restarting its loop. `pr-feedback-resolution` already
   calls the eval and pushes through `push-branch.sh` rather than the `pr-open`
   skill, so it never evaluates twice.
2. **The test.** `pr-eval-review-needed` stops asking "did I change anything the
   reviewer did not direct?" and asks whether the diff since the newest reviewed
   commit goes beyond what the pull request's review threads and review comments
   since that review asked for. The evidence is read from the pull request, so a
   cold run from `pr-sync` or `pr-merge` decides on the same footing as a
   feedback pass. The request/decline lists are unchanged.
3. **One trigger per head.** A new
   `pr-request-ai-review/agent-code/request-review.sh` is the only path that
   posts an AI review trigger, used by `pr-request-ai-review` and by
   `pr-merge`'s AI Review Recovery, whose in-conversation ledger it replaces.
   The unit is the commit, not the poster: a comment whose body opens
   `@claude review` (case folded, as the responder's preflight matches it) is a
   trigger whether a skill or a person posted it. A trigger the script posts
   names the commit it requests and counts for that commit only; a hand-typed
   one counts for the head only when it provably postdates the head's arrival.
   Before posting, the script reads the pull request's head, its reviews, and
   its issue comments, and refuses when an accepted AI review already names the
   head or a trigger for the head exists.
4. **The head commit's checks are the review's status.** A requested review has
   started when `Claude PR Review Responder` or `ai-review-present` is pending
   on the head commit, and it has finished when the latest `ai-review-present`
   run on the head completes; `pr-merge` and `pr-request-ai-review` watch
   `gh pr checks` for both and never look up the workflow by name or a run by
   id. A trigger that produces no check on the head names its cause from the
   `issue_comment` run on the default branch: a fork, a head branch without
   `ai-responder.yml`, or a rejected requester — each needs a person, not a
   retry. `pr-discover-ai-responder`, its script, and its tests are deleted;
   every `Require AI Review` reference becomes `ai-review-present`.

`request-review.sh` takes `--pr <number>` (required), `--rationale <one line>`
(optional; a newline in it is a `PREFLIGHT_ERROR`), and `--repo <owner/repo>`
(optional). The head's arrival time is the earliest `created_at` among the head
commit's check suites (`repos/{owner}/{repo}/commits/<sha>/check-suites`). A
posted trigger's body is `@claude review`, then the rationale line when given,
then `<!-- review-head: <sha> -->`; a comment carrying that marker counts for
the SHA it names and no other, whatever its date. An unmarked trigger counts for
the head only when created after the head's arrival; a head with no check suite
has no arrival time, so no unmarked trigger counts for it. Doubt resolves toward
posting: a duplicate trigger costs one redundant review, a wrongly counted one
leaves the head unreviewed. Accepted reviewers are the ones
[spec/ai-review-gate](../spec/ai-review-gate.md) names — `claude[bot]`,
`github-actions[bot]`, `chatgpt-codex-connector[bot]` — in state `APPROVED`,
`CHANGES_REQUESTED`, or `COMMENTED`. The spec's `+1` reaction from
`chatgpt-codex-connector[bot]` is not counted: a reaction names no commit, so it
cannot show that the head was reviewed. Output keys: `PR_NUMBER`, `HEAD_SHA`,
`COMMENT_URL` (the posted or the existing trigger; empty for
`ALREADY_REVIEWED`), and the `RESULT=` line:

| RESULT              | Exit | When                                                               |
| ------------------- | ---- | ------------------------------------------------------------------ |
| `SUCCESS`           | `0`  | Trigger posted for the head                                        |
| `ALREADY_REVIEWED`  | `3`  | An accepted AI review's commit is the head                         |
| `ALREADY_REQUESTED` | `4`  | A trigger names the head, or an unmarked one postdates its arrival |
| `PR_NOT_OPEN`       | `5`  | The pull request is closed, merged, or not found                   |
| `GH_UNAVAILABLE`    | `6`  | `gh` is missing, unauthenticated, or its API call failed           |
| `PREFLIGHT_ERROR`   | `2`  | Missing `--pr`, unknown argument, multi-line rationale             |
| `SCRIPT_FAILURE`    | `1`  | Unhandled error                                                    |

The maintainer decided that a hand-typed trigger counts like any other: two
review requests on one commit are never useful. One that no check suite dates
after the head is not counted, because it may belong to the previous head. The
script reads no workflow runs: the checks on the head commit already show
whether a requested review is running, and the skills read them there.

Rejected: dating the head by its commit date, alone or as a fallback — a
commit's date records when it was authored or committed, not when it reached the
pull request, so an old commit pushed late would inherit the previous head's
trigger; matching a marked trigger by date instead of by its marker — a trigger
posted before the head's first check suite would be missed; reading the issue
timeline to date the head — its `committed` event carries no timestamp; hooking
the eval into `pr-sync` alone — `pr-open` reached directly in update mode would
stay uncovered; gating step 10 on whether the push moved the head — a head
pushed earlier by another path would be skipped unevaluated; keeping
`pr-discover-ai-responder` for the trigger-without-check case — one
`gh run list --workflow ai-responder.yml --event issue_comment` line in
`pr-request-ai-review` covers it, and the filename is fixed; detecting which
workflow shape a repository runs — no consumer runs the earlier one.

## Implementation Steps

### Task 1: Trigger script

**Files:** Create:
`.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh`,
`.agents/plugins/agentdev/tests/test_request_review.py`

- [x] Tests, written first with a stub `gh` on a hermetic `PATH` in the style of
  `test_fetch_issue.py`, fail before the script exists and cover: no review and
  no trigger posts one whose body opens `@claude review`, carries the rationale
  line, and prints `COMMENT_URL` (`SUCCESS`); an accepted review on the head
  posts nothing (`ALREADY_REVIEWED`); an accepted review on an older commit
  still posts; a review by an unaccepted author on the head still posts; the
  posted body ends with the head's `review-head` marker; a marked trigger for
  the head posts nothing and prints its URL (`ALREADY_REQUESTED`), even when
  created before the head's earliest check suite; a marked trigger for another
  commit still posts, even when created after it; a hand-typed trigger created
  after the head's earliest check suite, in any letter case, posts nothing
  (`ALREADY_REQUESTED`); one created before it still posts; a hand-typed trigger
  on a head with no check suite still posts; a comment that mentions
  `@claude review` mid-body is not a trigger; a closed pull request
  (`PR_NOT_OPEN`); a failing `gh` call (`GH_UNAVAILABLE`); missing `--pr` and a
  multi-line rationale (`PREFLIGHT_ERROR`); `RESULT=` is the last stdout line on
  every path
  - **Evidence:** `tests/test_request_review.py` covers every listed case with a
    stub `gh` on a hermetic `PATH`; all 24 tests failed before the script
    existed.
- [x] `request-review.sh` implements the Approach's arguments, checks, head
  dating, output keys, and result table per `/agentdev:skill-scripts`, sourcing
  `bin/result-codes.sh`; `--help` lists options, keys, and results;
  `shellcheck -x` is clean; the new tests pass
  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` — 24
    passed; `shellcheck -x` on `request-review.sh` is clean; `gh api` confirmed
    to print the 404 body on stdout, which the script reads to report
    `PR_NOT_OPEN`.

### Task 2: pr-request-ai-review posts through the script

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md`

- [x] `## Post the request` runs
  `agent-code/request-review.sh --pr <pr> --rationale '<one line>'` instead of
  `gh pr comment`, with a table mapping each `RESULT` to its action
  (`ALREADY_REVIEWED` and `ALREADY_REQUESTED` are reported, not retried;
  `GH_UNAVAILABLE`, `PR_NOT_OPEN`, `PREFLIGHT_ERROR`, `SCRIPT_FAILURE` stop);
  `## Post at most once per head SHA` states that the script enforces the rule
  for every trigger on the head, hand-typed ones included when a check suite
  dates them after the head, and that no skill posts a trigger any other way;
  the frontmatter gains `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`
  as `pr-open` has it
  - **Evidence:** `pr-request-ai-review/SKILL.md` runs `request-review.sh` under
    `## Post the request` with a seven-row RESULT table,
    `## Post at most once per head SHA` names the script as the only trigger
    path, and the frontmatter carries `allowed-tools`;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reports 63/63 skills valid.

### Task 3: pr-request-ai-review confirms from the head commit's checks

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md`

- [x] `## Confirm it started` confirms the review from a pending
  `Claude PR Review Responder` or `ai-review-present` check on the head commit
  in `gh pr checks <pr>`, and drops workflow discovery and the claim that
  comment-triggered runs are not attached to the head
  - **Evidence:** `pr-request-ai-review/SKILL.md` `## Confirm it started` reads
    `gh pr checks <pr>` for a pending `Claude PR Review Responder` or
    `ai-review-present` check and no longer mentions workflow discovery or runs
    detached from the head.
- [x] Its gap shapes are read from the `issue_comment` run of `ai-responder.yml`
  the comment started on the default branch: every job skipped — the mention
  never qualified; preflight failed, or the bridge skipped or failed — nothing
  was dispatched (a fork, a head branch without `ai-responder.yml`, or a
  rejected requester), which needs a person; a review check that completes
  without a review — report the run's failure
  - **Evidence:** the same section lists the three shapes of the `issue_comment`
    run, with the `gh run list` and `gh run view --json jobs` commands that read
    it.
- [x] `## Related Skills` drops `pr-discover-ai-responder`
  - **Evidence:** `grep -n discover` on `pr-request-ai-review/SKILL.md` returns
    nothing; `validate_agent_files` reports 63/63 skills valid.

### Task 4: The eval reads intent from the pull request

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md`

- [x] `## The test` asks whether the diff since the newest reviewed commit goes
  beyond what the pull request's review threads and review comments since that
  review asked for, replacing the first-person question; the request/decline
  lists in `## What counts as beyond the feedback` keep their items
  - **Evidence:** `pr-eval-review-needed/SKILL.md` `## The test` asks whether
    the diff since the newest reviewed commit goes beyond the review threads and
    comments since that review; `## What counts as beyond the feedback` is
    unchanged.
- [x] `## Establish what the last review saw` adds the command that reads the
  review threads and comments posted since the newest reviewed commit, and says
  that a run with no such threads judges the whole diff as undirected
  - **Evidence:** the section adds `gh pr view --json reviews,comments` and
    `gh api --paginate repos/{owner}/{repo}/pulls/<pr>/comments` filtered from
    the newest reviewed review, and judges the whole diff as new work when
    nothing since asks for anything; both commands return the expected fields
    against PR #429.
- [x] The frontmatter `description` and the opening paragraph name `pr-open`'s
  update mode and `pr-merge`'s CI-fix push as callers alongside feedback
  resolution
  - **Evidence:** the description and opening paragraph name `pr-open` update
    mode, `pr-merge` after a CI-fix push, and `pr-feedback-resolution`;
    `validate_agent_files` reports 63/63 skills valid.

### Task 5: pr-open evaluates on every update

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-open/SKILL.md`

- [x] A new `### 10. Re-Review Evaluation` follows step 9: in update mode,
  always apply [pr-eval-review-needed](../pr-eval-review-needed/SKILL.md) with
  `PR_NUMBER`, and add its decision to the step 9 report; create mode skips it.
  `### 10. Error Handling` becomes `### 11. Error Handling`
  - **Evidence:** `pr-open/SKILL.md` gains `### 10. Re-Review Evaluation`, run
    on every update-mode run and skipped in create mode, and renumbers
    `### 11. Error Handling`; `validate_agent_files` reports 63/63 skills valid.

### Task 6: pr-merge evaluates CI-fix pushes

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [ ] Step 5 applies [pr-eval-review-needed](../pr-eval-review-needed/SKILL.md)
  after the push and before restarting the loop

### Task 7: pr-merge recovers the AI review from the head commit's checks

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [ ] Every `Require AI Review` reference — the completion criteria, the check
  classification in step 4, and the `## AI Review Recovery` introduction — names
  the `ai-review-present` check instead
- [ ] `## AI Review Recovery` drops workflow-filename discovery, the
  in-conversation per-head-SHA ledger, the "`gh pr checks` is not sufficient"
  warning, the `Determine checkout ref` attribution, and `gh run watch` by run
  id. A review in progress is a pending `Claude PR Review Responder` or
  `ai-review-present` check on the head, waited on with `gh pr checks --watch`
- [ ] Its trigger step requests the review through
  [pr-request-ai-review](../pr-request-ai-review/SKILL.md), whose script posts
  it; `ALREADY_REQUESTED` means wait on the head's checks, not post again
- [ ] The step that waits for a clean review's gate "to rerun and pass" says
  instead that the latest `ai-review-present` run on the head completes with the
  review, and a run whose review job ends without a review is reported, not
  retried; `## Related Skills` drops `pr-discover-ai-responder`

### Task 8: Delete pr-discover-ai-responder

**Files:** Delete: `.agents/plugins/agentdev/skills/pr-discover-ai-responder/`
(`SKILL.md`, `agent-code/discover-ai-responder.sh`),
`.agents/plugins/agentdev/tests/test_discover_ai_responder.py`; Modify:
`.agents/plugins/agentdev/README.md`

- [ ] The skill directory and its test file are removed, and the README's skills
  table drops its row
- [ ] `grep -rn 'pr-discover-ai-responder\|discover-ai-responder\|Require AI Review' .agents`
  returns nothing

### Task 9: Codebase map

**Files:** Modify:
`docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md` and any other
doc `stale-map-docs.py` reports

- [ ] `/agentdev:iwe-map` refresh mode re-reads the stale docs —
  `pr-discover-ai-responder` leaves the skill count, the family table, and the
  bundled-scripts list, and `pr-request-ai-review` joins that list — and
  `stale-map-docs.py` reports none stale

## Spec changes

- `ai-review-refresh` (new) — **normative outcome:** after any push to a pull
  request that has an accepted AI review, made through `pr-open`'s update mode,
  `pr-merge`'s CI-fix step, or feedback resolution, the agent SHALL apply the
  re-review evaluation and report its decision; the catalog SHALL NOT post an AI
  review trigger for a head SHA that already has one, whoever posted it, or that
  an accepted AI review already names; and the catalog SHALL judge a requested
  review as running or finished from the checks on the pull request's head
  commit.

[spec/ai-review-gate](../spec/ai-review-gate.md) is unchanged: the workflow
already behaves as its comment-mention requirement states.

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` passes,
  and `uv run pytest .agents/plugins/agentdev/tests` stays green with
  `test_discover_ai_responder.py` gone.
- `shellcheck -x .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh`
  is clean.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
- `grep -rn "gh pr comment" .agents/plugins/agentdev/skills/*/SKILL.md` shows no
  `@claude review` trigger outside `request-review.sh`.
- `grep -rn 'pr-discover-ai-responder\|Require AI Review\|gh run watch\|Determine checkout ref' .agents/plugins/agentdev`
  returns nothing.
- Manual: on a reviewed pull request, commit a behavior change no thread asked
  for and run `/agentdev:pr-sync`; the run reports a re-review decision, posts
  one trigger, and confirms it from a pending check on the head commit. Rerun
  `/agentdev:pr-sync` without a new commit; the script reports
  `ALREADY_REQUESTED` and nothing is posted. On a fresh head, type
  `@claude review` by hand, then run the script; it reports `ALREADY_REQUESTED`.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- `update-branch`'s own pushes — it runs no eval after a base merge, though the
  eval counts a judgment-call conflict merge as new scope.
- Reading workflow runs inside `request-review.sh`.
- Any change to the `ai-review-present` gate or the responder workflow.
- A push during a running review: the new head's gate passes on the prior review
  while the older head's run is pending. The skills do not claim that watching
  `gh pr checks` closes this window.
- `pr-merge-stack`, which reaches review handling through `pr-merge`.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:266` — step 9, create or
  update the pull request
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:311` —
  `### 10. Error Handling`, renumbered by Task 5
- `.agents/plugins/agentdev/skills/pr-sync/SKILL.md:8` — delegation to `pr-open`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:139` — completion criterion
  naming `Require AI Review`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:193` — step 4
  classification naming `Require AI Review`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:199` — step 5, CI-fix
  commit and push
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:240` —
  `## AI Review Recovery`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:249` — workflow-filename
  discovery
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:259` — in-conversation
  trigger ledger
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:262` — "`gh pr checks` is
  not sufficient" warning
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:275` — step 3, bare
  `gh pr comment` trigger
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:288` — step 4, wait by run
  id
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:297` — gate "to rerun and
  pass"
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:310` — `## Related Skills`
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:338` — the
  eval's existing caller
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md:27` —
  `## The test`
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md:67` —
  `## Establish what the last review saw`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:14` —
  `## Post the request`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:43` —
  `## Confirm it started`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:67` —
  `## Post at most once per head SHA`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:84` —
  `## Related Skills`
- `.agents/plugins/agentdev/skills/pr-discover-ai-responder/SKILL.md:1` — skill
  deleted by Task 8
- `.agents/plugins/agentdev/README.md:111` — skills-table row for
  `pr-discover-ai-responder`
- `.agents/plugins/agentdev/skills/extract-github-actions-logs/agent-code/parse-actions-url.sh:19`
  — `RESULT_CODES` pattern for a standalone script sourcing
  `bin/result-codes.sh`
- `.agents/plugins/agentdev/bin/result-codes.sh` — shared result helpers
- `.agents/plugins/agentdev/tests/test_fetch_issue.py:37` — hermetic `PATH` and
  `gh` stub pattern
- `.github/workflows/ai-responder.yml:363` — `bridge` job dispatching on the
  head branch
- `.github/workflows/ai-responder.yml:384` — the dispatched workflow path
- `.github/workflows/ai-responder.yml:509` — `ai-review-present`, needing
  `claude-respond`
- `docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md:31` — family
  table counting `pr-discover-ai-responder`
- `docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md:36` — skills
  with bundled scripts
