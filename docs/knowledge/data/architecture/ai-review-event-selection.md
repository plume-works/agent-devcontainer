---
type: architecture
description: The AI reviewer prefers COMMENT over REQUEST_CHANGES so an author unblocks by resolving inline threads without forcing a re-review; REQUEST_CHANGES is used only for a blocking finding with no inline anchor, where no thread would gate merge.
generated:
  by: claude-code/fable-5-1
  at: 2026-09-03T03:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .github/workflows/ai-responder.yml
- resource: https://github.com/Dr-QP/Dr.QP/commit/d836554c11984d3116f454dcb19a1e08d8e43349
- resource: https://github.com/Dr-QP/Dr.QP/pull/409
---

# AI review event selection

## Decision

The `pr-review` skill selects its GitHub pull request review event by whether a
blocking finding has a **live inline anchor**:

- no validated findings → `APPROVE`;
- every blocking finding is attached as an inline comment → `COMMENT`;
- at least one blocking finding has no live inline anchor → `REQUEST_CHANGES`.

The anchor-less case is a PR-wide judgment (the metadata gate) or a blocking
finding whose inline location GitHub rejected and that fell back to a prose PR
comment. Non-blocking findings never select `REQUEST_CHANGES`. Severity tiers
still drive dedup priority and inline emphasis; they select the event only
through the anchor test above.

The rule is stated at four points in `pr-review/SKILL.md` (the event-decision
step, the tier definitions, the metadata gate in Step 3, and the
`post-review.sh` fallback contract), and `post-review.sh` accepts all three
events.

## Why prefer COMMENT over REQUEST_CHANGES for anchored findings

A merge in this repo is gated by unresolved **inline threads**
(`required_review_thread_resolution`), not by the review verdict — the `main`
ruleset sets `required_approving_review_count: 0`, so `reviewDecision` never
gates merge. An anchored blocking finding therefore already blocks the merge
through its thread, and the author unblocks by **resolving the thread** once the
finding is addressed — no further review needed.

`REQUEST_CHANGES` on such a finding would add no enforcement (the thread already
blocks) but would set a **sticky `CHANGES_REQUESTED` decision that only a fresh
review can dismiss**. Resolving the threads does not clear it. That forces a
second AI review run purely to lift the verdict — a real cost, in dollars and
latency, for no added blocking. Avoiding that re-review is the reason `COMMENT`
is preferred wherever the finding is anchored.

## Why REQUEST_CHANGES is required for anchor-less findings

A finding with no inline anchor creates no thread, so
`required_review_thread_resolution` has nothing to hold and a `COMMENT` review
gates **nothing** — the merge stays green. This is the case the metadata gate
falls into (it is a review body, PR-wide by nature) and the Step-8 inline-reject
fallback (the finding is posted as a prose PR comment). With no thread
available, the review **verdict is the only lever**, so `REQUEST_CHANGES` is
required to block merge. Its re-review cost is not a drawback here: there is no
thread the author could resolve instead, so a fresh review is the intended way
to clear it.

See [AI review gate](../spec/ai-review-gate.md) for what the gate accepts.

## The self-review API rule (a separate constraint)

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
its `ai-review-present` job trust-lists `renovate[bot]`/`dependabot[bot]`), so
the collision case does not arise for the AI reviewer here in normal operation.

This is why `REQUEST_CHANGES` carries a retry-to-`COMMENT` fallback in the
skill: on a bot- or self-authored PR the verdict event is rejected, and a
`COMMENT` noting the downgrade is the best available. On the normal
human-authored PR the bot is a distinct identity and `REQUEST_CHANGES` succeeds.
This repository already keeps bot-authored PRs out of the responder path anyway
(`ai-responder.yml` skips `pull_request.user.type == 'Bot'`, and its
`ai-review-present` job trust-lists `renovate[bot]`/`dependabot[bot]`), so the
collision rarely arises for the AI reviewer here.

### Consequence for a verdict gate

If the gate were changed to `required_approving_review_count: 1`, an AI
`APPROVE` would become load-bearing and would succeed on human-authored PRs
(distinct identities). It would fail only on a PR authored by the reviewer
identity — the same bot-authored edge case — which this repository already
excludes from the responder. The barrier to a verdict gate is therefore a policy
choice (should an AI approval alone unblock merge), not the self-review API
rule.

## Alternatives rejected

**Map severity tier to event unconditionally (`REQUEST_CHANGES` for every
blocking finding).** The original design, briefly mandatory. Rejected because it
forces a sticky `CHANGES_REQUESTED` verdict on findings that are already
blocking through their inline thread — the author resolves the thread but merge
stays blocked until a fresh AI review dismisses the verdict, an extra review run
for no added enforcement. The `## Why` above is the correction: use
`REQUEST_CHANGES` only where no thread exists to gate.

**Ban `REQUEST_CHANGES` unconditionally (`COMMENT` for every finding).** The
prior state of this skill, and simpler. Rejected because a blocking finding with
no inline anchor — the metadata gate, or a Step-8 inline-reject fallback — then
gates nothing: `COMMENT` sets no verdict and there is no thread, so merge stays
green on a finding meant to block it. The anchor test restores a block for
exactly that case without reintroducing the re-review cost on anchored findings.

## Consequences

- On an anchored finding a human reader sees `COMMENT`, not `REQUEST_CHANGES`,
  even for a critical one; the severity is conveyed in the inline comment text.
  The finding still blocks merge through its thread, and resolving the thread
  unblocks it with no re-review.
- On an anchor-less blocking finding the review is `REQUEST_CHANGES`, and the
  block is lifted only by a fresh review — the intended cost, since there is no
  thread to resolve instead.
- The metadata gate now blocks merge. Before this change it posted a `COMMENT`
  body that gated nothing (see [AI review gate](../spec/ai-review-gate.md)); it
  now posts `REQUEST_CHANGES`.

## Provenance

The rule was inherited into this repository with the `pr-review` skill when the
`agentdev` catalog was extracted from the Dr.QP workspace. It originated in
Dr.QP commit `d836554c1` (2026-07-06, "Drop REQUEST_CHANGES from pr-review
skill, always use COMMENT"), which shipped in [Dr.QP PR
#409](https://github.com/Dr-QP/Dr.QP/pull/409).

The operative reason for preferring `COMMENT` is the re-review cost under
`## Why` (a sticky `CHANGES_REQUESTED` verdict that resolving threads cannot
clear), not the self-review rejection.

That commit made the rule a **blanket** ban on `REQUEST_CHANGES`. This
repository later refined it to the conditional rule under `## Decision`, once
the blanket ban was found to leave anchor-less blocking findings (the metadata
gate) unable to gate merge.
