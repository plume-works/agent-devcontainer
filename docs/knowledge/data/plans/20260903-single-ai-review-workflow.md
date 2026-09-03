---
type: plan
created: 2026-09-03
description: Merge the AI responder and the ai-review-present gate into one workflow whose gate job depends on the review job, and bridge PR comment mentions into a workflow_dispatch on the PR head branch.
generated:
  by: claude-code/fable-5-1
  at: 2026-09-03T01:30:00Z
sources:
- resource: https://github.com/plume-works/agent-devcontainer/issues/95
- resource: .github/workflows/ai-responder.yml
- resource: .github/workflows/require-ai-review.yml
- resource: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- resource: https://docs.github.com/en/actions/concepts/security/github_token
---

# One AI review workflow with a needs-coupled gate

## Context

[Issue #95](https://github.com/plume-works/agent-devcontainer/issues/95) asks
for a review flow without race conditions, ready for an autonomous merge path.
The shipped flow
([AI responder workflows](../features/ai-responder-workflows.md)) is two
workflows coupled only by polling, and the coupling fails in both directions:

- **The gate cannot observe the review it waits for.** The responder posts its
  review with `GITHUB_TOKEN`, and GitHub creates no workflow run for events that
  token produces. The gate's `pull_request_review` trigger therefore never fires
  for a Claude review; its 8-minute poll is the only path, and a review that
  takes longer leaves the gate red until a human pushes or reviews.
- **The gate is green while a review is in flight.** A comment-requested review
  runs against `main`'s SHA, so nothing on the PR head says a review is running.
  With auto-merge enabled, the PR merges the moment CI finishes, whether or not
  the review has landed.
- **Comment-triggered runs execute `main`'s workflow file** while checking out
  the PR head, so a PR that changes the responder is reviewed by the old
  plumbing.

The gate's acceptance policy is kept: any prior accepted review is enough
([AI review gate](../spec/ai-review-gate.md)), and Codex web reviews must keep
satisfying it.

## Approach

One workflow file, `ai-responder.yml`, owns three jobs plus preflight:

```
pull_request · pull_request_review · workflow_dispatch        issue_comment · pull_request_review(_comment)
                        │                                          "@claude …" on a pull request
                        ▼                                                      │
  preflight — resolve PR, fork gate, write-access gate,               bridge (runs main's file)
              review_exists, is_draft, wants_review                   fork + write-access gate,
                        │                                             then `workflow_dispatch`
  claude-respond — if wants_review                     ◄──────────── on the PR head branch
                        │
  ai-review-present — needs: [claude-respond], if: always()
              sister job success → PASS; failure → FAIL;
              skipped → PASS iff an accepted review exists; else FAIL
```

Three GitHub facts make this shape sound:

1. A `workflow_dispatch` to a branch runs **that branch's** copy of the file
   (the file must also exist on the default branch), with `GITHUB_REF` and
   `GITHUB_SHA` set to the dispatched branch and its head. A dispatched review
   therefore lands its checks on the PR head, and every review — PR-event or
   comment-requested — runs the same file from the same ref.
2. `workflow_dispatch` is a documented exception to the rule that `GITHUB_TOKEN`
   events start no runs, so the bridge needs only `actions: write`.
3. `chatgpt-codex-connector[bot]` is a GitHub App, so a Codex web review fires
   `pull_request_review` and re-runs the gate. The poll served only the Claude
   path; `needs:` replaces it.

Because the gate job `needs` the review job, the `ai-review-present` check on
the head SHA stays pending for the whole review, and auto-merge waits. A push
during a review is the one window left: the new SHA's gate passes on the prior
review while the older SHA's run is still pending. Accepted, and recorded under
Out of scope.

Job and workflow names are kept (`ai-responder.yml`, `claude-respond`,
`ai-review-present`) so the `main` ruleset's required-check context and every
external reference stay valid; `require-ai-review.yml` is deleted. Timeouts are
unchanged — the gate's 10 minutes start only after the review job completes.

Rejected:

- **Two workflows, with the gate re-triggered by `workflow_run` on the
  responder.** Fixes the missed-review case only; the gate still has no head-SHA
  signal during a review, and PR-number plumbing across runs is the same
  discovery problem in a new place.
- **Posting the review through the Claude App identity so `pull_request_review`
  fires.** Would make the gate re-run after a review but keeps the
  poll-versus-timeout coupling and the in-flight blind spot.
- **A gate that waits on other runs of this workflow for the same PR.** Closes
  the push-during-review window at the cost of a gate timeout that must match
  the review's and cross-run discovery logic in the gate. The maintainer chose
  the plain `needs:` coupling.

## Implementation Steps

### Task 1: Preflight computes the trigger decision once

**Files:** Modify: `.github/workflows/ai-responder.yml`; Create:
`.github/actions/ai-review-status/action.yml`

The acceptance test (Claude or Codex review in an accepted state, or a Codex
`+1` reaction, trusted-bot waiver) moves out of the gate's inline script into a
composite action so preflight and the gate evaluate the same rule.

- [x] Add the `workflow_dispatch` trigger with inputs `pr_number` (required),
  `task` (the requested free-form task; empty means a review), `comment_id`, and
  `comment_kind` (`issue_comment`, `pull_request_review_comment`, or
  `pull_request_review`), and add the gate's `pull_request` activity types
  (`synchronize`, `review_requested`, `review_request_removed`),
  `pull_request_review` types (`dismissed`, `edited`), and `merge_group` to the
  existing `on:` block
  - **Evidence:** `.github/workflows/ai-responder.yml` `on:` block carries all
    four `workflow_dispatch` inputs (all `type: string`) and the merged trigger
    set; committed as "feat(ai-responder): preflight computes the trigger
    decision once".
- [x] Create `.github/actions/ai-review-status` as a composite action wrapping
  the acceptance logic now at `require-ai-review.yml:66-172` — inputs
  `pr-number`, `github-token`, `trusted-bot-actors`; outputs `found` and
  `reason` — with no sleep loop
  - **Evidence:** `.github/actions/ai-review-status/action.yml` — one
    `github-script` step, the three inputs, `found`/`reason` outputs, a single
    pass over reviews then reactions; same commit as above.
- [x] Extend `preflight` to resolve the PR from the `workflow_dispatch` input as
  well as from the event payload, and emit `review_exists` (from the composite
  action), `is_draft`, and `wants_review`, where `wants_review` is true for
  `opened`, `ready_for_review`, `reopened`, `assigned`, `workflow_dispatch` with
  an empty `task`, and `synchronize` when `review_exists` is false — and always
  false while `is_draft` is true on a `pull_request` event
  - **Evidence:** `preflight` in `.github/workflows/ai-responder.yml` —
    `Determine checkout ref` fetches the PR from `inputs.pr_number` on
    `workflow_dispatch`; `Check for an accepted AI review` runs the composite
    action after a sparse checkout of `.github/actions`;
    `Determine agent prompts` computes `wantsReview` from `payload.action`,
    `IS_DRAFT`, and `REVIEW_EXISTS`; job outputs `review_exists`, `is_draft`,
    `wants_review` (plus `head_ref` and `is_pull_request` for the bridge); same
    commit.
- [x] Keep the owner, fork, and write-access gates exactly as they are for every
  event, including `workflow_dispatch`
  - **Evidence:** the preflight `if:` gains only
    `github.event_name == 'workflow_dispatch'` as an accepted event; the
    `isFork` computation and `Authorize responder requester` step are unchanged
    and apply to the PR resolved from `inputs.pr_number`; same commit.
- [x] `actionlint` and `zizmor` pass on the workflow and the composite action
  - **Evidence:** `pre-commit run actionlint --files …` → Passed;
    `zizmor .github/workflows/ai-responder.yml .github/actions/ai-review-status/action.yml`
    → "No findings to report" (zizmor v1.22.0); the pre-commit hooks re-run both
    on the commit.

### Task 2: The review job runs on preflight's decision

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [x] Gate `claude-respond` on `needs.preflight.outputs.wants_review == 'true'`
  in place of the per-event `claude_requested` test, keeping the `is_fork` and
  result checks
  - **Evidence:** `claude-respond` `if:` in `.github/workflows/ai-responder.yml`
    reads `wants_review == 'true' || wants_task == 'true'` — `wants_task` is the
    free-form path (`issues` mentions, non-PR comments, a dispatch with a task)
    that the plan keeps as-is and `wants_review` does not cover;
    `claude_requested` is removed. Committed as "feat(ai-responder): run the
    review job on preflight's decision".
- [x] Build the prompt from `inputs.task` on `workflow_dispatch` (empty → the
  fixed `agentdev:pr-review` review prompt), leaving the `issues` and non-PR
  free-form paths as they are
  - **Evidence:** `Determine agent prompts` — `requestedTask` is `dispatchTask`
    on `workflow_dispatch`, `isReview` is `wantsReview || isReviewRequest`, the
    `issues` branch of `mentions` and the `issueText` fallback are untouched;
    same commit.
- [x] Move the run-link footer step to read `inputs.comment_id` and
  `inputs.comment_kind`, so a dispatched review annotates the comment that
  requested it
  - **Evidence:** `Append run link to Claude review request` runs only on
    `workflow_dispatch` with a `comment_id` and an empty `task`; it fetches the
    body by id for each of the three `comment_kind` values (issue comment,
    review comment, review) and updates it through the matching API; same
    commit.
- [x] Key concurrency so `pull_request`-event runs for one PR share a group,
  cancelling in progress only on `synchronize` (a newer push supersedes an
  unfinished review of an older head, and the new run reviews it if no review
  exists; `review_requested`, `assigned`, and the other activity types queue
  behind a running review instead of cancelling it, since none of them starts a
  replacement review) and `workflow_dispatch` runs are keyed by
  `inputs.comment_id`, never cancelled by a push
  - **Evidence:** the `concurrency:` block — `pr-<number>` group for
    `pull_request`, `dispatch-<comment_id>` for `workflow_dispatch`,
    `cancel-in-progress` is the expression
    `event_name == 'pull_request' && action == 'synchronize'`; same commit.

### Task 3: The gate job depends on the review job

**Files:** Modify: `.github/workflows/ai-responder.yml`; Delete:
`.github/workflows/require-ai-review.yml`

- [x] Add job `ai-review-present` with `needs: [preflight, claude-respond]`,
  `if: always()`, `timeout-minutes: 10`, and the gate's current read-only
  permissions, that: skips on `merge_group`; passes when
  `needs.claude-respond.result == 'success'` **and** the composite action
  reports `found`; fails when the review job failed or was cancelled; and
  otherwise passes if and only if the composite action reports `found`
  - **Evidence:** the `ai-review-present` job at the end of
    `.github/workflows/ai-responder.yml` — `if: always() && <PR-bearing event>`,
    read-only permissions, `timeout-minutes: 10`; `Verify AI reviewed PR` exits
    0 on `merge_group`, 1 on a `failure`/`cancelled` review job, and otherwise
    `[[ "${REVIEW_FOUND}" == 'true' ]]`. Committed as "feat(ai-responder): the
    gate job depends on the review job".
- [x] Keep the trusted-bot waiver (`renovate[bot]`, `dependabot[bot]`) and the
  `log-debug-stats` step
  - **Evidence:** the gate passes
    `trusted-bot-actors: 'renovate[bot],dependabot[bot]'` to the composite
    action, whose waiver reads the PR author; `Log debug stats` closes the job
    with `if: always()`; same commit.
- [x] Delete `require-ai-review.yml`; the required-check context name
  `ai-review-present` is unchanged, so the `main` ruleset needs no edit
  - **Evidence:** `git rm .github/workflows/require-ai-review.yml` in the same
    commit; the new job is `name: ai-review-present`.
- [x] `actionlint` and `zizmor` pass
  - **Evidence:** `pre-commit run actionlint --files …` → Passed; `zizmor` on
    the workflow and the composite action → "No findings to report"; both re-run
    by the pre-commit hooks on the commit.

### Task 4: Bridge PR comment mentions into a dispatch on the head branch

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [x] Add job `bridge`, running only for `issue_comment`,
  `pull_request_review_comment`, and `pull_request_review` events whose body
  opens with `@claude` **and** whose subject is a pull request; it reuses
  preflight's PR resolution and gates (fork → skip, write access → fail)
  - **Evidence:** the `bridge` job in `.github/workflows/ai-responder.yml` —
    `needs: preflight`, `if:` requires `preflight.result == 'success'` (the
    write-access step fails preflight), `is_fork != 'true'`,
    `is_pull_request == 'true'`, and one of the three event names; the `@claude`
    opening is preflight's own `if:`. Committed as "feat(ai-responder): bridge
    PR comment mentions into a dispatch on the head branch".
- [x] With `actions: write`, dispatch this workflow to the PR head branch with
  `pr_number`, `task` (empty when the body opens with `@claude review`, else the
  body), `comment_id`, and `comment_kind`; stop with a failure naming the branch
  when the head branch has no `ai-responder.yml`
  - **Evidence:** `Dispatch the responder on the head branch` — permissions
    `actions: write`, `contents: read`; `repos.getContent` on the head ref turns
    a 404 into `core.setFailed` naming the branch, then
    `actions.createWorkflowDispatch` with `ref: head_ref` and the four inputs;
    same commit.
- [x] Remove the direct review path for those three events so a PR mention is
  answered only through the dispatched run; `issues` events keep their free-form
  path on `main`
  - **Evidence:** `Determine agent prompts` — `wantsTask` returns false when
    `IS_PULL_REQUEST` is true, `wantsReview` is true only for `pull_request`
    events and an empty-task dispatch, so `claude-respond` never runs for a PR
    comment; a mention on a plain issue or on an `issues` event still sets
    `wantsTask`; same commit.
- [x] `actionlint` and `zizmor` pass
  - **Evidence:** `pre-commit run actionlint --files …` → Passed; `zizmor` → "No
    findings to report"; both re-run by the pre-commit hooks on the commit.

### Task 5: Repository documentation names one workflow

**Files:** Modify: `README.md`,
`docs/knowledge/data/architecture/template-boundary.md`

- [x] Rewrite `README.md:141-145` so it describes one workflow contributing
  `ai-review-present`, and drop the `require-ai-review.yml` row from
  `template-boundary.md:159-160`, folding its "satisfiable only with the
  responder" note into the `ai-responder.yml` row
  - **Evidence:** `README.md` "AI pull request review" opens with the
    one-workflow description and its trigger paragraph now states the
    push-without-review and comment-bridge behavior; `template-boundary.md`
    keeps one `ai-responder.yml` row carrying the "satisfiable only while the
    responder job is retained" note and gains an `ai-review-status/` row;
    `ai-review-event-selection.md`'s two gate mentions name the
    `ai-review-present` job. Committed as "docs: one AI review workflow".

### Task 6: Prove the flow on a real pull request

**Files:** none — CI evidence

Stands alone: every item's evidence is a run GitHub produces. The comment bridge
is testable only after the workflow is on `main`, because GitHub resolves
`issue_comment` against the default branch's file.

- [x] A PR opened from this branch shows `ai-review-present` pending on its head
  SHA until `claude-respond` completes, then passing, in the same run
  - **Evidence:** PR #97, run 33712475591 (`pull_request` `opened`, head
    `5e03697`): `claude-respond` posted the `github-actions[bot]` COMMENTED
    review, then `ai-review-present` was created, ran, and passed in the same
    run. GitHub creates the gate job only once its `needs` complete, so during
    the review the required check reads as expected-but-unreported on the head
    SHA; the ruleset blocks merge in that state exactly as for a pending job.
