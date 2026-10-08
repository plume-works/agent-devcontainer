---
type: architecture
description: pr-review ships the reachable-scenario correctness bar with three-part scenarios validated part by part; the light validator judges whether a fault is real rather than whether each stated part holds, so a DROP's named part is diagnostic and a confirmed Outcome may overstate the harm.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-06T10:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: data/plans/20261005-pr-review-scenario-validation.md
---

# PR review scenario validation

## Decision

The maintainer ships the reachable-scenario correctness bar in `pr-review`,
settling the open validator question in
[PR review correctness bar](pr-review-correctness-bar.md):

- **Reach beyond the diff.** Correctness passes read, at the head commit, the
  code the changed lines call, the code that calls them, and the code that runs
  beside them in the same lifecycle or workflow.
- **Reachable scenario.** A correctness finding needs a concrete input or state
  the code can receive at the head commit and the wrong outcome it produces;
  "depends on specific inputs or state" is no longer a reason to stay silent.
- **Three-part scenario.** Every correctness candidate states a **Trigger**, a
  **Path** (`file:line` chain to the fault), and an **Outcome**. Step 5 discards
  a candidate with an empty part before validation.
- **Parts as written.** The validator receives a scenario candidate's three
  parts in place of its claim, judges them in trigger → path → outcome order,
  and returns `CONFIRM` or `DROP: trigger|path|outcome — <reason>`. Candidates
  without a scenario keep their claim and the "clearly a violation" bar.
- **Stated intent is evidence, not a verdict.** A comment or PR description
  presenting behavior as deliberate does not refute a reachable wrong outcome,
  and a guarantee the PR description promises that the code breaks counts toward
  the outcome. The validator prompt says where to read the description.

The validator stays on the `light` model, per
[PR review effort tiers](pr-review-effort-tiers.md).

## What holds

Full-effort Codex replays of #199 and #203 under the shipped skill find every
known bug in every run — the #199 concurrency race and all five #203 bugs,
including the out-of-diff keyring ordering — with no correctness finding judged
noise. Every unmatched correctness finding has a matching fix in the merged pull
request.

## Known limits

- **The validator judges the fault, not the stated parts.** Handed a real fault
  with one part false as written, it still confirms in many runs, reading the
  fault from the parts that hold. A drop's named part is a diagnostic hint, not
  a guarantee of which part failed, and a confirmed finding's Outcome can
  overstate the harm.
- **Permission exposure is not resolved consistently.** Whether a loose-mode
  file is exposed depends on directory modes another script sets; validators
  split on it. Such findings are excluded from this evaluation.
- **A missing Outcome does not by itself explain the spike's K1 drop.**
  Validated alone, the previous bar confirmed outcome-less scenario claims in
  every run; the three-part requirement makes candidates consistent rather than
  rescuing them.

## Rejected alternatives

**Carry the claim alongside the scenario parts.** Given both, the validator
re-derives the claim and confirms candidates whose stated part is false; with
the parts alone, it drops a false Path in most runs.

**Change the validator but keep the diff-only bar.** The K1 drop occurred only
under the reachable-scenario bar, and the part-by-part validator acts only on
the scenario candidates that bar produces.

**Hold the change until the negative controls pass.** The light validator does
not test each part as written under either prompt form, with or without the
claim. The maintainer ships on the full replays' recall and noise result;
validating correctness candidates on the `large` model stays
[a someday idea](../someday/pr-review-large-validator.md).
