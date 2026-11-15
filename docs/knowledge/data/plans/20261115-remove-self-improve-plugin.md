---
type: plan
created: 2026-11-15
description: Remove the self-improve plugin, its connections, its research, and its glossary terms. Close the graph documents about the plugin, because the project does not use its idea now.
release: internal
sources:
- resource: https://github.com/plume-works/agent-devcontainer/pull/134
  title: Consolidate self-improve and plan resumable Claude reviews
---

# Remove the self-improve plugin

## Context

The backlog task [Remove the self-improve
plugin](../archive/next-release/backlog/revert-self-improve-consolidation.md)
started this work. Pull request #134 put the `self-improve` plugin in this
repository. Its function is to keep a rule from a session in a permanent file.
`AGENTS.md#project-memory` now sends each rule of this type to `AGENTS.md` or to
a document under `docs/knowledge/data/`.

The project does not use the idea of the plugin now. The work deletes the
plugin. The work does not move the plugin to a different repository, and it does
not restore the earlier repository of the plugin.

Because the plan closes no feature and corrects no bug, `release` is `internal`.

## Approach

Delete the plugin, and each file and each line that exists only for the plugin.
The function `py_packages/agentdev_runtime/agentdev_runtime/catalog.py::claude`
and the code in `py_packages/agentdev_runtime/agentdev_runtime/worktree.py` that
installs the per-worktree catalog install each plugin that
`.claude-plugin/marketplace.json` lists. They do not change: with only
`agentdev` in the list, they install only `agentdev`.

All the targets of the root `Makefile` are for the plugin. Nothing outside the
plugin calls `make`. For this reason, the work deletes the `Makefile`. The work
deletes the research that pull request #134 added under `docs/research/`.
`docs/research/vscode-vulnerability/` is not about the plugin and stays.

The three rules that pull request #134 added to `AGENTS.md#project-memory` are
general rules, and they stay.

Each open graph document about the plugin closes:

- The four bugs and the backlog task go to `stage: cancelled` in the archive.
- The four ADRs go to `stage: deprecated` in the archive. No new ADR replaces
  them, because the project does not use the idea now and has no new decision.
- The someday idea has no stage, and the archive has no folder for someday
  ideas. For this reason, `iwe delete` removes it.

The glossary loses the nine entries whose definition is about the plugin. The
words `gate`, `owner`, `proposal`, `reviewer`, and `signal` also occur in other
documents with their normal meaning, which these entries do not define.

## Implementation Steps

### Task 1: Remove the plugin and its marketplace entry

**Files:** Modify: `.agents/plugins/self-improve/`,
`.claude-plugin/marketplace.json`

- [ ] `.agents/plugins/self-improve/` does not exist.
- [ ] `.claude-plugin/marketplace.json#plugins` lists only `agentdev`.
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude`
  exits 0.

### Task 2: Remove the connections to the plugin

**Files:** Modify: `Makefile`, `pyproject.toml`, `.github/workflows/ci.yml`,
`.github/workflows/validate-agent-files.yml`, `.gitignore`,
`.agents/plugins/agentdev/tests/test_macos_bootstrap.py`

- [ ] The root `Makefile` does not exist.
- [ ] `pyproject.toml#tool.pytest.ini_options.testpaths` does not hold
  `.agents/plugins/self-improve/tests`.
- [ ] `pyproject.toml#tool.pytest.ini_options.markers` does not hold the markers
  `smoke`, `interactive`, `pty`, `harness`, and `auto_memory`.
- [ ] The pytest command in `.github/workflows/ci.yml` does not name
  `.agents/plugins/self-improve/tests`.
- [ ] `.github/workflows/validate-agent-files.yml` does not have the step
  `Test self-improve plugin` and its comment.
- [ ] `.gitignore` does not have the block that starts with
  `# self-improve runtime state`, and does not have the `/test-runs/` entry and
  its comment.
- [ ] `.agents/plugins/agentdev/tests/test_macos_bootstrap.py::test_plugin_step_installs_only_agentdev`
  does not have the assertion that names `self-improve`.
- [ ] `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py::test_plugin_step_installs_only_agentdev`
  passes.

### Task 3: Remove the research of the plugin

**Files:** Modify: `docs/research/case-study/`,
`docs/research/hypothetical-extensions/`, `.ruff.toml`

- [ ] `docs/research/case-study/` does not exist.
- [ ] `docs/research/hypothetical-extensions/` does not exist.
- [ ] `.ruff.toml` does not have the `extend-exclude` entry, the `force-exclude`
  entry, and the comment above them.

### Task 4: Remove the plugin from the README

**Files:** Modify: `README.md`

- [ ] The feature list at the start of `README.md` does not have the item about
  the `self-improve` plugin.
- [ ] `README.md#the-plugin-catalog` says that Claude Code sees one plugin,
  `agentdev`.
- [ ] `README.md` does not have the `### self-improve` section.
- [ ] The paragraph about the plugin sources in `README.md` names only
  `.agents/plugins/agentdev/`.

### Task 5: Remove the glossary terms of the plugin

**Files:** Modify: `docs/knowledge/data/glossary.md`

- [ ] `docs/knowledge/data/glossary.md` does not have the entries `fingerprint`,
  `preimage`, and `umbrella`.
- [ ] `docs/knowledge/data/glossary.md` does not have the entries of
  `candidate`, `gate`, `owner`, `reviewer`, and `signal` that start with "In
  self-improve". The other entry for `candidate` stays.
- [ ] `docs/knowledge/data/glossary.md` does not have the entry `proposal`.

### Task 6: Close the graph documents about the plugin

