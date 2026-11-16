---
type: plan
created: 2026-11-16
release: internal
description: Make each support file in docs/knowledge/ a symbolic link to its scaffold copy. Add a pre-commit hook that makes and checks the links.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md
---

# Link the support files of the knowledge base to the scaffold

## Context

The support files of the knowledge base are in two locations: `docs/knowledge/`
and the scaffold at
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/`.
`scaffold.md#maintenance` gives the rule that the two copies have the same
bytes. No hook or test makes sure of this. Each plan that changes a support file
edits the two copies and compares them with `diff` or `cmp` by hand. Thus, a
change to one copy can go into `main` without the change to the other copy.

The root `.iwe` is already a symbolic link to the `.iwe/` of the scaffold. This
plan does the same for the support files in `docs/knowledge/`.

## Approach

The scaffold keeps the only copy of each support file. In `docs/knowledge/`,
each support file becomes a relative symbolic link to its scaffold copy. The
plugin thus keeps all its files, and each checkout of agent-devcontainer reads
the scaffold copy through the link.

These files become links: `AGENTS.md`, `CLAUDE.md`, `SCHEMA.md`, `README.md`,
`.markdownlint.yml`, and each document in `schema/`. These files stay real
files:

- `LICENSE.md`, because the consumer owns it after `/agentdev:iwe-bootstrap`
  installs it.
- `.gitignore`, because git does not read a `.gitignore` that is a symbolic
  link.
- All files in `data/` and `tests/`.

`schema/` stays a real directory with one link for each document in it. `iwe`
does not follow a symbolic link to a directory. Thus, if `schema/` is a link,
the `schema/*` documents are not in the graph, and `iwe normalize` does not
format them. `iwe` follows a symbolic link to a file. `iwe normalize` writes
through the link and keeps it.

A new script, `scripts/link-knowledge-support.py`, makes and checks the links. A
new pre-commit hook runs it. The script reads each file in the scaffold
`docs/knowledge/`, but not the files in `data/`, `LICENSE.md`, or `.gitignore`.
Each of these scaffold copies is `F`. `L` is the same path under
`docs/knowledge/`. The script does the action that the table gives:

| State of `L`                                 | Action of the script                      | Exit |
| -------------------------------------------- | ----------------------------------------- | ---- |
| A link that resolves to `F`                  | none                                      | 0    |
| Missing                                      | make the link                             | 1    |
| A real file with the same bytes as `F`       | replace the file with the link            | 1    |
| A real file with bytes that are not the same | no change; report "different: `L` vs `F`" | 1    |
| A link to a different target                 | no change; report the link                | 1    |

For a file in `docs/knowledge/` that has no scaffold copy:

| State                                                        | Action of the script                        | Exit |
| ------------------------------------------------------------ | ------------------------------------------- | ---- |
| A link that does not resolve                                 | no change; report the link                  | 1    |
| A real file in `docs/knowledge/schema/`                      | no change; report "belongs in the scaffold" | 1    |
| A file in `data/` or `tests/`, `LICENSE.md`, or `.gitignore` | ignore it                                   | 0    |

The script never deletes a file. It changes a file only when it cannot remove
content: the file is not there, or the file has the same bytes as its scaffold
copy. The script exits 1 when it changes or reports a file, so the commit stops
and the author stages the change. One run of the script also changes the copies
to links the first time.

The `iwe-schema-validate` and `iwe-normalize` hooks also start on a change under
the scaffold `docs/knowledge/`. Git records an edit through a link at the path
of the scaffold copy, so without this change these hooks do not start.

Prettier does not format these files. `.prettierignore` already has
`docs/knowledge/**` and the scaffold `assets/**`, and pre-commit does not give a
symbolic link to a hook. `iwe normalize` formats them.

No change is necessary in `/agentdev:iwe-bootstrap`: it copies from the real
files of the scaffold. No change is necessary in `/agentdev:template-consume`
update mode: `check-updates.py::upstream_link_target` already compares the
target of a tracked path that is a link. A consumer that copies the full
repository (Workflow A) has links that do not resolve after it deletes
`.agents/`. The consumption guide gives this information for `.iwe`. It must
also give this information for these links.

Assumption: the hook entry runs the script alone. It does not use
`git diff --exit-code` as `iwe-normalize` does, because `git diff` does not show
a new link that git does not track yet. The script exit code stops the commit
instead.

## Implementation Steps

### Task 1: Add the link script and its tests