- [x] A push to a PR with an accepted review runs the gate only (review job
  skipped) and passes without a poll
  - **Evidence:** PR #97, run 33713536553 (`pull_request` `synchronize`, head
    `55f91d2`, pushed after the `5e03697` review): preflight success,
    `claude-respond` skipped, `bridge` skipped, `ai-review-present` success; the
    run finished within a minute of the push.
- [x] A push to a PR with no accepted review runs the review job and the gate
  passes on its result
  - **Evidence:** throwaway PR #99 (closed): a second commit pushed while the
    `opened` review of `f8a2ba5` was running cancelled that run (33714763006 —
    review job cancelled, gate failed on the superseded head) and run
    33714813477 (`synchronize`, head `56fc89a`) found no accepted review, ran
    `claude-respond` to success, and `ai-review-present` passed.
- [x] After merge: an `@claude review` comment produces a `workflow_dispatch`
  run filed on the PR head branch, running the branch's file, with the run link
  appended to the comment and the check visible in `gh pr checks`
  - **Evidence:** throwaway PR #101 (closed): comment 5528342317 produced bridge
    run 33775175948 (`issue_comment`, on `main`'s file) which dispatched run
    33775210264 on `scratch/ai-review-item4`, head `3d4d5b0`. That run's
    preflight authorized the forwarded requester, `claude-respond` posted an
    APPROVED review on `3d4d5b0`, `ai-review-present` passed, and all four
    checks are filed on the head commit. The run link was appended to the
    comment body. Two prior gates had to be opened for this to work — see
    [dispatched-review identity](../architecture/dispatched-review-identity.md).
- [x] After merge: a comment on a fork PR or from a non-writer dispatches
  nothing
  - **Evidence:** fork PR #105 from `we-are-code-artisans` (permission `read`,
    head `we-are-code-artisans/agent-devcontainer`, head `681a5be`): run
    33776829317 skipped preflight, `claude-respond`, and `bridge` before any
    checkout, posted no review, and `ai-review-present` failed with "No AI
    review found", so merge stays blocked rather than passing unreviewed. GitHub
    additionally held all four workflow runs at `action_required` until a
    maintainer approved them, a gate upstream of the workflow's own.

