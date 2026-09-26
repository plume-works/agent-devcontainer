---
type: codebase
description: The IWE configuration, frontmatter schemas, operating manual, and repository tests that make docs/knowledge/data/ a validated OKF bundle; the data itself is the graph, not this doc.
source:
- .iwe
- docs/knowledge/tests
- docs/knowledge/AGENTS.md
- docs/knowledge/SCHEMA.md
- docs/knowledge/STRUCTURE.md
source_digest: sha256:842b7ac1ced4f5683194e21e25b719721c0e8273abfde51144c3a2a274bd668c
verified:
  by: claude-code/opus-5.5
  at: 2026-09-26T00:00:00Z
stale_after: 2026-12-25
generated:
  by: claude-code/opus-5.5
  at: 2026-09-26T00:00:00Z
sources:
- id: code
  resource: .iwe
---

# Knowledge workspace machinery

The scaffolding around the project's memory. `.iwe/config.toml` at the
repository root points the library at `docs/knowledge`, binds a schema to every
`data/` path, and configures normalization; the three Markdown files beside
`data/` explain the manual, the frontmatter shapes, and the design rationale;
four pytest modules gate plan checkboxes, the consumer seed, and the production
digest masks for Dev Container feature pins, role pins, and workflow image
digests. This doc deliberately excludes `docs/knowledge/data/` from its
`source`: the map commit would otherwise make itself stale.

## Public surface

- `.iwe/config.toml` — `[library] path`, `refs_extension = ".md"`,
  `wrap_column = 80`, and the `[schemas.*]` bindings; `[schemas.tracker]` also
  binds `data/template-adoption`, a document only a consumer workspace holds
- `.iwe/schemas/*.yaml` — 15 schemas: `architecture`, `bug`, `codebase`,
  `concept`, `feature`, `hub`, `okf`, `okf-index`, `okf-log`, `plan`, `release`,
  `someday`, `spec`, `task`, `tracker`
- `iwe schema validate`, `iwe normalize` — the commit gate, run by pre-commit
  and by `validate-knowledge-base.yml`
- `docs/knowledge/tests/test_plan_checkboxes.py` — every ticked task in an
  active plan carries an `- **Evidence:**` child; a done plan has no unticked
  task
- `docs/knowledge/tests/test_iwe_seed.py` — assembles
  [the consumer seed](../templates/iwe.md) as a standalone workspace and checks
  its schema, normalization, onboarding tasks, links, license, and boundaries
- `docs/knowledge/tests/test_devcontainer_metadata_mask.py` — exercises the
  checked-in Dev Container feature-pin mask against the full production
  configuration, keeping version-only changes fresh while feature identity
  changes remain stale
- `docs/knowledge/tests/test_pin_metadata_masks.py` — runs `stale-map-docs.py`
  over a copy of the production role and workflow masks: Renovate pin, checksum,
  and `agent-desktop` digest bumps keep a map doc fresh, while `zizmor`'s
  version, a download URL, a `# renovate:` comment, or a different image still
  make it stale
- `iwec --transport stdio` — the MCP server `.mcp.json` registers

## How it works

Bindings are by key glob, not frontmatter, so a document is validated by where
it lives; hubs and the OKF reserved files have their own schemas, and `okf.yaml`
catches any document under `data/` without a `type`. The IWE skills in the
[catalog](../agents/plugins/agentdev/skills.md) write the data; `iwe normalize`
rewrites links and wrapping after every manual edit. The seed test mounts the
root schemas over a copied `templates/iwe/data/` tree because the seed is not a
member of this repository's graph.

## Depends on

`iwe` `0.19.0` from [dev_tools](../ansible/roles/dev_tools.md) in the image and
from `cargo install` in CI; `python-frontmatter` and `pytest` for the
repository-level tests.

## Invariants & gotchas

- Run `iwe` from the repository root: it does not search upward for `.iwe/` and
  has no root flag. Keys are relative to `docs/knowledge/`.
- The hub set is closed by the `[schemas.hub]` list; adding a hub means adding a
  binding.
- `.iwe/` stays at the root so the IWE VS Code extension finds it when the whole
  repository is the workspace.

## Key references

Verified anchor points (line numbers as of 2026-09-26):

- `.iwe/config.toml:17` — `path = "docs/knowledge"`
- `.iwe/config.toml:63-124` — schema bindings
- `.iwe/config.toml:111` — the tracker binding, including the consumer-only
  `data/template-adoption`
- `docs/knowledge/tests/test_plan_checkboxes.py:162` — `check_plan`
- `docs/knowledge/tests/test_iwe_seed.py:57` — standalone consumer-workspace
  fixture
- `docs/knowledge/tests/test_devcontainer_metadata_mask.py:67` — production mask
  workspace fixture
- `docs/knowledge/tests/test_pin_metadata_masks.py:73,123,148` — mask workspace
  fixture, role-pin and container-digest freshness tests
- `.pre-commit-config.yaml:102-122` — `plan-checkboxes`, `iwe-schema-validate`,
  `iwe-normalize` hooks
- `.github/workflows/validate-knowledge-base.yml:91-109` — graph and seed checks
