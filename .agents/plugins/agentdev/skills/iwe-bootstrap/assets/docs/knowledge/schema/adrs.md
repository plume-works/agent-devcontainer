# ADRs

An ADR records one design decision and its reason.

- Path: `data/adr/NNNN-<slug>.md`. `NNNN` is the next free four-digit number in
  `data/adr/` and `data/archive/*/adr/`.
- Hub: `data/adr.md`.

A decision gets an ADR only when all three of these are true:

1. **It is difficult to reverse.** A later change of the decision has a real
   cost.
2. **It is a surprise without context.** A later reader of the code will ask why
   it is done this way.
3. **It is the result of a real trade-off.** There were genuine alternatives,
   and one was picked for specific reasons.

A decision that is easy to reverse, that is not surprising, or that had no real
alternative gets no ADR.

These decisions qualify:

- the shape of the architecture;
- an integration pattern between parts of the system;
- a technology choice that carries lock-in: not every library, only one that
  would be expensive to swap out;
- a boundary or a scope decision: the explicit refusals are as valuable as the
  acceptances;
- a deliberate deviation from the obvious path, where a reasonable reader would
  assume the opposite;
- a constraint that the code does not show;
- an alternative that was rejected for a reason that is not obvious.

``` yaml
---
type: adr # required
stage: proposed # required: see the table
description: One sentence that gives the decision. # required
supersedes: # optional: the earlier ADRs that this ADR replaces
- adr/0001-code-and-tests-state-behaviour
---
```

The frontmatter has no date field. Git records the date.

| Stage        | Meaning                                        | Set by | Location    |
| ------------ | ---------------------------------------------- | ------ | ----------- |
| `proposed`   | A plan proposes the decision                   | Plan   | `data/adr/` |
| `accepted`   | The plan shipped                               | Ship   | `data/adr/` |
| `rejected`   | The plan was cancelled                         | Ship   | Archive     |
| `superseded` | An accepted ADR names this ADR in `supersedes` | Ship   | Archive     |
| `deprecated` | The decision does not apply now                |        | Archive     |

Body: an H1 that is the short title of the decision, then 1 to 10 sentences that
give the context, the decision, and the reason. The value of an ADR is the
record that a decision was made and why. The schema permits two optional
sections, in this order, and no other section. Include an optional section only
when it adds real value. Most ADRs do not need them.

- `## Considered Options` — only when the rejected alternatives are worth
  remembering.
- `## Consequences` — only when downstream effects that are not obvious need to
  be called out.

These rules also apply:

- Nobody edits an accepted ADR. A decision that changes gets a new ADR that
  names the earlier ADR in `supersedes`. The one exception is a change of
  terminology that follows the glossary and leaves the decision as it is.
- A code comment refers to an ADR as `ADR-NNNN`.
