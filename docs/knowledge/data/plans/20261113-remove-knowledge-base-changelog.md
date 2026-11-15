---
type: plan
created: 2026-11-13
release: internal
description: This plan removes docs/knowledge/CHANGELOG.md, its iwe-bootstrap copy, and each reference to the file outside the archive.
sources:
- resource: docs/knowledge/CHANGELOG.md
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.py
- resource: .agents/plugins/agentdev/tests/test_iwe_seed.py
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
---

# Remove `CHANGELOG.md` from `docs/knowledge/`

## Context

The user asked to remove `docs/knowledge/CHANGELOG.md`. The `iwe-bootstrap`
skill installs a copy of it,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/CHANGELOG.md`.
The two files are the same.

The `## Changelog` section of `data/product.md` is a different record, and this
plan does not change it.

These files name `CHANGELOG.md` outside `data/archive/`:

- `.agents/plugins/agentdev/tests/test_iwe_seed.py`, in the list of files that
  the scaffold and `docs/knowledge/` share.
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md` and its
  `references/consumption-guide.md`, in the list of paths that the update mode
  compares.
- [Migrate a repository that consumed the earlier IWE
  scaffold](../backlog/migrate-earlier-iwe-scaffold.md), as a source and as one
  place for the migration steps.

## Approach

Delete the two files. Remove `CHANGELOG.md` from the test list, from the two
`template-consume` lists, and from the task
`data/backlog/migrate-earlier-iwe-scaffold.md`.

A change to the bootstrap script is not necessary. The bootstrap script writes a
`CONFLICT` line for a scaffold file that is not in the `docs/knowledge/` tree.
It does not report a file that the scaffold does not contain, such as
`CHANGELOG.md` in a `docs/knowledge/` tree that an earlier scaffold installed.

A consumer keeps its own copy of `CHANGELOG.md`. The consumer can delete it.

## Implementation Steps

### Task 1: Delete `CHANGELOG.md` and its scaffold copy

**Files:** Delete: `docs/knowledge/CHANGELOG.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/CHANGELOG.md`;
Modify: `.agents/plugins/agentdev/tests/test_iwe_seed.py`

- [x] `docs/knowledge/CHANGELOG.md` does not exist.
  - **Evidence:** Deleted with `git rm`; `test ! -e docs/knowledge/CHANGELOG.md`
    passes.
- [x] The scaffold copy of `CHANGELOG.md` does not exist.
  - **Evidence:** Deleted with `git rm`; `test ! -e` on the scaffold path
    passes.
- [x] `SHARED_KNOWLEDGE_FILES` in
  `.agents/plugins/agentdev/tests/test_iwe_seed.py` does not contain
  `'CHANGELOG.md'`.
  - **Evidence:** Removed the entry; `grep CHANGELOG` on the test file finds
    nothing.
- [x] `uv run pytest .agents/plugins/agentdev/tests/test_iwe_seed.py` passes.
  - **Evidence:** Passes, run together with `test_iwe_bootstrap.py`: 35 passed.
- [x] `uv run pytest .agents/plugins/agentdev/tests/test_iwe_bootstrap.py`
  passes.
  - **Evidence:** Passes, run together with `test_iwe_seed.py`: 35 passed.

### Task 2: Remove `CHANGELOG.md` from the `template-consume` lists

**Files:** Modify: `.agents/plugins/agentdev/skills/template-consume/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] The list of `docs/knowledge/` paths in
  `template-consume/SKILL.md#default-template-surface` does not contain
  `docs/knowledge/CHANGELOG.md`.
- [ ] The list in `consumption-guide.md#reusable-scaffold` does not contain
  `docs/knowledge/CHANGELOG.md`.

### Task 3: Remove `CHANGELOG.md` from `migrate-earlier-iwe-scaffold`

**Files:** Modify: `docs/knowledge/data/backlog/migrate-earlier-iwe-scaffold.md`

- [ ] The `sources` of the task do not contain `docs/knowledge/CHANGELOG.md`.

- [ ] The last paragraph of the task contains this text:

  ``` markdown
  Whether this is a script or a `template-consume` update step is for the plan
  to decide.
  ```

## Acceptance

### Scenario: A new scaffold has no `CHANGELOG.md`

- **WHEN** `/agentdev:iwe-bootstrap` installs the scaffold in a repository that
  has no scaffold
- **THEN** the installed `docs/knowledge/` tree does not contain `CHANGELOG.md`
- **Test:**
  `.agents/plugins/agentdev/tests/test_iwe_bootstrap.py::test_fresh_install_creates_the_packaged_scaffold`

The test compares the installed tree with the scaffold. For this reason, the
test shows that the scenario is true only after Task 1 deletes the scaffold
copy.

## Verification

``` bash
test ! -e docs/knowledge/CHANGELOG.md
test ! -e .agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/CHANGELOG.md
! grep -n 'CHANGELOG' .agents/plugins/agentdev/tests/test_iwe_seed.py .agents/plugins/agentdev/skills/template-consume/SKILL.md .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md docs/knowledge/data/backlog/migrate-earlier-iwe-scaffold.md
uv run pytest .agents/plugins/agentdev/tests/test_iwe_seed.py .agents/plugins/agentdev/tests/test_iwe_bootstrap.py
uv run validate_agent_files --recommend . --require-marketplace claude
iwe normalize && iwe schema validate
uv run scripts/check-anchors.py
```

## Out of scope

- The `## Changelog` section of `docs/knowledge/data/product.md` and of its
  scaffold copy.
- The copy of `CHANGELOG.md` in a consumer repository.
- The documents under `docs/knowledge/data/archive/` that name `CHANGELOG.md`.
- A new place for the `### Migration` steps of `CHANGELOG.md`. The [Migrate a
  repository that consumed the earlier IWE
  scaffold](../backlog/migrate-earlier-iwe-scaffold.md) task gives the migration
  steps for a consumer.

## Key references

- `docs/knowledge/CHANGELOG.md` — the file that this plan deletes.
- `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/CHANGELOG.md`
  — the scaffold copy that this plan deletes.
- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.py::Bootstrap.check_existing`
  — writes a `CONFLICT` line for a scaffold file that is not in the tree, and
  does not write one for a file that the scaffold does not contain.
- `.agents/plugins/agentdev/tests/test_iwe_bootstrap.py::test_fresh_install_creates_the_packaged_scaffold`
  — installs the scaffold and compares the installed tree with the scaffold.
- `.agents/plugins/agentdev/tests/test_iwe_seed.py::SHARED_KNOWLEDGE_FILES` —
  the list of shared files.
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md#default-template-surface`
  — the list of `docs/knowledge/` paths that the update mode compares.
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#reusable-scaffold`
  — the same list in the guide.
- `docs/knowledge/data/backlog/migrate-earlier-iwe-scaffold.md` — the task that
  names `CHANGELOG.md`.
