---
type: bug
description: Three knowledge-base test fixtures build their workspace at a fixed path under /tmp/agentdev-tests and delete it on entry, so two concurrent test runs destroy each other's workspace and fail intermittently.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T03:30:00Z
sources:
- resource: docs/knowledge/tests/test_body_shape_schemas.py
- resource: docs/knowledge/tests/test_plan_release_schema.py
- resource: docs/knowledge/tests/test_iwe_seed.py
---

# Bug: knowledge-base tests share a fixed scratch directory across concurrent runs

## Symptom

`test_body_shape_schemas.py` fails intermittently when another run of the
knowledge-base suite is in progress, for example the `plan-checkboxes`
pre-commit hook in one worktree while a sibling worktree runs the same hook. The
failures vary between runs: `test_unmodified_graph_validates` reports
`.iwe/schemas/feature.yaml not found`, and `test_malformed_body_is_rejected`
cases fail or error in the `document` fixture. Each test passes when run alone.

## Reproduction

Run the suite twice at once from the repository root:

``` bash
uv run pytest docs/knowledge/tests & uv run pytest docs/knowledge/tests; wait
```

Both runs collected the same tests; one ended `6 failed, 52 passed` and the
other `52 passed, 6 errors`, all in `test_body_shape_schemas.py`. The failure
reproduced in two rounds out of two.

## Root cause

The module-scoped `workspace` fixture in `test_body_shape_schemas.py` builds its
graph copy at the fixed path `/tmp/agentdev-tests/body-shape-schemas` and
deletes that directory first if it exists. A second run starting while the first
is mid-module deletes and re-creates the directory the first run is validating
and mutating, so the first run sees a missing schema or a missing document. The
fixture also never removes its directory, so a stale copy is always left for the
next run to delete.

`test_plan_release_schema.py` (`plan-release-schema`) and `test_iwe_seed.py`
(`iwe-seed-consumer`) use the same fixed-path, delete-on-entry fixture and race
the same way. The other fixtures under `docs/knowledge/tests/` already create a
`uuid4`-suffixed directory per run and remove it on teardown.

## Fix

Not fixed yet.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `docs/knowledge/tests/test_body_shape_schemas.py:79` — `workspace` fixture
  deleting the fixed `body-shape-schemas` directory
- `docs/knowledge/tests/test_plan_release_schema.py:54` — `workspace` fixture
  deleting the fixed `plan-release-schema` directory
- `docs/knowledge/tests/test_iwe_seed.py:73` — `consumer_workspace` fixture
  deleting the fixed `iwe-seed-consumer` directory
- `docs/knowledge/tests/test_pin_metadata_masks.py:94` — the per-run `uuid4`
  directory the other fixtures use