## Spec changes

[AI review gate](../spec/ai-review-gate.md) — contract-heavy: acceptance
criteria and the security gate change shape.

``` markdown
## MODIFIED Requirements

### Requirement: PRs are blocked until an AI review exists

A pull request SHALL NOT be mergeable until either Claude or Codex has reviewed
it. The `ai-review-present` check SHALL accept a review from `claude[bot]` or
`github-actions[bot]`, a review from `chatgpt-codex-connector[bot]`, or a `+1`
reaction from `chatgpt-codex-connector[bot]`, in state `approved`,
`changes_requested`, or `commented`.

The check SHALL NOT require that the review name the pull request's current head
commit. It asserts that the pull request has been reviewed, not that each pushed
commit has been. Refreshing a review is the author's call, requested with an
`@claude review` comment the way a human re-review is re-requested.

The check SHALL be a job of the same workflow as the review job, depending on
it, so that it is pending for as long as a review of the pull request is
running in that workflow run, and it SHALL evaluate without polling.

#### Scenario: a reviewed PR receives a further push

- **WHEN** an accepted AI review exists on the pull request and the author
  pushes a commit after it
- **THEN** the review job is skipped and `ai-review-present` passes on the
  existing review.

#### Scenario: an unreviewed PR receives a further push

- **WHEN** no accepted AI review exists on the pull request and the author
  pushes a commit
- **THEN** the review job runs and `ai-review-present` reports its outcome.

#### Scenario: Claude reviews a PR through the responder workflow

- **WHEN** the review job in a run posts a review on a pull request
- **THEN** `ai-review-present` in that run passes once the job completes, and
  is pending until then.

#### Scenario: the review job fails

- **WHEN** the review job in a run fails or is cancelled
- **THEN** `ai-review-present` in that run fails.

#### Scenario: Codex reviews a PR through Codex web

- **WHEN** a maintainer runs a Codex review outside GitHub Actions and it posts
  as `chatgpt-codex-connector[bot]`
- **THEN** the review event re-runs the workflow and `ai-review-present`
  passes.

#### Scenario: no AI has reviewed

- **WHEN** the review job did not run in a run and no accepted review exists on
  the pull request
- **THEN** `ai-review-present` fails, blocking merge.

### Requirement: the responder only acts for authorized same-repository requests

The responder SHALL NOT check out or execute code for a pull request originating
from a fork, and SHALL NOT act on a request from an actor without write access.
Both gates SHALL apply before a dispatch is issued for a comment and again in the
dispatched run.

#### Scenario: a fork PR triggers the responder

- **WHEN** the pull request head repository differs from the workflow repository
- **THEN** preflight records the fork, no dispatch is issued, and every
  responder job is skipped before any checkout.

#### Scenario: a user without write access mentions @claude

- **WHEN** the requesting actor's permission is not `admin`, `maintain`, or
  `write`
- **THEN** preflight fails, no dispatch is issued, and no responder job runs.

## ADDED Requirements

### Requirement: a review runs on first push and on explicit request

The review job SHALL run when a pull request is opened, marked ready for
review, reopened, or assigned; when a `workflow_dispatch` requests it; and on a
push to a pull request that has no accepted review. It SHALL NOT run for a
`pull_request` event on a draft pull request.

#### Scenario: a draft is opened

- **WHEN** a pull request is opened as a draft
- **THEN** no review runs until the pull request is marked ready for review.

### Requirement: comment mentions run the pull request branch's workflow

A `@claude` mention opening a comment, review, or review comment on a pull
request SHALL be answered by a `workflow_dispatch` of this workflow on the
pull request's head branch, so the run executes the branch's own workflow file
and its checks attach to the head commit.

#### Scenario: a maintainer comments `@claude review`

- **WHEN** a writer opens a pull request comment with `@claude review`
- **THEN** a run of this workflow starts on the head branch, reviews the pull
  request, and appends its run link to the comment.

#### Scenario: the head branch has no workflow file

- **WHEN** the pull request's head branch does not carry `ai-responder.yml`
- **THEN** the bridge fails naming the branch, and no review runs.
```

