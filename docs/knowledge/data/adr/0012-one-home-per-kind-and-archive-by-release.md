---
type: adr
stage: accepted
description: Each kind of knowledge has one document type, and finished work moves to one archive folder for each release, with one subfolder for each type.
---

# Each kind of knowledge has one home, and the archive is by release

The user decided that the graph layout must not repeat knowledge and must stay
simple. For this reason, each kind of knowledge has one document type. A feature
is a proposal that goes to the archive with the plan that implements it. Ship
never deletes finished work. It moves the work to `data/archive/next-release/`
and then to the folder of its release. That folder has one subfolder for each
type, so that the schema of its type still applies.

## Considered Options

- A smaller validation for documents in the archive. Rejected: the user chose
  full validation. A schema change applies to the archived documents of that
  type in the same change.

## Consequences

- The archive folder is the only record of the release of a document, so
  `.iwe/schemas/plan.yaml` refuses a `released` field.
- Ship writes no release page. Only the release cut writes
  `data/releases/<X.Y.Z>.md`, so no file collects the work that is not yet
  released, and parallel Ship runs do not edit the same file.
