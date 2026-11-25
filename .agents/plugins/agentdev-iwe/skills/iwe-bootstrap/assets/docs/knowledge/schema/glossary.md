# Glossary

The glossary is the shared language of the project: the concepts that are
specific to this project, each with one name. It is a tracker at
`data/glossary.md`. A single-context project has this one glossary.

## Structure

``` md
# Glossary

{One or two sentences: what the project is and why it exists.}

## Language

### {Cluster}

**Order**: {What the term is, in one or two sentences.} *Avoid*: Purchase,
transaction

**Invoice**: A request for payment sent to a customer after delivery.
```

- Each term is one paragraph: the term in bold, a colon, then the definition.
- `*Avoid*:` ends the paragraph and lists the other words for the same concept.
  Leave it out when there is no other word.
- `###` subheadings group the terms when natural clusters emerge. A flat list
  under `## Language` is fine when all terms belong to one area.

## Rules

- **Be opinionated.** When several words exist for one concept, pick the best
  one and list the others under `*Avoid*`.
- **Keep definitions tight.** One or two sentences. Define what the term is, not
  what it does.
- **Only terms specific to this project.** A general programming or tooling
  concept does not belong, even if the project uses it a lot. Before adding a
  term, ask: is this concept unique to this project? Only then does it belong.
- **No implementation details.** No file path, command, flag, or configuration
  key. The glossary is not a spec, a scratch pad, or a record of decisions: a
  decision goes in an ADR.
- **Update it when a term is settled.** Add or change the entry in the same
  change that settles the term, and challenge a use that conflicts with it.

The format follows the `GLOSSARY-FORMAT.md` of the `domain-modeling` skill in
<https://github.com/mattpocock/skills>.
