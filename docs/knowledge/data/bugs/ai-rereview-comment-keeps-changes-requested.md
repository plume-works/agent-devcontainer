---
type: bug
description: An AI re-review that submits COMMENT never replaces the reviewer's own earlier CHANGES_REQUESTED, so the pull request stays blocked until a person dismisses the review.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T19:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: data/architecture/ai-review-event-selection.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/542
- resource: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
---

# Bug: an AI re-review that comments leaves its own change request blocking merge

## Symptom

A pull request the AI reviewer once marked `CHANGES_REQUESTED` stays blocked
after the author fixes it and a re-review finds only anchored or non-blocking
issues. On [#542](https://github.com/plume-works/agent-devcontainer/pull/542)
`github-actions[bot]` approved, then requested changes, then re-reviewed with a
`COMMENTED` review; the merge stayed blocked until the maintainer dismissed the
change request, and merged six seconds later. The ruleset required zero
approving reviews at the time.

## Reproduction

1. Get a `REQUEST_CHANGES` review from the AI reviewer — for example from the
   Step 3 metadata gate on a pull request with a stale description.
2. Fix the cause and request a re-review by removing the author as assignee and
   adding them back.
3. Let the re-review find any inline-anchored finding, blocking or not.
4. The review is submitted as `COMMENT`; the pull request still reports the
   bot's change request and cannot merge without a dismissal or bypass.

## Root cause

GitHub keeps a reviewer's `CHANGES_REQUESTED` until that same reviewer approves
or the review is dismissed, and a pending change request blocks merge even when
the ruleset requires zero approvals. A `COMMENT` review from the same reviewer
does not replace it.

`pr-review` Step 9 chooses `COMMENT` whenever every blocking finding is anchored
inline or only non-blocking findings remain, so a re-review in that state can
never lift its own earlier change request. The rule's rationale in [AI review
event selection](../architecture/ai-review-event-selection.md) rests on the
premise that the review verdict never gates merge at zero required approvals,
which does not hold.

## Fix

Not yet fixed. The reviewer stops choosing `COMMENT`: no findings or only
non-blocking findings submit `APPROVE`, and any blocking finding submits
`REQUEST_CHANGES`, so a clean re-review always replaces an earlier change
request.

## Key references

Verified anchor points (line numbers as of 2026-10-30):

- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:149` — Step 9 event
  selection
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:152` — the `COMMENT`
  branch
- `docs/knowledge/data/architecture/ai-review-event-selection.md:36` — "Why
  prefer COMMENT over REQUEST_CHANGES for anchored findings"
