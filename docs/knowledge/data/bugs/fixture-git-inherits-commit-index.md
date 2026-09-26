---
type: bug
description: The devcontainer metadata-mask tests run git in a nested fixture repository without clearing GIT_INDEX_FILE, so under `git commit -a` the plan-checkboxes hook fails and can leave a stray index.lock in the outer repository.
generated:
  by: claude-code/opus-5
  at: 2026-09-26T11:20:00Z
sources:
- resource: docs/knowledge/tests/test_devcontainer_metadata_mask.py
- resource: .pre-commit-config.yaml
---

# Fixture git inherits the outer commit's index

## Symptom

`git commit -a` on a change under `docs/knowledge/data/plans/` fails the
`plan-checkboxes` hook: every test in `test_devcontainer_metadata_mask.py`
errors at setup with `git commit -m 'add devcontainer'` returning exit status 1.
The same tests pass under `uv run pytest`, `pre-commit run`, and a plain
`git commit` of staged changes.

## Reproduction

1. Edit any plan under `docs/knowledge/data/plans/`.
2. `git commit -am <message>`.
3. The `plan-checkboxes` hook fails in the fixture's `production_mask_workspace`
   setup.

Running the tests with `GIT_INDEX_FILE` set to an absolute path in the outer
`.git/` reproduces it outside a commit, and writes into that path.

## Root cause

`git commit -a` builds the commit in a temporary index and exports its
**absolute** path as `GIT_INDEX_FILE` to hooks. `_git` in
`docs/knowledge/tests/test_devcontainer_metadata_mask.py:43` runs git in a
nested repository under `.tmp/` with the inherited environment, so the fixture's
`git add` and `git commit` read and write the outer repository's index instead
of their own. A plain `git commit` exports the relative `.git/index`, which
resolves inside the fixture's working directory, so it goes unnoticed.

## Fix

`_git` passes an environment with the `GIT_*` repository variables
(`GIT_INDEX_FILE`, `GIT_DIR`, `GIT_WORK_TREE`) removed, so the fixture
repository is self-contained regardless of the caller.
