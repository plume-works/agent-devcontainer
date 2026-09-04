---
type: codebase
description: The IWE configuration, frontmatter schemas, operating manual, and checkbox test that make docs/knowledge/data/ a validated OKF bundle; the data itself is the graph, not this doc.
source:
- .iwe
- docs/knowledge/tests
- docs/knowledge/AGENTS.md
- docs/knowledge/SCHEMA.md
- docs/knowledge/STRUCTURE.md
source_digest: sha256:9861aeb6b87ceb9304a3b3d9dd188b3c10d2b57bc7f0bedaf779aad6cf671a6c
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
sources:
- id: code
  resource: .iwe
---

# Knowledge workspace machinery

The scaffolding around the project's memory. `.iwe/config.toml` at the
repository root points the library at `docs/knowledge`, binds a schema to every
`data/` path, and configures normalization; the three Markdown files beside
`data/` explain the manual, the frontmatter shapes, and the design rationale;
one pytest module gates plan checkboxes. This doc deliberately excludes
`docs/knowledge/data/` from its `source`: the map commit would otherwise make
itself stale.

## Public surface

- `.iwe/config.toml` — `[library] path`, `refs_extension = ".md"`,
  `wrap_column = 80`, and the `[schemas.*]` bindings
- `.iwe/schemas/*.yaml` — 15 schemas: `architecture`, `bug`, `codebase`,
  `concept`, `feature`, `hub`, `okf`, `okf-index`, `okf-log`, `plan`, `release`,
  `someday`, `spec`, `task`, `tracker`
- `iwe schema validate`, `iwe normalize` — the commit gate, run by pre-commit
  and by `validate-knowledge-base.yml`
- `docs/knowledge/tests/test_plan_checkboxes.py` — every ticked task in an
  active plan carries an `- **Evidence:**` child; a done plan has no unticked
  task
- `iwec --transport stdio` — the MCP server `.mcp.json` registers

## How it works

Bindings are by key glob, not frontmatter, so a document is validated by where
it lives; hubs and the OKF reserved files have their own schemas, and `okf.yaml`
catches any document under `data/` without a `type`. The IWE skills in the
[catalog](../agents/plugins/agentdev/skills.md) write the data; `iwe normalize`
rewrites links and wrapping after every manual edit.

## Depends on

`iwe` `0.19.0` from [dev_tools](../ansible/roles/dev_tools.md) in the image and
from `cargo install` in CI; `python-frontmatter` and `pytest` for the checkbox
test.

## Invariants & gotchas

- Run `iwe` from the repository root: it does not search upward for `.iwe/` and
  has no root flag. Keys are relative to `docs/knowledge/`.
- The hub set is closed by the `[schemas.hub]` list; adding a hub means adding a
  binding.
- `.iwe/` stays at the root so the IWE VS Code extension finds it when the whole
  repository is the workspace.

## Key references

Verified anchor points (line numbers as of 2026-09-04):

- `.iwe/config.toml:17` — `path = "docs/knowledge"`
- `.iwe/config.toml:63-124` — schema bindings
- `docs/knowledge/tests/test_plan_checkboxes.py:162` — `check_plan`
- `.pre-commit-config.yaml:91-111` — `plan-checkboxes`, `iwe-schema-validate`,
  `iwe-normalize` hooks
- `.github/workflows/validate-knowledge-base.yml:78-89` — the CI checks