**Files:** Create: `scripts/link-knowledge-support.py`,
`scripts/tests/test_link_knowledge_support.py`

- [x] `scripts/link-knowledge-support.py` exists, runs from the repository root,
  and does the actions of the two tables in `## Approach`.
  - **Evidence:** Script added. A dry run on a scratch copy of HEAD made 22
    links; a second run exited 0 with no output. It also reports a support file
    reached through a linked directory instead of writing a link over the
    scaffold copy, which keeps "never deletes a file" true.
- [x] `uv run pytest scripts/tests/test_link_knowledge_support.py` passes, with
  one test for each scenario in `## Acceptance`.
  - **Evidence:** 11 passed: the 8 scenario tests (the missing-link test runs
    for a top-level and a `schema/` file), plus a missing `schema/` directory
    and a support file under a linked directory.

### Task 2: Run the script from pre-commit

**Files:** Modify: `.pre-commit-config.yaml`

- [x] A local hook `link-knowledge-support` runs
  `uv run scripts/link-knowledge-support.py` with `pass_filenames: false`, on a
  change under `docs/knowledge/` or under the scaffold `docs/knowledge/`.
  - **Evidence:** Hook added with `types: []` and `types_or: [file, symlink]`,
    because the default `types: [file]` skips a link. In a scratch git copy,
    `pre-commit run link-knowledge-support --files <path>` ran for a link in
    `docs/knowledge/`, a link in `schema/`, and a scaffold file, and skipped
    `README.md` at the root.
- [x] The `files:` patterns of the `iwe-schema-validate` and `iwe-normalize`
  hooks also match each Markdown file under the scaffold `docs/knowledge/`.
  - **Evidence:** Both patterns are now
    `^(<scaffold assets>/)?(docs/knowledge/.*\.md|\.iwe/.*)$`. In the scratch
    copy, `pre-commit run iwe-normalize --files` on the scaffold
    `schema/adrs.md` ran and passed.

### Task 3: Replace the copies with links

**Files:** Modify: `docs/knowledge/AGENTS.md`, `docs/knowledge/CLAUDE.md`,
`docs/knowledge/SCHEMA.md`, `docs/knowledge/README.md`,
`docs/knowledge/.markdownlint.yml`, each file in `docs/knowledge/schema/`

- [x] `uv run scripts/link-knowledge-support.py` replaces the 22 copies with
  links and reports no file that is different from its scaffold copy.
  - **Evidence:** The run printed 22 "replaced the copy with a link" lines and
    no "different:" line; `find docs/knowledge -maxdepth 2 -type l` lists 22.
- [x] A second run of `uv run scripts/link-knowledge-support.py` exits 0 and
  writes no output.
  - **Evidence:** Second run: exit 0, no output.
- [x] `iwe find -f keys | grep -vc '^data/'` gives 22, the same number as before
  the change.
  - **Evidence:** 22 before the run and 22 after it; `iwe normalize` changed no
    file and `iwe schema validate` passed.

### Task 4: Record the link rule in the scaffold reference

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md`

- [ ] `scaffold.md#maintenance` gives the rule that each support file in
  `docs/knowledge/` of agent-devcontainer, except `LICENSE.md` and `.gitignore`,
  is a link to its scaffold copy. It names `scripts/link-knowledge-support.py`
  as the script that makes and checks the links. It says that `schema/` is a
  real directory with one link for each document, because `iwe` does not follow
  a link to a directory. It replaces the sentence that gives the rule that the
  support files have the same bytes.

### Task 5: Tell consumers about the links

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] In `consumption-guide.md#initialize-the-consumers-knowledge`, the Workflow
  A text about the `.iwe` link also names the support-file links in
  `docs/knowledge/`. These links do not resolve after the consumer deletes
  `.agents/`.
- [ ] In `consumption-guide.md#5-adapt-pre-commit-and-lint-configuration`, the
  list tells the consumer to remove the `link-knowledge-support` hook, because
  the consumer has no scaffold.

## Acceptance

### Scenario: The script makes a missing link

- **WHEN** a scaffold support file has no file at its path under
  `docs/knowledge/`, at the top level or in `schema/`
- **THEN** the script makes a relative link to the scaffold copy, `schema/`
  stays a real directory, and the script exits 1
- **Test:**
  `scripts/tests/test_link_knowledge_support.py::test_missing_link_is_made`

### Scenario: The script replaces a copy with the same bytes

- **WHEN** a support file under `docs/knowledge/` is a real file with the same
  bytes as its scaffold copy
