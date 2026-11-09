---
name: pr-merge
description: 'Merge an open GitHub pull request: monitor CI and AI review, resolve conflicts and remediate failures and feedback, then squash merge it explicitly once every requirement passes. Use when a PR needs to be merged or shepherded through CI and review to merge. Keywords: merge PR, squash merge, monitor PR, merge-ready, wait for CI, CI failures, AI review, Claude Responder.'
---

# Merge PR

Drive one open pull request through the complete CI-and-review cycle and merge
it explicitly with a squash merge once conflicts, checks, feedback, and reviews
are all resolved. Never enable auto-merge. This is a persistent workflow: wait
for the relevant GitHub state to change, then act on the new state.

## When to Use This Skill

- A pull request has just been opened and must be merged after CI and review.
- Someone asks to merge, babysit, or shepherd a PR through CI and review.
- CI is still running, an automated AI review is pending, or review feedback
  must be addressed before merging.

Do not use this skill for a draft, closed, or merged PR unless the user first
asks to change that state.

## Prerequisites and Scope

- Resolve the PR from an explicit number or URL, or use the current branch:

  ```bash
  gh pr view --json number,url,headRefName,headRefOid,isDraft,state
  ```

- Verify GitHub CLI authentication before monitoring:

  ```bash
  gh auth status
  ```

- Check the PR's base branch:

  ```bash
  gh pr view <pr> --json baseRefName --jq .baseRefName
  ```

  This skill merges only into `main`. A PR based on any other branch is a
  dependent pull request with unmerged pull requests below it: stop without
  merging, and point the user at `/agentdev:pr-merge-stack` for its top pull
  request.

- Work from an isolated worktree. If the caller did not provide one, create
  one under `./.tmp/` after resolving the PR number and head branch.
  If current branch matches the PR head branch, use it directly.

  ```bash
  mkdir -p ./.tmp
  git fetch origin <head-branch>
  git worktree add --detach ./.tmp/pr-merge-<pr> origin/<head-branch>
  git -C ./.tmp/pr-merge-<pr> switch -c pr-merge-worktree/<pr>
  git -C ./.tmp/pr-merge-<pr> branch --set-upstream-to=origin/<head-branch>
  ```

  Run all local inspection, tests, commits, and pushes from that worktree.
  Push its `HEAD` only to the resolved PR head branch; never push its private
  `pr-merge-worktree/<pr>` name. The upstream set above is what makes the push
  helper target the head branch. Preserve the caller's worktree and unrelated
  local branches. After a confirmed merge, remove only the clean worktree and
  private branch that this skill created; otherwise leave them in place and
  report their path and state.

- Record the initial head SHA, CI check names and URLs, AI-review state, and
  unresolved review threads. Keep this state in the conversation; do not post
  progress comments to the PR.
- Work only on the PR head branch. Preserve unrelated local changes, never
  force-push, and never update its base branch unless
  the user explicitly requests it. This skill's merge workflow authorizes disabling auto-merge and
  performing the final squash merge.
- A remediation requested by this skill is authorized by the user request to
  make the PR mergeable. Still stop for a genuinely ambiguous review request
  and ask for clarification in that review thread.

## Disable Auto-Merge Once

Immediately after resolving the PR and confirming it is open and not a draft,
inspect its automatic merge request:

```bash
gh pr view <pr> --json autoMergeRequest
```

If `autoMergeRequest` is non-null, disable it, so GitHub cannot merge the PR
before its feedback and reviews are resolved, and record that in the final
report:

```bash
gh pr merge <pr> --disable-auto
```

## Completion Criteria

Treat the PR as complete only when all of these are true for its current head
branch:

- It is open and not a draft.
- Every reported CI check has completed successfully. Report external checks
  that cannot be inspected, but do not claim they passed without evidence or
  call the PR merge-ready while one is failing or pending.
- The `ai-review-present` gate is successful and an accepted Claude review
  exists for the PR's current review cycle.
- The review agent has finished; all of its actionable, unresolved feedback is
  fixed, replied to, and resolved using the feedback-resolution workflow.
- `gh pr view` reports no remaining merge blocker (for example, a conflict or
  missing required approval) before the merge is attempted.
- GitHub reports the PR as merged.

## Monitoring Loop

Repeat this loop until the completion criteria are met, the PR becomes closed
or draft, or a non-actionable blocker needs user direction. Use repeated
bounded waits; never replace a wait with a text-only promise to check later.

1. Refresh the PR and capture its head SHA and merge state:

   ```bash
   gh pr view <pr> --json number,url,state,isDraft,headRefName,headRefOid,mergeable,mergeStateStatus,reviewDecision,reviews
   gh pr checks <pr> --json name,state,bucket,link,workflow,startedAt,completedAt
   ```

2. If `mergeable` is `CONFLICTING` or `mergeStateStatus` is `DIRTY`, the PR
   conflicts with its base and its checks will not run. Follow the
   merge-conflict step at the start of
   [pr-feedback-resolution](../pr-feedback-resolution/SKILL.md)'s Workflow 1,
   then restart at step 1. If `mergeable` is `UNKNOWN`, GitHub has not computed
   it yet: restart at step 1 after a bounded wait instead of waiting on checks.

