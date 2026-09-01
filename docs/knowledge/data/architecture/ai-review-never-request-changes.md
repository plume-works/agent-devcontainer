---
type: architecture
description: The AI reviewer submits COMMENT or APPROVE only, never REQUEST_CHANGES, because merge blocking lives in inline threads rather than the review event; the self-review API rule that also forbids it is a bot-authored-PR edge case, not the main reason.
generated:
  by: claude-code/opus-4-8
  at: 2026-09-01T05:40:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .github/workflows/require-ai-review.yml
- resource: https://github.com/Dr-QP/Dr.QP/commit/d836554c11984d3116f454dcb19a1e08d8e43349
- resource: https://github.com/Dr-QP/Dr.QP/pull/409
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

**The review event is cosmetic in this lineage's merge model.** The `main`
ruleset sets `required_approving_review_count: 0`, so a review verdict never
enters `reviewDecision` and never gates merge. The one review-driven merge block
is `required_review_thread_resolution` — an unresolved **inline thread**. A
`COMMENT` review carries inline threads exactly as `REQUEST_CHANGES` would, so
the blocking power is identical. `REQUEST_CHANGES` adds a false signal ("this
blocks merge") that the ruleset does not honor, while adding nothing the inline
threads do not already provide. This reason holds regardless of the reviewer's
identity, and is the robust one.

Consequently the only means by which an AI review gates a merge here is leaving
an **unresolved inline thread**. The review event and the review body are both
advisory. This is the same fact that makes a review-level body (the `pr-review`
metadata gate) unable to block merge: it creates no thread. See
[AI review gate](../spec/ai-review-gate.md) for what the gate accepts.

## The self-review rule is a narrow edge case, not the main reason

GitHub rejects **both** verdict events — `APPROVE` and `REQUEST_CHANGES` — when
the reviewer identity equals the PR **author** identity; only `COMMENT` (no
verdict) is allowed on one's own PR. This is an identity-collision rule, not a
"same token" or "reviewed its own review" rule.

It therefore fires only on a PR **authored by the reviewer identity itself** —
in practice a bot- or automation-authored PR whose author matches the responder
identity (`claude[bot]` under OIDC App auth, or `github-actions[bot]` under
`github.token`). A human-authored PR reviewed by the bot is a normal
cross-identity review, and the bot may submit `APPROVE` or `REQUEST_CHANGES`
without rejection. This repository already keeps bot-authored PRs out of the
responder path (`ai-responder.yml` skips `pull_request.user.type == 'Bot'`, and
`require-ai-review.yml` trust-lists `renovate[bot]`/`dependabot[bot]`), so the
collision case does not arise for the AI reviewer here in normal operation.

The reversal commit (see `## Provenance`) named this API rejection as its cause,
but generalized it: in the originating repository no PR was ever authored by the
reviewer identity, so the rejection never actually triggered there. The durable
justification for dropping `REQUEST_CHANGES` is the cosmetic-event reason above,
not the self-review rule.

### Consequence for a verdict gate

If the gate were changed to `required_approving_review_count: 1`, an AI
`APPROVE` would become load-bearing and would succeed on human-authored PRs
(distinct identities). It would fail only on a PR authored by the reviewer
identity — the same bot-authored edge case — which this repository already
excludes from the responder. The barrier to a verdict gate is therefore a policy
choice (should an AI approval alone unblock merge), not the self-review API
rule.

## Alternatives rejected

**Map severity tier to event (`REQUEST_CHANGES` for blocking findings).** This
was the original design and was briefly mandatory. It was reverted the same day
it was made authoritative: it required a retry-to-`COMMENT` fallback at every
call site to guard against the self-review rejection, and bought no additional
merge enforcement over `COMMENT` under a presence gate.

**Keep `REQUEST_CHANGES` with a retry-to-`COMMENT` fallback.** Correct but
carried three copies of the same catch-and-downgrade logic (main step, Codex
path, `post-review.sh`) to guard an event that can only fail (on an
identity-collision PR) or be redundant (on every other PR). Dropped in favor of
the simpler rule.

## Consequences

- A human reader of the PR sees `COMMENT`, not `REQUEST_CHANGES`, even for a
  critical finding. The severity is conveyed in the inline comment text and the
  summary, not the review state.
- Merge blocking depends entirely on `required_review_thread_resolution`: a
  finding gates merge only while its inline thread is unresolved. A finding that
  cannot be anchored to a line (a PR-wide judgment posted as a review body) does
  not gate merge at all.
- The rule is portable for the robust reason: under any presence-plus-threads
  gate a `COMMENT` review blocks exactly as well as `REQUEST_CHANGES`. The
  self-review rejection is not why it is portable — that fires only on the
  bot-authored-PR edge case, which the responder path already excludes.

## Provenance

The rule was inherited into this repository with the `pr-review` skill when the
`agentdev` catalog was extracted from the Dr.QP workspace. It originated in
Dr.QP commit `d836554c1` (2026-07-06, "Drop REQUEST_CHANGES from pr-review
skill, always use COMMENT"), whose message states the self-review rejection as
the cause. The commit shipped in [Dr.QP PR
#409](https://github.com/Dr-QP/Dr.QP/pull/409) — a PR about flaky launch tests
whose title and body do not mention the skill change, which is why the decision
left no trace outside the commit message. That rationale was over-general: at
that commit the Dr.QP responder reviewed as the `claude[bot]` GitHub App (OIDC,
`id-token: write`), and no Dr.QP PR was ever authored by `claude[bot]`, so the
rejection could not have fired in practice. The tooling failure actually
observed on a live run (sibling commit `81ab18702`, "observed on PR #410's
Claude Responder run", PR #410 authored by a human) was the review MCP tools
being missing, a separate problem. The durable reason the rule is correct is the
cosmetic-event reason under `## Why`. The extraction carried the rule but not
its history, which is why this note records it on this side.
