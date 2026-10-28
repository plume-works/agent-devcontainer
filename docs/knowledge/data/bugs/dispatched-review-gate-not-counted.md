---
type: bug
description: The ai-review-present check that a comment-requested review's workflow_dispatch run files on the head commit is not counted by the merge ruleset, so that review neither holds a merge while it runs nor unblocks a red gate when it lands.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-25T19:10:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: docs/knowledge/data/spec/ai-review-gate.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/472
- resource: https://github.com/plume-works/agent-devcontainer/pull/468
- resource: https://github.com/plume-works/agent-devcontainer/pull/101
stage: done
---

# Bug: a comment-requested review's gate does not count toward merge

## Symptom

An `@claude review` comment runs the review as a `workflow_dispatch` of
`ai-responder.yml` on the pull request's head branch. That run's
`Claude PR Review Responder` and `ai-review-present` check runs land on the head
commit, but the pull request's status rollup leaves them out, so they don't
appear in `gh pr checks`, `statusCheckRollup`, or the merge box. The `main`
ruleset requires `ai-review-present` and evaluates only the check from the
`pull_request`-event run. Two consequences follow:

- **A requested review does not hold a merge.** If the `pull_request`-event gate
  is already green from an earlier accepted review, the pull request stays
  mergeable while the requested review runs. Auto-merge can land it before the
  review publishes. [One AI review workflow with a needs-coupled
  gate](../plans/20260903-single-ai-review-workflow.md) set out to close this
  gap for comment-requested reviews.
- **A requested review does not unblock a red gate.** When the
  `pull_request`-event gate failed, for example on a body marked
  `[ci:skip-ai-review]`, the dispatched run's passing gate and its accepted
  review leave the pull request `BLOCKED`. It stays blocked until a later
  `pull_request` event re-runs the gate, in practice the next push.

## Reproduction

1. Open a same-repository pull request whose body carries `[ci:skip-ai-review]`
   alone on a line. The `pull_request` run skips the review job, and its
   `ai-review-present` fails.
2. Comment `@claude review`. The bridge dispatches the review on the head
   branch. The review job posts an accepted review on the head commit, and the
   dispatched run's `ai-review-present` passes.
3. `gh pr view <pr> --json mergeStateStatus` reports `BLOCKED`. The GraphQL
   `statusCheckRollup` lists only the `pull_request` run's checks, with the
   failing `ai-review-present` as the one failing required check.
   `repos/{owner}/{repo}/commits/<sha>/check-runs` lists both gates.

Observed on throwaway PR #472 (head `be74664`, closed unmerged). The
`pull_request` gate failed at 18:46:47Z and the dispatched gate passed at
18:50:50Z, with an APPROVED `github-actions` review on `be74664`. Afterwards
`mergeStateStatus` was `BLOCKED`, the other three required checks passed, the
ruleset requires no approvals, and no review thread was unresolved. PR #468
(head `293ddf0`) and PR #101 (head `3d4d5b0`) show the same rollup exclusion:
each dispatched suite is linked to its pull request, yet neither rollup lists
it.

## Root cause

GitHub's pull request rollup, and the required-status-check evaluation that
follows it, include check suites from the pull request's own events and leave
out the suite a `workflow_dispatch` run creates on the head branch. That holds
even though the suite reports the pull request in `pull_requests` and its check
runs share the required check's name and app.
[spec/ai-review-gate](../spec/ai-review-gate.md) couples the gate to the review
job with `needs:`, and that coupling holds only inside one run. The bridge moves
comment-requested reviews into a separate, dispatched run, so the coupled gate
it produces is one the ruleset never reads. The posted review creates no
`pull_request_review` event either, because the review job posts with
`GITHUB_TOKEN`. So nothing re-runs the `pull_request` gate once the review
lands.

## Fix

Unfixed, and no direction has been chosen yet. Any fix must get a counted
`ai-review-present` result onto the head commit after a comment-requested review
finishes, and keep it pending while that review runs. Candidates to weigh at
planning time:

- the dispatched run re-runs the latest `pull_request`-event run of
  `ai-responder.yml` for the head
- the review is posted under an identity whose review raises a
  `pull_request_review` event
- the gate is reported in a form the ruleset reads from any run

The skills in [PR skills drive the AI review lifecycle on the single review
workflow](../plans/20261023-pr-skills-ai-review-lifecycle.md) work around this
behavior rather than fixing it.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.github/workflows/ai-responder.yml:33` — `workflow_dispatch` trigger the
  bridge targets
- `.github/workflows/ai-responder.yml:363` — `bridge` job
- `.github/workflows/ai-responder.yml:412` — `createWorkflowDispatch` on the
  head branch
- `.github/workflows/ai-responder.yml:509` — `ai-review-present` job
- `.github/workflows/ai-responder.yml:513` — `needs: claude-respond`, which
  couples the gate to the review only within one run
- `.github/workflows/ai-responder.yml:517` — the gate's condition admitting an
  empty-task `workflow_dispatch`
- `docs/knowledge/data/spec/ai-review-gate.md:31` — the gate is pending while a
  review runs "in that workflow run"
- `docs/knowledge/data/spec/ai-review-gate.md:122` — an explicit request
  outranks the skip marker
- `docs/knowledge/data/spec/ai-review-gate.md:228` — dispatched checks "attach
  to the head commit"
- `docs/knowledge/data/plans/20260903-single-ai-review-workflow.md:33` — the
  in-flight-review gap that plan set out to close
