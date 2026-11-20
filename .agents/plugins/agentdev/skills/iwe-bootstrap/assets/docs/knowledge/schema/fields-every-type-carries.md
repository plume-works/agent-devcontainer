# Fields every type carries

The optional families of OKF, the Open Knowledge Format (SPEC §4.1, §5), are on
each schema. `.iwe/schemas/okf.yaml` checks them.

- `type` — required on each document under `data/`, with one exception:
  `data/index.md`.
- `description` — one sentence. Each document has one. An OKF tool and
  `data/index.md` show it before a reader opens the file.
- `sources` — the materials that a document derives from. Each entry is
  `{ id, resource, title, author, usage_count, last_modified }`, and `resource`
  is required. A `resource` is a URL or a repository path. To attribute one
  claim, use a Markdown footnote with the `id` of the entry as its label.
- `resource`, `tags`, `stale_after`, `usage_window` — optional.

`stage` is the only lifecycle field. The state of a work item — its `stage`,
`priority`, `completed`, and `rank` — lives only in its own frontmatter, and no
hub repeats it, so a state change edits one file that only its own pull request
touches.

The workspace diverges from OKF only to cut merge and upkeep cost. No document
sets the optional `status` of OKF, so a state change edits one field. No
document sets `generated` or `verified` of OKF: source control records when a
document changed and who changed it.
