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
3. **It is the result of a real trade-off.** There were real alternatives, and
   one was selected for specific reasons.

These decisions qualify:

- the shape of the architecture;
- an integration pattern between parts of the system;
- a technology that is expensive to replace;
- a boundary or a scope decision, a refusal included;
- a deliberate deviation from the obvious path;
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
give the context, the decision, and the reason. `## Considered Options` and
`## Consequences` are optional, in this order, and the schema permits no other
section. An ADR has an optional section only when the section adds value: the
rejected options, for example, only when a later reader needs them.

- Nobody edits an accepted ADR. A decision that changes gets a new ADR that
  names the earlier ADR in `supersedes`.
- A code comment refers to an ADR as `ADR-NNNN`.
