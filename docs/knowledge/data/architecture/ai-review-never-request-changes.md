---
type: architecture
description: The AI reviewer submits COMMENT or APPROVE only, never REQUEST_CHANGES, because GitHub blocks REQUEST_CHANGES on a reviewer's own PR and the blocking power lives in inline threads, not the review event.
generated:
  by: claude-code/opus-4-8
  at: 2026-09-01T05:20:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .github/workflows/require-ai-review.yml
- resource: https://github.com/Dr-QP/Dr.QP/commit/d836554c11984d3116f454dcb19a1e08d8e43349
---

# AI review never requests changes

## Decision

The `pr-review` skill submits its GitHub pull request review with event
`COMMENT` when any validated finding survives, and `APPROVE` when none does. It
never submits `REQUEST_CHANGES`, regardless of finding severity. Severity tiers
still drive dedup priority and inline-comment emphasis, but they do not select
the review event. The rule is stated at four points in `pr-review/SKILL.md` (the
event-decision step, the tier definitions, the Codex path, and the
`post-review.sh` fallback contract).

## Why

Two independent reasons, either sufficient:

1. **GitHub blocks `REQUEST_CHANGES` on a reviewer's own pull request.** The
   responder posts reviews as `github-actions[bot]` under `github.token` (see
   [AI review gate](../spec/ai-review-gate.md); the gate accepts `claude[bot]`
   and `github-actions[bot]`). When that identity is also the PR's effective
   author, the API rejects `REQUEST_CHANGES`, forcing a retry with `COMMENT`. A
   mandated event that must be caught and downgraded at every call site is a
   liability, not a gate.
2. **The event is cosmetic in this repository's merge model.** The `main`
   ruleset sets `required_approving_review_count: 0`, so a review verdict never
   enters `reviewDecision` and never gates merge. The one review-driven merge
   block is `required_review_thread_resolution` — an unresolved **inline
   thread**. A `COMMENT` review carries inline threads exactly as
   `REQUEST_CHANGES` would, so the blocking power is identical.
   `REQUEST_CHANGES` adds a false signal ("this blocks merge") that the ruleset
   does not honor, while adding nothing the inline threads do not already
   provide.

Consequently the only means by which an AI review gates a merge here is leaving
an **unresolved inline thread**. The review event and the review body are both
advisory. This is the same fact that makes a review-level body (the `pr-review`
metadata gate) unable to block merge: it creates no thread. See
[AI review gate](../spec/ai-review-gate.md) for what the gate accepts.

## Alternatives rejected

**Map severity tier to event (`REQUEST_CHANGES` for blocking findings).** This
was the original design and was briefly mandatory. It was reverted the same day
it was made authoritative, once the own-PR rejection surfaced on a live
responder run: it required a retry-to-`COMMENT` fallback at every call site and
bought no additional merge enforcement.

**Keep `REQUEST_CHANGES` with a retry-to-`COMMENT` fallback.** Correct but
carried three copies of the same catch-and-downgrade logic (main step, Codex
path, `post-review.sh`) to produce an outcome identical to always using
`COMMENT`. Dropped in favor of the simpler rule.

## Consequences

- A human reader of the PR sees `COMMENT`, not `REQUEST_CHANGES`, even for a
  critical finding. The severity is conveyed in the inline comment text and the
  summary, not the review state.
- Merge blocking depends entirely on `required_review_thread_resolution`: a
  finding gates merge only while its inline thread is unresolved. A finding that
  cannot be anchored to a line (a PR-wide judgment posted as a review body) does
  not gate merge at all.
- The rule is portable. It holds in any repository where the AI reviewer's
  identity can coincide with the PR author, which is the normal case for a
  same-repository responder running on `github.token`.

## Provenance

The rule was inherited into this repository with the `pr-review` skill when the
`agentdev` catalog was extracted from the Dr.QP workspace. It originated in
Dr.QP commit `d836554c1` (2026-07-06, "Drop REQUEST_CHANGES from pr-review
skill, always use COMMENT"), whose message states the own-PR rejection as the
cause. The extraction carried the rule but not that rationale, which is why this
note records it on this side.
