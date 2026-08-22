---
name: iwe-audit
description: Audit knowledge-base documents and code comments for session residue — provenance, war stories, defended alternatives, and dated tool behavior — then prune it or restate it as a verified durable fact. Use when asked to clean up docs, prune stale rationale, review comments for noise, check whether a spec still says something worth saying, or when a document has been rewritten several times as a decision changed. Judges whether text deserves to exist; proving a rewrite preserved meaning belongs to /agentdev:semantic-refactor-audit, and reviewing newly written logic belongs to /agentdev:pr-review.
---

# Knowledge Base Audit

Documents and comments accumulate a residue of the sessions that wrote them: how
a thing was discovered, what broke on the way, the alternative that was almost
written, what a third-party tool did on one afternoon. Each sentence looked like
diligence when it was typed. Together they bury the few facts a reader came for,
and they age badly — provenance is the first thing to become false.

Two failure modes make this harder than deletion.

**Cutting the fact along with the noise.** A war story often carries a real
constraint in its final clause. Removing the paragraph removes the constraint,
and nobody notices until it is violated.

**Laundering.** The tempting move is to rewrite a shaky discovery as a confident
decision. That is worse than leaving it: the sloppy version at least read as
uncertain, while the polished one reads as settled and gets planned against. A
fact earns durable phrasing by being checked against the code, not by being
restated well.

## Durable and not

- **Durable** — the decision and who made it, the constraint it creates, the
  invariant that must hold, the interface. Survives a reimplementation.
- **Not durable** — how the decision was reached, what broke on the way, a
  tool's behavior on one day, the alternative that was almost written, whether
  something was hard to find. Dies with the code that provoked it.

The test: _would this still be true if the code were rewritten from scratch?_

## Scope

Audit the documents that promise durable content — specifications, architecture,
feature descriptions, product definition — and code comments.

Leave the documents whose job is process: plans, bug reports, release notes,
session logs. Residue found in a spec sometimes belongs in one of these. That is
a move, not a deletion.

Confine one run to a scope you can finish and report on. A partial sweep of a
directory tells the reader nothing about the rest of it, so say what you covered.

## Workflow

### 1. Collect candidates

Grep for the tells, then read around each hit. A pattern is a smell, never a
verdict — roughly half of any pattern's hits are load-bearing.

| Residue               | Grep for                                                                                     |
| --------------------- | -------------------------------------------------------------------------------------------- |
| Provenance            | `turned out\|we found\|originally\|previously\|used to\|at the time\|discovered\|in one run` |
| Defensive adverbs     | `deliberate\|intentionally\|on purpose\|note that\|worth noting\|be aware\|keep in mind`     |
| Defended alternatives | `rather than\|instead of\|as opposed to`                                                     |
| Generalized from once | `surprises\|people often\|commonly\|tends to`                                                |
| Dated tool behavior   | a named external tool plus a present-tense claim about how it behaves                        |

Two more that grep cannot find, so read for them: a comment longer than three
lines, and a comment that restates the line beneath it.

Where the history is available, a document rewritten in consecutive commits as a
decision changed is a strong candidate — successive drafts leave their arguments
behind in the text.

### 2. Classify each candidate

- **DROP** — provenance, obstacle narration, defense of a draft no reader ever
  saw, adverbs that assert nothing. If the sentence also carries a constraint,
  that constraint becomes a REWRITE. Never a bare deletion.
- **MOVE** — genuine process detail belonging to a plan or bug document. Name
  the destination.
- **REWRITE** — a durable fact currently phrased as a discovery. State it as a
  decision or a constraint. Where the decision-maker and reason are not
  recoverable from the repository, state the constraint alone and stop.
  Manufacturing a rationale to fill the hole left by deleted provenance is the
  worst outcome this skill can produce.
- **KEEP** — passes the test as written.

A defended alternative earns DROP when the alternative it argues against does
not exist in the current code. The argument is then addressed to an earlier
draft, and only its author can see what it is replying to.

### 3. Verify before promoting

No text becomes a durable fact on the strength of already asserting itself.

For every REWRITE and KEEP, confirm the claim against the current code and cite
`file:line`. Where it cannot be confirmed, mark it UNVERIFIED, leave the text
untouched, and report it for a human. Documents under audit are old by
definition; some of what they assert stopped being true before the audit started,
and an unverified rewrite converts a stale claim into an authoritative one.

Deterministic checks only. Reading the code settles this; conviction does not.

### 4. Report, then apply

Produce the table before editing anything, and wait for approval:

| `file:line` | quoted text | pattern | verdict | replacement | evidence |
| ----------- | ----------- | ------- | ------- | ----------- | -------- |

An empty evidence cell on a REWRITE or KEEP means UNVERIFIED, however confident
the replacement text sounds.

When applying, leave no trace of the audit itself — no note that the document
was reviewed, no changelog entry, no revision marker. The audit's only signature
is a shorter file. A record of this pass is exactly the kind of text the next
audit would delete.

## Definition of done

- The audited scope is stated, along with what was excluded.
- Every DROP either removed no fact, or moved its constraint into a REWRITE.
- Every REWRITE and KEEP cites `file:line` evidence, or is reported UNVERIFIED
  and left alone.
- No rationale was invented to replace deleted provenance.
- The documents carry no record of having been audited.

Worked cases for each pattern, drawn from real audits, are in
[worked-cases.md](references/worked-cases.md).
