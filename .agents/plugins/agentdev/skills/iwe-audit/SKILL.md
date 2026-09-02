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

Audit any text that promises durable content: `data/spec/`,
`data/architecture/`, `data/features/`, `product.md`, code comments, and —
outside the graph — `README.md`, `AGENTS.md`, skill and agent definitions, and
docstrings.

Do not audit: `data/bugs/`, `data/releases/`, `data/log.md`, or commit messages.
Process detail is their job; commit messages are owned by
`/agentdev:git-commit`. Residue in a spec may belong in one of these — that is a
move, not a deletion. A plan is audited only in plan mode below, and only its
intent sections: a plan's `## Verification results` and `- **Evidence:**`
children are narrative-sanctioned and stay out of scope.

**Diff scope.** When a caller runs this skill over a diff, the candidate set is
the diff's added lines, not a grep over `<TARGET>`. §1's patterns are the smell
list applied to those added lines. Everything downstream — §"Durable vs not",
§2 verdicts, §3 verify — is unchanged and shared with the local-tree scope.

**Plan scope.** When the `<TARGET>` is a plan, the candidate set is every plan
section except the two narrative-sanctioned homes — `## Verification results`
and the `- **Evidence:**` children under `## Implementation Steps` — which stay
out of scope. `## Context`, `## Approach`, task descriptions, and the rest are
in scope: they state intent and must record what is settled, not the path taken
to settle it. Like Diff scope, this scope is report-only (see §4). Everything
downstream is unchanged and shared with the other scopes.

## 1. Collect candidates

Seed with grep, then read around each hit — the pattern is a smell, not a
verdict:

```bash
# Provenance
grep -rEni 'turned out|we found|originally|previously|used to|at the time|cost a debugging session|in one run|discovered' <TARGET>

# Defensive adverbs
grep -rEni 'deliberate|intentionally|on purpose|note that|worth noting|be aware|keep in mind' <TARGET>

# Rejected alternatives — flag when the named alternative is absent from current code
grep -rEni 'rather than|instead of|as opposed to' <TARGET>

# Generalization from one incident
grep -rEni 'surprises|people often|commonly|tends to' <TARGET>
```

Two more that grep cannot find:

- Dated third-party behavior: a named external tool plus a present-tense claim
  about how it behaves
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

DROP carries the same burden, for the opposite reason: it is the one verdict
that destroys text rather than leaving it in place. Its `evidence` must show the
sentence carries no constraint — the fact it states is asserted elsewhere and
cited `file:line`, or it asserts nothing checkable at all. A sentence that
grep flagged but that constrains behavior is a REWRITE or a KEEP, never a DROP;
`rather than` and `instead of` introduce load-bearing prohibitions as often as
they introduce dead alternatives. Cannot show it → UNVERIFIED, same as above.

## 4. Report, then apply

Output a table before editing anything: `file:line` | quoted text | pattern |
verdict | replacement | evidence. Wait for approval.

**Diff scope and Plan scope stop here.** In either scope the skill is
report-only: it produces the table and stops. Every verdict is a recommendation
— MOVE names the destination, DROP/REWRITE quote the replacement — but the
changed lines are left untouched. Applying is the caller's decision, made
outside this skill.

When applying: no note in the document saying it was audited, no changelog
entry, no "(revised)" markers. The audit leaves no trace but a shorter file.
