---
type: bug
description: The review opt-out marker matched anywhere in a PR body, so prose about it disabled review, and it outranked an explicit @claude review request, leaving a marked PR with no way to get one.
generated:
  by: claude-code/opus-5
  at: 2026-09-12T05:31:29Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: https://github.com/plume-works/agent-devcontainer/pull/141
stage: done
---

# The review opt-out marker fired too broadly

## Symptom

Two independent over-reaches of the same marker.

A pull request that *documents* `[ci:skip-ai-review]` disabled review on itself.
The preflight test was `body.includes('[ci:skip-ai-review]')`, which a migration
note or a backtick-quoted mention satisfies exactly as well as a deliberate
directive.

A marked pull request could not then obtain a review by asking. `@claude review`
on it produced no review responder, so the marker was unreachable from the
comment path that exists to request one.

## Reproduction

Open a pull request whose body explains the marker — one sentence naming it in
backticks is enough. The review responder is skipped and `ai-review-present`
fails with `Review job: skipped. No AI review found.` Comment `@claude review`
on that pull request: the bridge dispatches, preflight runs, and the review
responder is skipped again.

## Root cause

`skipAiReview` was a substring test. A marker is a directive, and a directive
needs a form that prose cannot accidentally take; a bare substring has no such
form.

The precedence bug is structural rather than textual. In `wantsReview` the
`SKIP_AI_REVIEW` early-return stood above the `workflow_dispatch` branch, so it
decided before the code that recognizes an explicit request. A bridged
`@claude review` arrives as an empty-task dispatch and never reached that
branch.

## Fix

The marker is matched only as a whole line, allowing surrounding whitespace:
`/^[^\S\r\n]*\[ci:skip-ai-review\][^\S\r\n]*\r?$/m`. The character class
excludes newlines so `^` and `$` cannot span lines, and the optional `\r`
accepts the CRLF bodies the GitHub API returns.

`wantsReview` checks the dispatch branch first, so an explicit request outranks
the marker. The marker sets a default for the pull request; it is not a veto
over a maintainer asking for a review.

Both are narrowings — a body that carried a deliberate own-line marker behaves
as it did before. The contract is in
[AI review gate](../spec/ai-review-gate.md).

## Key references

Verified anchor points (line numbers as of 2026-09-12):

- `.github/workflows/ai-responder.yml:182-185` — the own-line marker match
- `.github/workflows/ai-responder.yml:251-258` — `wantsReview`, dispatch branch
  above the marker early-return
- `.github/workflows/ai-responder.yml:333-341` — the bridge, which never
  consulted the marker and already dispatched for a marked pull request
