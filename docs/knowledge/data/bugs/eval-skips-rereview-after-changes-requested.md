---
type: bug
stage: done
severity: medium
description: pr-eval-review-needed decides by scope alone, so after a push that applies exactly what a CHANGES_REQUESTED AI review asked for it requests no re-review, and the pull request stays blocked because only that reviewer's own APPROVE lifts its change request.
sources:
- resource: .agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md
- resource: docs/knowledge/data/spec/ai-review-refresh.md
- resource: openspec/specs/ai-review-gate/spec.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/654
---

# Bug: the re-review evaluation skips a re-review after a change request

## Symptom

After the author fixes what a `CHANGES_REQUESTED` AI review asked for,
`pr-eval-review-needed` reports that no re-review is needed. The pull request
stays blocked: the `main` ruleset requires one approving review, and GitHub
keeps the reviewer's change request until that same reviewer approves or a
person dismisses it. Seen on
[#654](https://github.com/plume-works/agent-devcontainer/pull/654): the AI
review on `5ed40228` requested changes, the push of `eca72817` applied exactly
the two threads, and `pr-feedback-resolution` reported "not requested".

## Reproduction

1. Get a `REQUEST_CHANGES` review from the AI reviewer on a pull request.
2. Push a commit that applies only what its threads asked for.
3. Apply `pr-eval-review-needed`, as `pr-feedback-resolution` does at the end of
   a feedback pass.
4. It answers **No** — the diff only applies requested feedback — and requests
   no review. `gh pr view` still reports `mergeStateStatus: BLOCKED`.

## Root cause

The skill's test asks only whether the diff since the newest reviewed commit
goes beyond what the review threads and comments asked for, and never reads the
newest review's verdict. The "every push to a reviewed pull request is
evaluated" requirement in [AI review refresh](../spec/ai-review-refresh.md)
specifies exactly that, and its scenario "an update only applies requested
feedback" requires that no review be requested, with no exception for a blocking
verdict.

The rule rests on a premise that no longer holds: that re-reviewing applied
feedback only re-reads the reviewer's own instructions. Under [AI review event
selection](../../../../openspec/specs/ai-review-gate/spec.md#rationale) the AI
reviewer's verdict gates merge, and only its own `APPROVE` lifts its earlier
`CHANGES_REQUESTED`, so a re-review is the step that unblocks the pull request.

## Potential solution

Read the AI reviewer's newest verdict before the scope test: when it is
`CHANGES_REQUESTED`, request a re-review whatever the diff holds. The scope test
decides only when that verdict is `APPROVED`.

## Fix

`pr-eval-review-needed` reads the AI reviewer's newest verdict — its latest
`APPROVED` or `CHANGES_REQUESTED` review — before the scope test. While that
verdict is `CHANGES_REQUESTED` it requests a re-review whatever the diff holds
and names the change request as the reason; otherwise the scope test decides.
The contract is the [AI review refresh](../spec/ai-review-refresh.md)
requirement "every push to a reviewed pull request is evaluated", changed by
[Re-request an AI review after a change
request](../plans/20261103-rereview-after-changes-requested.md).

## Key references

- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md#the-test` —
  `## The test`;
  `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md#the-test › "review saw."`
  — the **No** branch
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md#what-counts-as-beyond-the-feedback › "outside the one raised."`
  — "Do not request a review when" list
- `docs/knowledge/data/spec/ai-review-refresh.md#requirement-every-push-to-a-reviewed-pull-request-is-evaluated`
  — Requirement: every push to a reviewed pull request is evaluated;
  `docs/knowledge/data/spec/ai-review-refresh.md#scenario-pr-sync-pushes-undirected-behavior › "asked for and"`
  — Scenario: an update only applies requested feedback
- `openspec/specs/ai-review-gate/spec.md#why-the-verdict-follows-severity › "blocks merge until the same reviewer approves or"`
  — a pending `CHANGES_REQUESTED` blocks merge until the same reviewer approves
