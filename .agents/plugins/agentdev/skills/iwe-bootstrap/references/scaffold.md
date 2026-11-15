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

- **Hubs and trackers** — one hub for each document type. `SCHEMA.md` defines
  the types.
- **`data/product.md`** — the foundation document, left as ✏️ placeholder blocks
  for `/agentdev:iwe-setup` to fill.
- **Onboarding tasks** under `data/backlog/` — `fill-product-doc` is the one
  task `/agentdev:iwe-setup` closes; if you rename or remove it, the last step
  of that skill fails.
- **`*.example.md` documents** — fictional documents about a fictional product,
  showing the shape of each type, including a shipped plan and feature under
  `data/archive/0.1.0/`. `/agentdev:iwe-setup` deletes them once real
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

Each checkout of agent-devcontainer is a checkout for plugin development. Only
in agent-devcontainer, the root `.iwe` is a symbolic link to `assets/.iwe/`.
Therefore, the `.iwe/` of agent-devcontainer and the `.iwe/` of the scaffold
always have the same bytes.

The scaffold structure and the knowledge-base structure of agent-devcontainer
are always the same. The support files under `assets/docs/knowledge/` have the
same bytes as the files that agent-devcontainer uses. A schema change is also a
scaffold change. Adjust the starter documents of the scaffold in the same
commit. If you do not, the next `/agentdev:iwe-bootstrap` installs a workspace
that fails `iwe schema validate`. Every file under `assets/` must be the same
as its `iwe normalize` output.

Through the link, `iwe` writes its runtime files into `assets/.iwe/`. Their
names are in `assets/.iwe/.gitignore`, and `/agentdev:iwe-bootstrap` does not
copy them.

The scaffold graph is not part of a graph that `iwe` reads. No
`.iwe/config.toml` sets `assets/docs/knowledge/` as a workspace.
`iwe normalize`, not Prettier, formats its Markdown.
