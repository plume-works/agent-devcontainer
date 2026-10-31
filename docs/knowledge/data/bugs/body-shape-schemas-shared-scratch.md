---
type: bug
description: The body-shape schema tests build their scratch graph at a fixed /tmp path, so two runs at once — from different worktrees or sessions — rewrite each other's documents and fail with "section 'Root cause' not found".
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T06:00:00Z
sources:
- resource: docs/knowledge/tests/test_body_shape_schemas.py
- resource: docs/knowledge/tests/test_plan_release_schema.py
- resource: docs/knowledge/tests/test_iwe_seed.py
- resource: .pre-commit-config.yaml
---

# Bug: body-shape schema tests share one scratch graph across concurrent runs

## Symptom

`uv run pytest docs/knowledge/tests` — the `plan-checkboxes` hook — fails
intermittently while another run of the same suite is in progress:

``` text
E       AssertionError: section 'Root cause' not found
docs/knowledge/tests/test_body_shape_schemas.py:48: AssertionError
FAILED docs/knowledge/tests/test_body_shape_schemas.py::test_malformed_body_is_rejected[bug-missing-section]
```

Run alone, the same test passes.

## Reproduction

1. Start `uv run pytest docs/knowledge/tests/test_body_shape_schemas.py` in two
   checkouts (or two shells) at the same time.
2. Either run can fail: one deletes and recopies the workspace, or mutates the
   first bug document, while the other is reading or restoring it.

## Root cause

The `workspace` fixture builds its graph copy at
`/tmp/agentdev-tests/body-shape-schemas`, a path that does not depend on the
run, and removes any existing copy first. `/tmp` is shared by every worktree and
session in the container, so concurrent runs share one copy. Each
`test_malformed_body_is_rejected` case rewrites the lane's first document and
restores it afterwards; a second run that reads the document between those two
writes sees another case's mutation — here `## Root cause` already dropped — or
a tree the other run's fixture just deleted.

`test_plan_release_schema.py` (`plan-release-schema`) and `test_iwe_seed.py`
(`iwe-seed-consumer`) use the same fixed-path pattern and are exposed the same
way.

## Fix

Unfixed. Give each run its own scratch root, as the mask tests already do with
`TMP_ROOT / f'<name>-{uuid4().hex}'`, and remove it when the fixture finishes.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `docs/knowledge/tests/test_body_shape_schemas.py:22` — `TMP_ROOT`
- `docs/knowledge/tests/test_body_shape_schemas.py:82` — `workspace`, the fixed
  `body-shape-schemas` root and its `rmtree`
- `docs/knowledge/tests/test_body_shape_schemas.py:92` — `document`, which
  mutates and restores the lane's first document in place
- `docs/knowledge/tests/test_plan_release_schema.py:57` — fixed
  `plan-release-schema` root
- `docs/knowledge/tests/test_iwe_seed.py:76` — fixed `iwe-seed-consumer` root
- `docs/knowledge/tests/test_pin_metadata_masks.py:94` — the per-run `uuid4`
  root to follow
- `.pre-commit-config.yaml:106` — `plan-checkboxes`, which runs the suite
