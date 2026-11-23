# Archive

Finished work is archived, never deleted. `data/archive/` has one folder for
each cut version, and the folder `next-release`. Each folder has the subfolder
that its documents were in: `plans/`, `bugs/`, `backlog/`, `adr/`, or a retired
type's folder. No schema is bound under `data/archive/`: archived documents are
not validated.

- The session that closes a plan, a bug, a task, or an ADR moves it with
  `iwe rename` to `data/archive/next-release/<folder>/` in the same change that
  closes it, and removes its link from its hub. The stage table of each type
  shows which stages are in the archive.
- The release cut moves all documents under `next-release` to the folder of the
  version, and keeps the subfolders.
- The folder is the only record of the release of a document. No document has a
  `released` field. A document that no plan closed is part of the release that
  was open when the document closed.
- `architecture/` and `features/` hold retired types: a system design note, with
  the alternatives that were rejected, and a proposal of what users must get,
  written before the work.
- The `ship-records` check fails when a document is in the incorrect folder for
  its stage.
