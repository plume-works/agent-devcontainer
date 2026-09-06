# IWE seed

The starting `docs/knowledge/data/` tree a consuming repository receives when it
adopts this template with the knowledge-base bundle. `data/` here is the seed;
`LICENSE.md` is the MIT notice it carries into every consumer.

## Ownership

This seed is maintained in this repository, against the schemas in `.iwe/` and
the `agentdev` IWE workflow skills. Its content was imported once from
[plume-works/iwe-dev-workspace](https://github.com/plume-works/iwe-dev-workspace)
at commit `249943bcc30ac1016469d5ee89a16ce454cc882f`, under that project's MIT
license. Nothing here tracks that repository: changes to the schemas or the
onboarding skills are applied here directly, and the seed is never fetched from
elsewhere at adoption time.

## What it contains

- **Hubs and trackers** — one per document type, each carrying the conventions
  its documents follow.
- **`data/product.md`** — the foundation document, left as ✏️ placeholder blocks
  for `/agentdev:iwe-setup` to fill.
- **Onboarding tasks** under `data/backlog/` — `fill-product-doc` and
  `capture-current-architecture` are the two `/agentdev:iwe-setup` closes.
- **`*.example.md` documents** — fictional documents about a fictional product,
  showing the shape of each type. `/agentdev:iwe-setup` deletes them once real
  documents exist.

## Boundaries

The seed is not part of this repository's own IWE graph: `.iwe/config.toml`
points its library at `docs/knowledge`, so nothing under `templates/` is a graph
member, and `iwe` commands run at the repository root never read or rewrite it.
`docs/knowledge/tests/test_iwe_seed.py` validates it by assembling a throwaway
consumer workspace instead.

Seed Markdown is excluded from Prettier — `iwe normalize` owns its formatting,
and the two disagree.
