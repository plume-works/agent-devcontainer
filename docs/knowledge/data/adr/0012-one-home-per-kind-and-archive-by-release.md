---
type: adr
stage: accepted
---

# Each kind of knowledge has one home, and the archive is by release

The user set DRY and KISS as the principles of the graph's layout, so each kind
of knowledge has one home, one document type. A feature is a proposal that is
archived with the plan that implements it. Finished work is archived, never
deleted: Ship moves it to `data/archive/next-release/`, and the release cut
moves it to the folder of its release. Each archive folder has one subfolder per
type, so that every archived document stays under its type's schema.

## Considered Options

- Minimal validation for archived documents. Rejected: the user chose full
  validation, so a schema change is applied to that type's archived documents in
  the same change.

## Consequences

- The archive folder is the only record of a document's release, so no
  `released` field repeats it, and `.iwe/schemas/plan.yaml` refuses one.
- Ship writes no release page. Only the release cut writes
  `data/releases/<X.Y.Z>.md`, so no file accumulates unreleased work, and
  parallel ships do not edit the same file.