[Template consumption](../spec/template-consumption.md) — simple: its "AI
responder and the review gate" section SHALL describe one workflow file that
both answers mentions and contributes `ai-review-present`, and the
`workflow_dispatch` trigger SHALL be listed alongside the default-branch
requirement for comment mentions.

## Verification

- `pre-commit run actionlint --all-files` and
  `pre-commit run zizmor --all-files` pass.
- `git ls-files .github/workflows` no longer lists `require-ai-review.yml`.
- `gh api repos/:owner/:repo/rulesets/20021618` still lists `ai-review-present`
  as a required check, unchanged.
- Task 6's runs, read from `gh run list --workflow ai-responder.yml` and
  `gh pr checks`, show the pending-then-passing gate in one run and the
  dispatched run filed on the head branch.
- `grep -rn require-ai-review README.md docs/knowledge` returns only the shipped
  plans and log entries that record its history.

## Out of scope

- **A push during a running review.** The new head's gate passes on the prior
  review while the older head's run is pending. Closing that window needs a gate
  that discovers other runs, which the maintainer rejected in favour of plain
  `needs:` coupling.
- **Reviewing every commit.** The acceptance policy stays as specified.
- **Simplifying the `pr-*` skills** that compensate for comment runs being
  invisible on the head SHA. Filed as
  [Simplify the pr-* skills for the single review workflow](../backlog/simplify-pr-skills-single-review-workflow.md).
