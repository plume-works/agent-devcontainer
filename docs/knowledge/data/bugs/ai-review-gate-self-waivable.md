---
type: bug
description: A marker in the author-controlled PR body skipped the required ai-review-present job, and a skipped job satisfies a required status check, so any PR author could waive the mandatory AI review.
generated:
  by: claude-code/opus-5
  at: 2026-09-12T04:50:59Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: https://github.com/Dr-QP/Dr.QP/pull/454#discussion_r3991170588
stage: done
---

# AI review gate was self-waivable from the PR body

## Symptom

`ai-review-present` is a required status check, but a pull request whose body
contained `[ci:no-review]` merged without any AI review. The check reported
`skipped`, and branch protection treats a skipped required check as satisfied.

The waiver was available to anyone who could open a pull request — the PR body
is author-controlled, and neither the marker read nor the gate's `if:` applied
the write-access check the responder request path already used.

## Reproduction

Open a pull request with `[ci:no-review]` anywhere in its description. The
review responder is skipped, `ai-review-present` is skipped, and the merge
button turns green with no review on the pull request.

## Root cause

The marker was wired into two places that serve different purposes. Suppressing
the *review run* is a legitimate author convenience; suppressing the *gate* is a
security boundary, and the same marker did both.

The gate additionally re-read the marker straight from
`github.event.pull_request.body`, so events that never run preflight also
skipped it — widening the same hole rather than closing it.

## Fix

The marker, renamed `[ci:skip-ai-review]` so its scope is legible, now reaches
only `wantsReview`, which gates the review responder. `ai-review-present` no
longer consults it in any form: the preflight output it read was removed along
with the payload `contains` check, so the gate runs on every event it applies to
and fails when no accepted review exists.

A marked pull request therefore skips the AI run and keeps a red gate. Merging
it takes ruleset bypass, which is a permission, not a string in a text field.

Rejected: gating the marker behind `getCollaboratorPermissionLevel`, as the
responder request path does. It keeps the waiver mechanism and only narrows who
holds it, so a writer can still merge unreviewed work with no trace in the
branch protection record. Ruleset bypass expresses the same intent through a
permission GitHub already audits.

The contract is in [AI review gate](../spec/ai-review-gate.md).

## Key references

Verified anchor points (line numbers as of 2026-09-12):

- `.github/workflows/ai-responder.yml:184-185` — the marker read, now output as
  `skipAiReview`
- `.github/workflows/ai-responder.yml:251-259` — the only consumer: the review
  responder's `wantsReview`
- `.github/workflows/ai-responder.yml:477-480` — the gate's `if:`, with no
  marker term