- **THEN** the script replaces the file with a link to the scaffold copy and
  exits 1
- **Test:**
  `scripts/tests/test_link_knowledge_support.py::test_same_copy_becomes_a_link`

### Scenario: The script reports a copy that is different from its scaffold copy

- **WHEN** a support file under `docs/knowledge/` is a real file with bytes that
  are not the same as its scaffold copy
- **THEN** the script names the two paths as different, does not change the
  file, and exits 1
- **Test:**
  `scripts/tests/test_link_knowledge_support.py::test_different_copy_is_reported`

### Scenario: The script reports a link to a different target

- **WHEN** a support file under `docs/knowledge/` is a link that does not
  resolve to its scaffold copy
- **THEN** the script names the link, does not change it, and exits 1
- **Test:**
  `scripts/tests/test_link_knowledge_support.py::test_link_to_other_target_is_reported`

### Scenario: The script reports a link that does not resolve

- **WHEN** a link under `docs/knowledge/` has no scaffold copy, for example
  after a change renames a scaffold file
- **THEN** the script names the link, does not delete it, and exits 1
- **Test:**
  `scripts/tests/test_link_knowledge_support.py::test_dangling_link_is_reported`

### Scenario: The script reports a schema document that only the repository has

- **WHEN** `docs/knowledge/schema/` has a real file that the scaffold does not
  have
- **THEN** the script names the file as one that belongs in the scaffold, does
  not change it, and exits 1
- **Test:**
  `scripts/tests/test_link_knowledge_support.py::test_repository_only_schema_file_is_reported`

### Scenario: The script ignores the files that the repository owns

- **WHEN** `docs/knowledge/` has `LICENSE.md`, `.gitignore`, and files in
  `data/` and `tests/` that are real files
- **THEN** the script does not change or report them
- **Test:**
  `scripts/tests/test_link_knowledge_support.py::test_owned_files_are_ignored`

### Scenario: A correct tree passes

- **WHEN** each support file under `docs/knowledge/` is a link to its scaffold
  copy
- **THEN** the script writes no output and exits 0
- **Test:**
  `scripts/tests/test_link_knowledge_support.py::test_linked_tree_passes`

## Verification

- `uv run pytest scripts/tests/test_link_knowledge_support.py`
- `uv run scripts/link-knowledge-support.py` exits 0 and writes no output.
- `find docs/knowledge -maxdepth 2 -type l | wc -l` gives 22.
- `test -f docs/knowledge/LICENSE.md && test ! -L docs/knowledge/LICENSE.md`
- `test -f docs/knowledge/.gitignore && test ! -L docs/knowledge/.gitignore`
- `test -d docs/knowledge/schema && test ! -L docs/knowledge/schema`
- `iwe find -f keys | grep -vc '^data/'` gives 22.
- `iwe normalize && git diff --exit-code` exits 0.
- `iwe schema validate` exits 0.
- `uv run pre-commit run link-knowledge-support --all-files` passes.

## Out of scope

- A check that `SCHEMA.md` has a Markdown link to each document in `schema/`.
  `SCHEMA.md` names the documents in code formatting, and `iwe schema validate`
  does not check Markdown links.
- A check that fails on a Markdown link in the graph that has no target
  (`iwe stats`).
- A change to `/agentdev:iwe-bootstrap` or to `check-updates.py`.
- The `.iwe/` link, which is already a link.

## Key references

- `.agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md#maintenance`
  — the rule that this plan changes from "same bytes" to "link".
- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.py` —
  copies the real scaffold files with `symlinks=True`; no change.
- `.agents/plugins/agentdev/skills/template-consume/agent-code/check-updates.py::upstream_link_target`
  — compares the target of a tracked path that is a link; no change.
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#initialize-the-consumers-knowledge`
  — the Workflow A text about the `.iwe` link.
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#5-adapt-pre-commit-and-lint-configuration`
  — the list of hooks that a consumer keeps or removes.
- `.pre-commit-config.yaml#repos` › `id: iwe-normalize` — the `files:` pattern
  that Task 2 changes; `id: iwe-schema-validate` has the same pattern.
- `scripts/check-ship-records.py` and `scripts/tests/test_check_ship_records.py`
  — the model for a repository script that a hook runs, and for its tests in a
  temporary directory under `/tmp`.
- `scripts/tests/scratch.py` — `TMP_ROOT`, the root directory under `/tmp` for
  test files.
- `.prettierignore` › `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/**`
  — Prettier does not format the scaffold.