**Files:** Modify: `docs/knowledge/data/bugs/`,
`docs/knowledge/data/backlog/self-improve-execution-tracing.md`,
`docs/knowledge/data/someday/self-improve-hermes-prompt-stack.md`,
`docs/knowledge/data/adr/`, `docs/knowledge/data/bugs.md`,
`docs/knowledge/data/backlog.md`, `docs/knowledge/data/someday.md`,
`docs/knowledge/data/adr.md`, `docs/knowledge/data/archive/next-release/`

- [ ] `bugs/readme-says-self-improve-not-enabled` is at `stage: cancelled` in
  `data/archive/next-release/bugs/`.
- [ ] `bugs/self-improve-allowlist-accepts-nested-rules` is at
  `stage: cancelled` in `data/archive/next-release/bugs/`.
- [ ] `bugs/self-improve-reviewer-decline-asymmetry` is at `stage: cancelled` in
  `data/archive/next-release/bugs/`.
- [ ] `bugs/self-improve-unstageable-routing-option` is at `stage: cancelled` in
  `data/archive/next-release/bugs/`.
- [ ] `backlog/self-improve-execution-tracing` is at `stage: cancelled` in
  `data/archive/next-release/backlog/`.
- [ ] `iwe delete` removed `someday/self-improve-hermes-prompt-stack`.
- [ ] `adr/0087-self-improve-authorization-from-typed-commands` is at
  `stage: deprecated` in `data/archive/next-release/adr/`.
- [ ] `adr/0088-self-improve-lives-in-this-repository` is at `stage: deprecated`
  in `data/archive/next-release/adr/`.
- [ ] `adr/0089-self-improve-reviewer-holds-no-tools` is at `stage: deprecated`
  in `data/archive/next-release/adr/`.
- [ ] `adr/0090-self-improve-runtime-uses-only-the-standard-library` is at
  `stage: deprecated` in `data/archive/next-release/adr/`.
- [ ] `iwe schema validate` exits 0.

### Task 7: Remove the plugin path from the open bugs

**Files:** Modify:
`docs/knowledge/data/bugs/consumption-guide-keeps-publisher-source-references.md`,
`docs/knowledge/data/bugs/custom-image-bundle-misses-runtime-inputs.md`

- [ ] The `## Reproduction` of
  `bugs/consumption-guide-keeps-publisher-source-references` does not name
  `.agents/plugins/self-improve/tests` or a `self-improve` step.
- [ ] The `## Root cause` of `bugs/custom-image-bundle-misses-runtime-inputs`
  does not name `.agents/plugins/self-improve/tests`.

## Acceptance

### Scenario: The marketplace does not list the plugin

- **WHEN** Claude Code installs the plugins that
  `.claude-plugin/marketplace.json` lists
- **THEN** it installs only `agentdev`, and no `/self-improve:` skill is
  available
- **Checked at ship:** `.claude-plugin/marketplace.json#plugins`

### Scenario: The repository has no make targets

- **WHEN** a user runs `make` at the repository root
- **THEN** `make` finds no makefile
- **Checked at ship:** the repository root has no `Makefile`

### Scenario: The test suite does not collect plugin tests

- **WHEN** `uv run pytest` runs with the test paths in `pyproject.toml`
- **THEN** it collects no test under `.agents/plugins/self-improve/`
- **Checked at ship:** `pyproject.toml#tool.pytest.ini_options.testpaths`

## Verification

1. `test ! -e .agents/plugins/self-improve && test ! -e Makefile && test ! -e docs/research/case-study && test ! -e docs/research/hypothetical-extensions`
   exits 0.
2. `uv run validate_agent_files --recommend . --require-marketplace claude`
   exits 0.
3. `uv run pytest --collect-only -q` exits 0.
4. `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py py_packages/agentdev_runtime/tests/test_catalog_claude_register.py`
   passes.
5. `uv run ruff check .` exits 0.
6. `grep -n -i -e self-improve -e SELF_IMPROVE -e test-runs -e hypothetical-extensions -e case-study README.md .claude-plugin/marketplace.json pyproject.toml .github/workflows/ci.yml .github/workflows/validate-agent-files.yml .gitignore .ruff.toml .agents/plugins/agentdev/tests/test_macos_bootstrap.py docs/knowledge/data/glossary.md docs/knowledge/data/bugs.md docs/knowledge/data/backlog.md docs/knowledge/data/someday.md docs/knowledge/data/adr.md docs/knowledge/data/bugs/consumption-guide-keeps-publisher-source-references.md docs/knowledge/data/bugs/custom-image-bundle-misses-runtime-inputs.md`
   prints nothing.
7. Run `iwe normalize`. Then `iwe schema validate` exits 0.

## Out of scope

- The changes of pull request #134 to the review responder and the plan for
  resumed reviews.
- The documents in `docs/knowledge/data/archive/`. They record completed work
  and do not change.
- `docs/research/vscode-vulnerability/`.
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py::claude` and
  `py_packages/agentdev_runtime/agentdev_runtime/worktree.py`.

## Key references

- `.claude-plugin/marketplace.json#plugins` — the list of plugins that Claude
  Code installs from this repository.
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py::claude` — installs
  each plugin in the list, and it does not change.
- `pyproject.toml#tool.pytest.ini_options` — the test paths and the markers.
- `.github/workflows/ci.yml › "uv run pytest -n 8 py_packages"` — the pytest
  command that names the plugin tests.
- `.github/workflows/validate-agent-files.yml › "Test self-improve plugin"` —
  the step that tests the plugin.
- `.agents/plugins/agentdev/tests/test_macos_bootstrap.py::test_plugin_step_installs_only_agentdev`
  — the assertion that names `self-improve`.
- `.ruff.toml#extend-exclude` — the exclusion for the research prompts.
- `README.md#the-plugin-catalog` — the catalog section that names the plugin.
- `docs/knowledge/data/glossary.md` — the terms of the plugin.