- **Posting reviews under the Claude App identity.** Attribution is unchanged.
- **Loosening or tightening the acceptance rule** (the `+1` reaction and
  `commented` state stay accepted).

## Key references

Verified anchor points (line numbers as of 2026-09-03):

- `.github/workflows/ai-responder.yml:3-22` — the `on:` block the
  `workflow_dispatch` and gate triggers join
- `.github/workflows/ai-responder.yml:25` — the concurrency group Task 2 rekeys
- `.github/workflows/ai-responder.yml:46-62` — preflight `if:`, the owner and
  `startsWith('@claude')` gates
- `.github/workflows/ai-responder.yml:75-110` — `Determine checkout ref`, the PR
  resolution and fork gate preflight extends for `workflow_dispatch`
- `.github/workflows/ai-responder.yml:112-135` —
  `Authorize responder requester`, the write-access gate the bridge reuses
- `.github/workflows/ai-responder.yml:137-201` — `Determine agent prompts`,
  where `inputs.task` joins the prompt selection
- `.github/workflows/ai-responder.yml:203-220` — `claude-respond` job header,
  `if:`, permissions, `timeout-minutes: 30`, environment
- `.github/workflows/ai-responder.yml:222-253` — the run-link footer step that
  moves to the dispatch inputs
- `.github/workflows/ai-responder.yml:315` — `github_token`, the reason a Claude
  review fires no workflow event
- `.github/workflows/require-ai-review.yml:3-19` — the gate's trigger set merged
  into the responder
- `.github/workflows/require-ai-review.yml:30-33` — `ai-review-present`, the job
  name and `timeout-minutes: 10` that carry over
- `.github/workflows/require-ai-review.yml:45,66-74` — the trusted-bot waiver
- `.github/workflows/require-ai-review.yml:90-172` — the acceptance predicates
  the composite action absorbs
- `.github/workflows/require-ai-review.yml:209-243` — the 8-minute poll that is
  dropped
- `.github/workflows/require-ai-review.yml:249-253` — `log-debug-stats`, kept
- `README.md:141-145` — the two-workflow description Task 5 rewrites
- `docs/knowledge/data/architecture/template-boundary.md:159-160` — the two
  workflow rows Task 5 merges
- `docs/knowledge/data/spec/template-consumption.md:323-343` — the matched-pair
  section the spec change rewrites
