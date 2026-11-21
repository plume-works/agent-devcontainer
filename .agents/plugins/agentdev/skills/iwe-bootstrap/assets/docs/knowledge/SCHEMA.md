# Document types

This file and the documents in `schema/` are the only definition of the document
types in `data/`. This file gives what goes where. Each document in `schema/`
defines one type or one shared rule: what the type holds, the path, the
frontmatter, the body, and the stages. No other file gives these again. A
document, a skill, or an agent rulebook that needs a definition names the
document, for example `docs/knowledge/schema/bugs.md`.

The schemas in `.iwe/schemas/*.yaml` enforce the shapes. The `[schemas]` section
of `.iwe/config.toml` binds each schema to a path, and each document under
`data/` has a binding, hubs included. `iwe schema validate` must exit 0 before a
commit.

The examples in these documents describe one fictional product (Pomodux, a
focus-timer app). The `*.example.md` documents show each shape in place.

`data/` is a conformant [Open Knowledge
Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
v0.2 bundle. That is why each document has a `type`, and why `data/index.md` has
a shape of its own.

## What goes where

Each kind of knowledge has one home, and no type repeats the content of a
different type: a statement with two homes drifts in the one that nobody
maintains.

| Knowledge                                             | Home                                      | Writer                                  |
| ----------------------------------------------------- | ----------------------------------------- | --------------------------------------- |
| How the product behaves                               | The code and its tests                    | The change that builds the behaviour    |
| What the product is, its constraints, authoring rules | `data/product.md` (`schema/trackers.md`)  | `/agentdev:iwe-setup`                   |
| A project term                                        | `data/glossary.md` (`schema/glossary.md`) | The change that settles the term        |
| A principle that stays true in each release           | `schema/product-vision.md`                | `/agentdev:iwe-explore`                 |
| An idea that is not a commitment                      | `schema/someday-ideas.md`                 | `/agentdev:iwe-explore`                 |
| Work that one session can complete                    | `schema/backlog-tasks.md`                 | `/agentdev:iwe-capture`                 |
| A defect in shipped behaviour                         | `schema/bugs.md`                          | `/agentdev:iwe-capture`                 |
| What users must get, written before the work          | `schema/features.md`                      | `/agentdev:iwe-capture`                 |
| Committed work: its tasks, acceptance, and checks     | `schema/plans.md`                         | `/agentdev:iwe-plan`                    |
| A design decision and its reason                      | `schema/adrs.md`                          | `/agentdev:iwe-plan`                    |
| A measurement that does not yet settle a question     | `schema/findings.md`                      | The session that made the measurement   |
| A procedure that a contributor repeats                | `schema/guides.md`                        | The session that found the procedure    |
| What one release changed                              | `schema/releases.md`                      | The release cut of `/agentdev:iwe-ship` |
| Finished work                                         | `schema/archive.md`                       | The session that closes the work        |

The Home column names a document in `schema/`, or a file. In each path that
these documents give, a `<slug>` is a short name in kebab case, and one document
has one topic.

Plans, features, bugs, ADRs, releases, and backlog tasks are work items. A work
item has a `stage`. Findings, guides, product-vision documents, and someday
ideas are durable reference documents. A reference document has a `type` and no
`stage`, because nothing about it is a lifecycle.

## Rules that all types share

- `schema/fields-every-type-carries.md` — the frontmatter fields of each
  document.
- `schema/build-order.md` — the `rank` field and the build order.
- `schema/code-anchors.md` — the forms of a code anchor.
- `schema/hubs.md` — the hub of each type.
- `schema/trackers.md` — the trackers.
- `schema/glossary.md` — the format and the rules of the glossary.
- `schema/index-file.md` — `data/index.md`.
- `schema/archive.md` — where finished work goes.