3. If checks are pending or queued, wait in bounded polls (about 60 seconds)
   rather than blocking until every check finishes: `gh pr checks --watch`
   returns only when all checks complete, which delays posted feedback. After
   each poll, refresh both commands above and the unresolved review threads,
   then act on the first of these that holds:
   - A check has failed: go to step 4 now.
   - `Claude PR Review Responder` has completed on the current head, or a new
     review or unresolved thread has been posted: go to step 6 now, while the
     remaining checks keep running.
   - Otherwise keep polling.

4. Classify every completed non-success check before changing code:
   - A GitHub Actions failure: use
     [extract-github-actions-logs](../extract-github-actions-logs/SKILL.md)
     to collect the failing job log and artifacts, then use
     [pr-feedback-resolution](../pr-feedback-resolution/SKILL.md) to diagnose,
     implement, test, commit, and push the focused repair as step 5 does.
   - A CodeQL or Codecov failure: use the same feedback-resolution skill and
     its linked security or coverage workflow.
   - An external check: record its URL and report it as an external blocker;
     do not fabricate a GitHub Actions diagnosis.
   - `ai-review-present`: follow **AI Review Recovery**
     below. Do not try to repair this gate with a code change.
   - A cancelled, timed-out, or infrastructure failure: rerun only when the
     repository permits it and the failure is demonstrably transient;
     otherwise report it as a blocker with its evidence.

5. After a code change, run the narrowest relevant local verification —
   `uv run pytest <path>` or `bun test <path>` for the affected area.
   Commit, then push with the [pr-open](../pr-open/SKILL.md) push helper,
   `agent-code/push-branch.py`, handling its result as that skill's step 8 does.
   After the push, apply
   [pr-eval-review-needed](../pr-eval-review-needed/SKILL.md) and report its
   decision. Restart the loop from step 1 because the head SHA and checks have
   changed.

6. As soon as the review agent has posted on the current head, inspect reviews
   and unresolved review threads; do not wait for the other checks to finish
   first. Apply [pr-feedback-resolution](../pr-feedback-resolution/SKILL.md)
   once to gather and address all actionable feedback together, including any
   check failure already reported, rather than handling comments piecemeal.
   Its resolved-thread filtering and confidence rules are mandatory.

7. If feedback leads to a push, restart at step 1. If no actionable feedback
   remains, keep polling as step 3 does until every check has completed, then
   refresh checks and merge state once more. If the head SHA changed, restart
   at step 1. Otherwise, perform the final squash merge.

## Final Squash Merge

After every pre-merge completion criterion has been evidenced for the current
head SHA, merge the PR explicitly:

```bash
gh pr merge <pr> --squash
```

Confirm first that the base is still `main`, and never pass `--admin`: a merge
GitHub refuses is reported as a blocker, never forced through.

Refresh the PR afterwards and confirm that its state is `MERGED`. If GitHub
rejects the merge because the state changed, return to the monitoring loop;
otherwise report the concrete error as a blocker.

## AI Review Recovery

The `ai-review-present` check accepts a submitted review from Claude. A review is
requested by adding the `request-ai-review` label, which starts a
`pull_request` run of the AI responder workflow: the review's
`Claude PR Review Responder` check and the `ai-review-present` gate that waits on
it are filed on the head commit and listed by `gh pr checks`.

1. Confirm that the failed `ai-review-present` check actually says no accepted
   AI review was found. Inspect its log before triggering anything.

2. If `Claude PR Review Responder` or `ai-review-present` is pending on the
   current head, a review is already running. Wait on it with the bounded polls
   of the monitoring loop's step 3 rather than requesting another.

3. Otherwise request the review through
   [pr-request-ai-review](../pr-request-ai-review/SKILL.md), whose
   `request-review.py` adds the `request-ai-review` label at most once per head
   and title and description. On `ALREADY_REQUESTED`, the label is still waiting
   for a run or a responder check already covers this head: confirm it started as that skill describes and
   wait on the head's checks; never request again. On `ALREADY_REVIEWED`, an
   accepted review newer than the last title or description edit already names
   the head and the failed gate predates it; report that instead of requesting.
   On `BLOCKED`, the pull request carries `block-ai-reviews`, so no review can
   run until a person removes it: report that as a merge blocker and stop
   waiting.

4. Poll until the latest `ai-review-present` run on the head completes — it
   finishes in the same run as the review — then refresh both `gh pr checks`
   and PR reviews, without waiting for the head's other checks. Do not treat an added label, a started run, or a pending
   review as completion.
5. If the responder publishes actionable feedback, return to the review step
   in the monitoring loop and use `pr-feedback-resolution` to address all of
   it. If it publishes a clean review, the gate passes in that same run.
6. If the review job ends without a submitted review, the gate fails in that
   run: inspect its log and report that concrete failure. Do not request it
   again; require a new head SHA or user direction before retrying.

## Final Report

Report the PR URL, merged SHA, merge method, any auto-merge request disabled,
final check status, AI-review outcome, feedback resolved, local verification run, and any remaining external
or policy blocker. Say the PR was merged only after its merged state is
evidenced.

## Related Skills

- [pr-feedback-resolution](../pr-feedback-resolution/SKILL.md) — collect and
  resolve all review feedback and actionable CI findings in one pass.
- [extract-github-actions-logs](../extract-github-actions-logs/SKILL.md) —
  retrieve GitHub Actions logs and uploaded test artifacts.
- [pr-review](../pr-review/SKILL.md) — automated-review behavior used by the
  AI responder workflow.
- [pr-request-ai-review](../pr-request-ai-review/SKILL.md) — request the
  review with the `request-ai-review` label, at most once per head and title
  and description, and confirm it started.
