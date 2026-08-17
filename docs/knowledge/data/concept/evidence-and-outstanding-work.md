---
type: concept
description: Evidence and outstanding work never share a heading, and an artifact never restates what an automated check or another document already asserts.
generated:
  by: claude-code/opus-5
  at: 2026-08-15T00:00:00Z
sources:
- resource: docs/knowledge/data/bugs/plan-checkbox-over-claiming.md
- resource: .github/pull_request_template.md
---

# Evidence and outstanding work

Two rules about any document that reports on the state of work — a plan, a pull
request body, a release note. They are one idea seen from two sides: a reader
should be able to tell, per line, whether they are being *told something* or
*asked for something*.

## Evidence and outstanding work never share a heading

A claim about the past ("I ran this, it was green") and a claim about the future
("someone must run this") differ in everything that matters to a reader. The
first is falsifiable now and can be trusted without acting. The second is
falsifiable later or never, and transfers work to whoever is reading.

Putting both under one heading — `## How to Test`, `## Verification` — forces
the reader to re-derive the distinction line by line, from tense and mood alone.
They will get it wrong, and the failure is asymmetric: outstanding work read as
evidence is silently dropped, which is exactly the shape of
[plan checkbox over-claiming](../bugs/plan-checkbox-over-claiming.md).

The section boundary should carry the meaning, so that nothing which has not
happened can be written under the heading that means "done".

**An item whose evidence is external — a CI run, a deploy, a review, a rebuild —
always stands alone and names who can close it.** The session writing the
document cannot close such an item, so the document must not present it as
closed. Naming the closer is what makes this actionable rather than decorative:
a reviewer told "closed by: the checks on the current head" knows to wait, and a
reviewer told "closed by: a human with the devcontainer" knows not to skip it in
silence. An automated reviewer has no hands, and a document that forgets this
hands work to a reader who cannot perform it.

## An artifact asserts only what nothing else already asserts

Restating a claim that another artifact owns creates two copies that drift, and
the copy in the summarizing document is always the one that goes stale — it is
written once and never re-run.

Two corollaries:

- **What an automated check covers, the document omits.** A green CI run is a
  better assertion than a sentence claiming the same thing: it is re-evaluated
  on every push, and the sentence is not. Listing "linting passed" alongside a
  linter that runs on every commit adds no information and can contradict the
  build.
- **What another document owns, the document references.** A plan carrying
  per-task evidence is the record of that evidence; a pull request body links to
  the plan rather than restating its contents.

What survives both cuts is the residue: the things no automated check covers and
no other document records. That residue is small, and it is the only part worth
a reader's attention.

## Consequences

- Sections defined by tense, not by topic.
- Verification sections that shrink as CI coverage grows — which is the correct
  direction. A long verification section is evidence of a coverage gap, not of
  diligence.
- A cost: deciding what CI already covers requires knowing what CI does. A
  document written without that knowledge will either duplicate or omit wrongly,
  and omitting wrongly is the more dangerous error.

Applied to pull request bodies by
[PR verification sections](../architecture/pr-verification-sections.md).
