---
name: iwe-audit
description: Audit documents and code comments for session residue — provenance, defended alternatives, dated tool behavior — and prune it or restate it as a verified durable fact. Use when cleaning up docs, pruning stale rationale, or reviewing comments for noise. Proving a rewrite preserved meaning belongs to /agentdev:semantic-refactor-audit.
---

# Durable-knowledge audit

Audit <TARGET> for session residue: text that records how something was
discovered rather than what a reader needs to know. Prune it, or restate it as
a durable fact — but only after verifying the fact against the code.

## Durable vs not

- Durable — the decision and who made it, the constraint it creates, the
  invariant that must hold, the interface. Survives a reimplementation.
- Not durable — how the decision was reached, what broke on the way, a tool's
  behavior on one day, the alternative that was almost written, whether
  something was hard to find. Dies with the code that provoked it.

Test: would this still be true if the code were rewritten from scratch?

## Scope

Audit: `data/spec/`, `data/architecture/`, `data/features/`, `product.md`, and
code comments. These promise durable content.

Do not audit: `data/plans/`, `data/bugs/`, `data/releases/`, `data/log.md`.
Process detail is their job. Residue in a spec may belong in one of these —
that is a move, not a deletion.

## 1. Collect candidates

Seed with grep, then read around each hit — the pattern is a smell, not a
verdict:

- Provenance: `turned out|we found|originally|previously|used to|at the time|
cost a debugging session|in one run|discovered`
- Defensive adverbs: `deliberate|deliberately|intentionally|on purpose|
note that|worth noting|be aware|keep in mind`
- Rejected alternatives: `rather than|instead of|as opposed to` — flag when the
  named alternative does not exist in the current code
- Dated third-party behavior: a named external tool plus a present-tense claim
  about how it behaves
- Generalization from one incident: `surprises|people often|commonly|tends to`
- Comments only: over 3 lines; restates the line below it; commented-out code

## 2. Classify

- **DROP** — provenance, obstacle narration, defense of a draft nobody else saw,
  adverbs that assert nothing. Deleting must not delete a fact: if the sentence
  carries a real constraint, that constraint becomes a REWRITE, not a deletion.
- **MOVE** — real process detail that belongs in a plan or bug doc. Name the
  destination.
- **REWRITE** — a durable fact currently phrased as a discovery. State it as a
  decision or a constraint. If the decision-maker and reason are not recoverable
  from the repo, state the constraint alone. Never invent a rationale to fill
  the gap left by deleted provenance.
- **KEEP** — passes the test as written.

## 3. Verify before promoting

Nothing becomes a durable fact on the strength of the prose already asserting
it. For every REWRITE and KEEP, confirm it against the current code and cite
`file:line`. Cannot confirm → mark UNVERIFIED and leave the text alone; report
it as needing a human. A stale claim restated confidently is worse than the
sloppy version, because it now reads as settled.

## 4. Report, then apply

Output a table before editing anything: `file:line` | quoted text | pattern |
verdict | replacement | evidence. Wait for approval.

When applying: no note in the document saying it was audited, no changelog
entry, no "(revised)" markers. The audit leaves no trace but a shorter file.
