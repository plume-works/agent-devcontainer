# Archive

Finished work goes to the archive, and nobody deletes it. `data/archive/` has
one folder for each cut version, and the folder `next-release`. Each folder has
the subfolder that its documents were in: `plans/`, `bugs/`, `backlog/`,
`features/`, `adr/`, or `architecture/`. Each archived document keeps the schema
of its type and is validated in full.

- The session that closes a plan, a bug, a task, a feature, or an ADR moves it
  to `data/archive/next-release/<folder>/` with `iwe rename`. The same change
  removes its link from its hub. The stage table of each type shows which stages
  are in the archive.
- The release cut moves all documents under `next-release` to the folder of the
  version, and keeps the subfolders.
- The folder is the only record of the release of a document. No document has a
  `released` field. A document that no plan closed is part of the release that
  was open when the document closed.
- `type: architecture` is valid only under `data/archive/`. It is a retired
  type: a system design note, with the alternatives that were rejected.
- The `ship-records` check fails when a document is in the incorrect folder for
  its stage.
