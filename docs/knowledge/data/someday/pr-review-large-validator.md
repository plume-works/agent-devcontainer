---
type: someday
description: Validate pr-review's scenario-carrying correctness candidates on the large model at full effort, pending a cost/benefit evaluation against the recorded light-validator decision.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-05T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
---

# Validate correctness candidates on the large model

At full effort, `pr-review`'s correctness passes run on the `large` model while
every candidate is validated on `light`. A scenario claim — a trigger reachable
at the head commit, the path to the fault, and the wrong outcome — asks the
validator to reason across lifecycles, runs, and files outside the diff, which
is the reasoning the correctness passes get the large model for. Validating
scenario-carrying candidates on `large` at full effort could make their verdicts
more reliable.

It contradicts a recorded decision: [PR review effort
tiers](../architecture/pr-review-effort-tiers.md) fixes validation at `light`
because the gate's strength is its bar rather than its model, because a stronger
model asked to confirm only at high confidence also argues more persuasively for
dropping, and because validation is the only slot whose cost grows with the
number of findings.

## Promotion criteria

A cost/benefit evaluation would settle it:

- **Benefit:** a validator-only replay of a frozen candidate set, comparing
  `light` and `large` per candidate over repeated runs, positives and negative
  controls together. It counts only if `large` raises the confirm rate of real
  scenario candidates without confirming more negatives.
- **Cost:** the added per-candidate validation cost at full effort, given the
  number of correctness candidates a typical full review produces.

The part-by-part verdicts from [Ship the reachable-scenario bar with
part-by-part validation in
pr-review](../plans/20261005-pr-review-scenario-validation.md) show which part a
`light` validator drops, which would aim the evaluation.
