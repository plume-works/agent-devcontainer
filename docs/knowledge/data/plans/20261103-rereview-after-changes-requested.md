---
type: plan
created: 2026-11-03
release:
- bugs/eval-skips-rereview-after-changes-requested
description: Make pr-eval-review-needed request a re-review whenever the AI reviewer's newest verdict is CHANGES_REQUESTED, because only that reviewer's own APPROVE lifts its change request; the scope test decides whenever no AI change request is pending.
sources:
- resource: .agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md
- resource: docs/knowledge/data/spec/ai-review-refresh.md
- resource: docs/knowledge/data/archive/1.0.0/architecture/ai-review-event-selection.md
stage: done
completed: 2026-11-03
released: 2.1.0
---

# Re-request an AI review after a change request

## Context

Fixes [Bug: the re-review evaluation skips a re-review after a change
request](../bugs/eval-skips-rereview-after-changes-requested.md).

`pr-eval-review-needed` asks only whether the diff since the newest reviewed
commit goes beyond what reviewers asked for. Under [AI review event
selection](../archive/1.0.0/architecture/ai-review-event-selection.md) the AI
reviewer's verdict gates merge: the `main` ruleset needs one approving review,
and a pending `CHANGES_REQUESTED` stands until the same reviewer approves or a
person dismisses it. A push that applies exactly what a change request asked for
is therefore the push that most needs a re-review, and a scope-only test skips
it.

## Approach

The evaluation reads the AI reviewer's newest verdict before it applies the
scope test. When that verdict is `CHANGES_REQUESTED`, it requests a re-review
whatever the diff holds, and reports the verdict as the reason. When it is
`APPROVED`, the scope test decides. The AI reviewer is the author the [AI review
gate](../spec/ai-review-gate.md) accepts — `claude[bot]` or
`github-actions[bot]` — and its newest verdict is its latest review in state
`APPROVED` or `CHANGES_REQUESTED`; a later `COMMENTED` review does not replace
it, matching how GitHub keeps a reviewer's verdict.

Assumption: an AI reviewer with only `COMMENTED` reviews is left to the scope
test. `COMMENT` is submitted only when GitHub refuses a verdict on the
reviewer's own pull request, where a re-review cannot approve either.

Rejected: requesting a re-review on every push while no AI approval exists. It
would also re-request after a `COMMENTED`-only review, which cannot produce an
approval, and it adds a review per push in that state for no gain.

## Implementation Steps

### Task 1: The evaluation reads the newest AI verdict first

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md`

- [x] `## The test` opens with the verdict check: when the AI reviewer's newest
  verdict is `CHANGES_REQUESTED`, request a re-review regardless of the diff,
  because only that reviewer's `APPROVE` lifts its change request; the scope
  question applies whenever no AI change request is pending.
  - **Evidence:** commit 699047b7 opens `## The test` with the verdict check,
    and commit 466aa4a3 sends every other verdict, `COMMENTED`-only included, to
    the scope test;
    `validate_agent_files --recommend . --require-marketplace claude` reported
    61/61 skills valid on 466aa4a3.
- [x] The **No** branch and the "Do not request a review when" list say they
  apply only while no AI change request is pending.
  - **Evidence:** commit 466aa4a3 conditions both on no AI change request being
    pending; `validate_agent_files` reported 61/61 skills valid on that commit.
- [x] `## Establish what the last review saw` names the AI reviewer's logins and
  says its newest verdict is its latest `APPROVED` or `CHANGES_REQUESTED`
  review, read from the `reviews` query the section already runs.
  - **Evidence:** commit 699047b7 adds the paragraph after the `reviews` query,
    naming the logins in both the `gh pr view` and REST forms;
    `validate_agent_files` reported 61/61 skills valid on that commit.
- [x] `## Report the decision` says a request made for a change request names
  that verdict as the reason.
  - **Evidence:** commit 699047b7 changes the Requesting bullet to name the
    pending change request; `validate_agent_files` reported 61/61 skills valid
    on that commit.
- [x] The frontmatter `description` names a pending AI change request as a
  reason to request a review.
  - **Evidence:** commit 699047b7 rewrites the `description`;
    `validate_agent_files` reported 61/61 skills valid on that commit.

## Spec changes

[AI review refresh](../spec/ai-review-refresh.md) — the evaluation requirement
gains the verdict check, and the scenario for applied feedback is limited to an
approved pull request.

``` markdown
## MODIFIED Requirements

### Requirement: every push to a reviewed pull request is evaluated

After any push to a pull request that has an accepted AI review, made through
`pr-open`'s update mode (and so `pr-sync`), `pr-merge`'s CI-fix step, or
`pr-feedback-resolution`, the agent SHALL apply `pr-eval-review-needed` and
report its decision, whether or not it requests a review. When the AI
reviewer's newest verdict — its latest review in state `APPROVED` or
`CHANGES_REQUESTED` — is `CHANGES_REQUESTED`, the evaluation SHALL request a
review whatever the diff holds. Otherwise the evaluation SHALL ask whether the
diff since the newest reviewed commit goes beyond what the pull request's review
threads and review comments since that review asked for, read from the pull
request rather than from the session that made the change.

#### Scenario: pr-sync pushes undirected behavior

- **WHEN** a reviewed pull request gains a behavior change no review thread
  asked for and `pr-sync` updates it
- **THEN** the run reports a re-review decision and requests a fresh review.

#### Scenario: an update only applies requested feedback

- **WHEN** the AI reviewer's newest verdict is `APPROVED` and the diff since the
  newest reviewed commit only applies what the review threads and comments since
  that review asked for
- **THEN** the agent reports that no review is requested.

#### Scenario: an update answers a change request

- **WHEN** the AI reviewer's newest verdict is `CHANGES_REQUESTED` and the diff
  since that review only applies what its threads asked for
- **THEN** the agent requests a fresh review and reports the change request as
  the reason.
```

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- A change request from a human reviewer: lifting it is that reviewer's call.
- `pr-merge`'s merge-blocker handling, which already reports a missing required
  approval before merging.
- `request-review.py`: its once-per-head guard already allows a request on a
  head no AI review names, which every push produces.

## Key references

- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md › "Decide whether work just pushed to an open pull request"`
  — `description`
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md#the-test` —
  `## The test`;
  `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md#the-test › "— the diff only applies what those threads and comments"`
  — the **No** branch
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md#what-counts-as-beyond-the-feedback › "Unless an AI change request is pending, do not request a"`
  — "do not request a review when" list
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md#establish-what-the-last-review-saw`
  — `## Establish what the last review saw`
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md#report-the-decision`
  — `## Report the decision`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::reviewed`
  — accepted AI reviewer logins
- `docs/knowledge/data/spec/ai-review-refresh.md#requirement-every-push-to-a-reviewed-pull-request-is-evaluated`
  — Requirement: every push to a reviewed pull request is evaluated;
  `docs/knowledge/data/spec/ai-review-refresh.md#scenario-an-update-only-applies-requested-feedback`
  — Scenario: an update only applies requested feedback
