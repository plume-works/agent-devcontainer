---
type: architecture
description: Why the reachable-scenario correctness bar remains experimental after a mixed replay result, and why validator strictness must be isolated before changing the shipped PR review skill.
generated:
  by: codex/gpt-6
  at: 2026-10-04T21:58:34Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: data/plans/20260929-pr-review-scenario-bar-spike.md
---

# PR review correctness bar

## Decision

Keep the shipped `pr-review` correctness bar unchanged. The reachable-scenario
variant produced a mixed result: both #203 runs found K2–K6, including the
out-of-diff K4 ordering bug, while only one #199 run validated K1. The other
#199 run raised K1 as its sole candidate and dropped it during validation.

The spike therefore does not justify shipping the variant or rejecting its
direction. Validator strictness is the open question. Any follow-up experiment
must isolate validation from candidate generation and preserve the pass and
validator records needed to explain a dropped candidate.

## What the result establishes

The reachable-scenario correctness passes can find state-dependent and
out-of-diff bugs without adding correctness noise. Their only validated finding
outside the known-bug key was the real macOS `sha256sum` startup failure.

The experiment did not meet its holding criterion. K1 failed validation in one
variant run, and total review noise exceeded the per-PR threshold. The noise
does not implicate the correctness variant: every noise finding came from the
compliance or durable-knowledge pass, which the variant did not change, and
variant noise stayed at or below baseline noise on both pull requests.

## Validator question

The next experiment must answer why the same reachable K1 scenario survived one
validator and failed another. It closes when preserved validator evidence shows
whether the failure comes from the validation bar, missing scenario context, or
run variance, and a repeated replay demonstrates the chosen correction without
weakening the high-confidence gate.

Replay sessions used as evidence must retain their subagent records. An
ephemeral run that preserves only candidates and final findings cannot explain
why a validator dropped a candidate.

## Rule-checking noise is separate

The rule-checking noise has independent owners:

- codebase-map metadata needs a broader review-ignore boundary than stale
  `source_digest` values alone;
- durable-knowledge review must respect `pr-review`'s file lens and preserve
  `iwe-audit`'s load-bearing-comment guard;
- compliance review must distinguish agent scratch rules and example values from
  product constraints, and helper annotation rules from repository practice for
  test functions;
- the comment rule corrected in `2ef1717` now permits short reasons that code
  cannot express and requires a knowledge-base reference only when a matching
  document already records the rationale.

These issues should not be used either to accept or reject the
reachable-scenario bar.

## Rejected alternatives

**Ship the variant because it found K4 twice.** Rejected because K1's validation
was not repeatable, so the experiment did not meet its stated bar.

**Reject the variant because the runs contained noise.** Rejected because the
noise came exclusively from unchanged rule-checking passes and did not increase
relative to baseline.
