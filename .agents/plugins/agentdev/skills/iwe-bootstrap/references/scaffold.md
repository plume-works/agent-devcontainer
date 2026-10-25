# Bootstrap scaffold

`assets/` is the complete blank IWE workspace `/agentdev:iwe-bootstrap`
installs, laid out exactly as it lands in a repository root:

- `assets/.iwe/` — the IWE configuration and the schemas that validate the
  graph. `[workspace].path = "docs/knowledge"` makes every document key
  relative to `docs/knowledge/`, and `iwe` runs from the repository root.
- `assets/docs/knowledge/` — the knowledge-base instructions (`AGENTS.md`,
  `SCHEMA.md`, `STRUCTURE.md`, and their companions), the MIT `LICENSE.md`, and
  the starting `data/` graph.

## What the graph contains

- **Hubs and trackers** — one per document type, each carrying the conventions
  its documents follow.
- **`data/product.md`** — the foundation document, left as ✏️ placeholder blocks
  for `/agentdev:iwe-setup` to fill.
- **Onboarding tasks** under `data/backlog/` — `fill-product-doc` and
  `capture-current-architecture` are the two keys `/agentdev:iwe-setup` closes;
  renaming or removing either breaks that skill's closing step.
- **`*.example.md` documents** — fictional documents about a fictional product,
  showing the shape of each type. `/agentdev:iwe-setup` deletes them once real
  documents exist.

## Ownership

The scaffold ships inside the installed catalog and is the only source any
initialization copies from; nothing is fetched at bootstrap time. Its graph
content was imported once from
[plume-works/iwe-dev-workspace](https://github.com/plume-works/iwe-dev-workspace)
at commit `249943bcc30ac1016469d5ee89a16ce454cc882f`, under that project's MIT
license, and is maintained here against the catalog's IWE skills without
tracking that repository.

Once installed, every file belongs to the consuming repository. A catalog update
that changes `assets/` never reaches an initialized workspace.

## Maintenance

The scaffold's schemas, configuration, and knowledge instructions are the same
bytes the publishing repository's own workspace uses, so a schema change is a
scaffold change: adjust the seed documents in the same commit, or the next
bootstrap installs a workspace that fails `iwe schema validate`. Every file
under `assets/` must equal its `iwe normalize` output.

The scaffold is not a member of any live graph: no `.iwe/config.toml` points a
workspace at `assets/`, and `iwe normalize`, not Prettier, owns its Markdown.
