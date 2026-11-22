---
type: adr
stage: accepted
supersedes:
- adr/0058-ai-review-verdict-follows-severity
---

# AI review findings carry a verdict and a priority

`pr-review` gives every candidate finding one of three verdicts on whether the
issue exists at the head commit: `HOLDS`, `UNSETTLED`, or `REFUTED`. A `HOLDS`
finding is posted with a priority from `P1` to `P3` that weighs its impact with
how likely its trigger is, an `UNSETTLED` one is posted as a Question with no
priority, at most three per review, and a `REFUTED` one is not posted. Only a
`P1` finding, a defect on a trigger met in normal use, or the metadata gate
requests changes; every other review approves, and its threads hold the merge
until resolved. The `main` ruleset accepts only an `APPROVE` from the AI
reviewer, so a review that never approves would block every pull request with a
finding.

## Considered Options

- Blocking by the pass that raised a finding, as ADR-0058 had it. Rejected: a
  doubtful or cosmetic correctness finding blocked, and a convention could never
  block.
- A 0–10 Confidence beside the priority, with cut-offs between bands. Rejected:
  the same finding's Confidence moves across a cut-off from one run to the next,
  so its label changes by chance.
- Drop every finding the validator cannot confirm. Rejected: real issues the
  files cannot settle never reach the author.

## Consequences

- Trigger likelihood belongs to the priority, never to the verdict: a mechanism
  the files verify `HOLDS` even when its trigger is uncommon.
- A reply in an earlier thread holds unless the files at the head commit
  contradict it, so an answered finding is not posted again.
- An outcome that a document in the repository records as an accepted trade-off
  is `REFUTED`; a guarantee the change states and breaks is not.
