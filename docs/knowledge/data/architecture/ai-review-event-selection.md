---
type: architecture
description: The AI reviewer picks its review event from finding severity alone — APPROVE for no or only non-blocking findings, REQUEST_CHANGES for any blocking finding — because the one-approval main ruleset needs its approval and only its own APPROVE lifts its earlier change request.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T21:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .github/workflows/ai-responder.yml
- resource: https://github.com/Dr-QP/Dr.QP/commit/d836554c11984d3116f454dcb19a1e08d8e43349
- resource: https://github.com/Dr-QP/Dr.QP/pull/409
---

# AI review event selection

## Decision

The `pr-review` skill selects its GitHub pull request review event from the
severity of the validated findings alone:

| Validated findings          | Event             |
| --------------------------- | ----------------- |
| none                        | `APPROVE`         |
| non-blocking only           | `APPROVE`         |
| any blocking, inline or not | `REQUEST_CHANGES` |

The Step-3 metadata gate is a blocking finding and submits `REQUEST_CHANGES`.
`COMMENT` is never a chosen event; it is only the retry when GitHub rejects a
verdict because the reviewer owns the pull request (see below).

The rule is stated in `pr-review/SKILL.md` at the event-decision step, the tier
definitions, the Codex single-call option, and the `post-review.sh` fallback
contract. The Codex single-call tool accepts only `APPROVE` or `COMMENT`, so a
Codex review that must request changes posts through `post-review.sh`.

## Why the verdict follows severity

The `main` ruleset requires one approving review, keeps stale reviews on push,
and requires every review thread to be resolved. The AI reviewer's `APPROVE`
satisfies the required approval (see [Actions approval
permission](actions-approval-permission.md)), and a `COMMENT` never does. Two
consequences fix the rule:

- A review that should not block must `APPROVE`, or the pull request cannot
  merge without ruleset bypass.
- A pending `CHANGES_REQUESTED` blocks merge until the same reviewer approves or
  the review is dismissed. A clean re-review must therefore `APPROVE` to replace
  the reviewer's own earlier change request; a `COMMENT` leaves it standing.

Inline comments on an approving review still open threads, and thread resolution
holds the merge until each is resolved, so approving with non-blocking findings
loses no enforcement. Blocking findings always block: an approval shown beside
an unaddressed blocking finding would read as sign-off on it.

See [AI review gate](../spec/ai-review-gate.md) for what the gate accepts.

## The self-review API rule

GitHub rejects **both** verdict events — `APPROVE` and `REQUEST_CHANGES` — when
the reviewer identity equals the pull request **author** identity; only
`COMMENT` is allowed on one's own pull request. This is an identity-collision
rule, not a "same token" rule.

It fires only on a pull request authored by the reviewer identity itself —
`github-actions[bot]` under `github.token`, or `claude[bot]` under OIDC App
auth. A human-authored pull request reviewed by the bot is a cross-identity
review. That is why the skill retries a rejected `APPROVE` or `REQUEST_CHANGES`
as `COMMENT` with a note in the body. Bot-authored pull requests get no AI
review here: `ai-responder.yml` skips `pull_request.user.type == 'Bot'`, and its
`trusted-bot-approval` job approves the bots listed in `TRUSTED_BOT_ACTORS`
instead.

## Alternatives rejected

**`COMMENT` for anchored blocking findings.** The superseded rule: `COMMENT`
when every blocking finding was attached inline, `REQUEST_CHANGES` only for a
blocking finding with no inline anchor. It assumed merge was gated by thread
resolution alone. Under the one-approval ruleset a `COMMENT` neither satisfies
the required approval nor replaces the reviewer's earlier change request, so a
pull request it reviewed needed a clean re-review or ruleset bypass to merge.

**`APPROVE` with anchored blocking findings, relying on thread resolution.** The
open thread would still hold the merge, but blocking findings always block: an
approval beside an unaddressed blocking finding reads as sign-off on it.

**Ban `REQUEST_CHANGES` unconditionally (`COMMENT` for every finding).** A
blocking finding then never blocks through the verdict, and no review ever
satisfies the required approval.

## Consequences

- A review with only non-blocking findings is an `APPROVE` with inline comments;
  merge waits only for those threads to be resolved.
- A review with any blocking finding is `REQUEST_CHANGES`, and the pull request
  stays blocked until a later review from the same reviewer approves it.
- Every merge through the ruleset carries an approval from the AI reviewer or
  the trusted-bot approval job, unless it is merged by bypass.

## Provenance

The `pr-review` skill was inherited from the Dr.QP workspace, where commit
`d836554c1` ([Dr.QP PR #409](https://github.com/Dr-QP/Dr.QP/pull/409)) banned
`REQUEST_CHANGES` under a ruleset that required no approving review.
