---
type: codebase
description: The IWE configuration, frontmatter schemas, operating manual, and repository tests that make docs/knowledge/data/ a validated OKF bundle; the data itself is the graph, not this doc.
source:
- .iwe
- docs/knowledge/tests
- docs/knowledge/AGENTS.md
- docs/knowledge/SCHEMA.md
- docs/knowledge/STRUCTURE.md
source_digest: sha256:2d8300a1c71b47d460cb21b73d682d28522d338c9f04c30113f029b7013f6479
verified:
  by: claude-code/opus-5.5
  at: 2026-10-28T10:30:00Z
stale_after: 2027-01-26
generated:
  by: claude-code/opus-5.5
  at: 2026-10-28T10:30:00Z
sources:
- id: code
  resource: .iwe
---

# Knowledge workspace machinery

The scaffolding around the project's memory. `.iwe/config.toml` at the
repository root points the library at `docs/knowledge`, binds a schema to every
`data/` path, and configures normalization; the three Markdown files beside
`data/` explain the manual, the frontmatter shapes, and the design rationale;
seven pytest modules gate plan checkboxes, the plan `release` declaration, the
bug and feature body shape, the packaged IWE scaffold, and the production digest
masks for Dev Container feature pins and their lock, role pins, workflow image
digests, and hook revisions. This doc deliberately excludes
`docs/knowledge/data/` from its `source`: the map commit would otherwise make
itself stale.

## Public surface

- `.iwe/config.toml` — `[workspace] path`, `refs_extension = ".md"`,
  `wrap_column = 80`, and the `[schemas.*]` bindings; `[schemas.tracker]` also
  binds `data/template-adoption`, a document only a consumer workspace holds
- `.iwe/schemas/*.yaml` — 15 schemas: `architecture`, `bug`, `codebase`,
  `concept`, `feature`, `hub`, `okf`, `okf-index`, `okf-log`, `plan`, `release`,
  `someday`, `spec`, `task`, `tracker`; `bug` and `feature` also fix the body
  shape, requiring their sections in order under one H1 (`bug` also requires a
  `Bug: ` title prefix) while allowing extra sections
- `iwe schema validate`, `iwe normalize` — the commit gate, run by pre-commit
  and by `validate-knowledge-base.yml`
- `docs/knowledge/tests/test_plan_checkboxes.py` — every ticked task in an
  active plan carries an `- **Evidence:**` child; a done plan has no unticked
  task
- `docs/knowledge/tests/test_plan_release_schema.py` — rewrites one plan's
  `release` in a copy of the graph and checks that `iwe schema validate`
  requires `internal` or `features/` and `bugs/` keys on an active plan and
  accepts a done plan without one
- `docs/knowledge/tests/test_body_shape_schemas.py` — breaks one bug and one
  feature document in a copy of the graph by dropping, reordering, or misnaming
  a required section, and checks that `iwe schema validate` rejects each
- `docs/knowledge/tests/test_iwe_seed.py` — copies [the iwe-bootstrap
  scaffold](../agents/plugins/agentdev/skills/iwe-bootstrap.md) alone into a
  standalone workspace and checks its schema, normalization, completeness,
  onboarding tasks, links, license, and boundaries; also requires its `.iwe/`
  files and knowledge instructions to equal this repository's and every asset to
  be tracked
- `docs/knowledge/tests/test_devcontainer_metadata_mask.py` — exercises the
  checked-in Dev Container feature-pin and lock masks against the full
  production configuration, keeping a version bump and its regenerated lock
  fresh while feature identity or the locked registry changes remain stale
- `docs/knowledge/tests/test_pin_metadata_masks.py` — runs `stale-map-docs.py`
  over a copy of the production role and workflow masks: Renovate pin, checksum,
  and `agent-desktop` digest bumps keep a map doc fresh, while `zizmor`'s
  version, a download URL, a `# renovate:` comment, a 64-hex value outside a
  checksum field, or a different image still make it stale
- `docs/knowledge/tests/test_pre_commit_rev_mask.py` — runs `stale-map-docs.py`
  over the production root mask and hook config: hook `rev` and local hooks'
  `bunx` version bumps keep a map doc fresh, while a changed hook id,
  repository, or `bunx` package still makes it stale

## How it works

Bindings are by key glob, not frontmatter, so a document is validated by where
it lives; hubs and the OKF reserved files have their own schemas, and `okf.yaml`
catches any document under `data/` without a `type`. The IWE skills in the
[catalog](../agents/plugins/agentdev/skills.md) write the data; `iwe normalize`
rewrites links and wrapping after every manual edit. The scaffold test copies
the skill's `assets/` tree as a whole workspace because the scaffold is not a
member of this repository's graph.

## Depends on

The pinned `iwe` from [dev_tools](../ansible/roles/dev_tools.md), installed in
the image and fetched by `scripts/fetch-pinned-tool.py` in CI;
`python-frontmatter` and `pytest` for the repository-level tests.

## Invariants & gotchas

- Run `iwe` from the repository root: it does not search upward for `.iwe/` and
  has no root flag. Keys are relative to `docs/knowledge/`.
- The hub set is closed by the `[schemas.hub]` list; adding a hub means adding a
  binding.
- `.iwe/` stays at the root so the IWE VS Code extension finds it when the whole
  repository is the workspace.
- `.iwe/`, `AGENTS.md`, `SCHEMA.md`, `STRUCTURE.md`, and the other support files
  beside `data/` are duplicated byte for byte in the iwe-bootstrap scaffold; a
  change here is a change there.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.iwe/config.toml:17` — `path = "docs/knowledge"`
- `.iwe/config.toml:63-124` — schema bindings
- `.iwe/config.toml:111` — the tracker binding, including the consumer-only
  `data/template-adoption`
- `.iwe/schemas/bug.yaml:6`, `.iwe/schemas/feature.yaml:6` — the required body
  sections
- `docs/knowledge/tests/test_plan_checkboxes.py:162` — `check_plan`
- `docs/knowledge/tests/test_body_shape_schemas.py:124` —
  `test_malformed_body_is_rejected`
- `docs/knowledge/tests/test_iwe_seed.py:73` — standalone consumer-workspace
  fixture
- `docs/knowledge/tests/test_iwe_seed.py:110` —
  `test_scaffold_support_files_match_the_publisher_workspace`
- `docs/knowledge/tests/test_devcontainer_metadata_mask.py:72,210` — production
  mask workspace fixture and the feature-bump-with-lock test
- `docs/knowledge/tests/test_pin_metadata_masks.py:87,133,158,168` — mask
  workspace fixture, role-pin, non-checksum-hex, and container-digest tests
- `docs/knowledge/tests/test_pre_commit_rev_mask.py:60` — hook-config mask
  workspace fixture; all three mask fixtures run with the caller's `GIT_*`
  variables removed
- `.pre-commit-config.yaml:107-127` — `plan-checkboxes`, `iwe-schema-validate`,
  `iwe-normalize` hooks
- `.github/workflows/validate-knowledge-base.yml:86-107` — pinned iwe, graph and
  scaffold checks
