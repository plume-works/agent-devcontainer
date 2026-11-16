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

Pull request #134 added three rules to `AGENTS.md#project-memory`. The work
deletes the rule about instrumentation. The two rules about the documents in
`data/findings/` are general rules, and they stay.

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

### Task 1: Remove the plugin and its entry in `.claude-plugin/marketplace.json`

**Files:** Modify: `.agents/plugins/self-improve/`,
`.claude-plugin/marketplace.json`

- [x] `.agents/plugins/self-improve/` does not exist.
  `test ! -e .agents/plugins/self-improve` succeeds.
  - **Evidence:** `git rm -r .agents/plugins/self-improve`;
    `test ! -e .agents/plugins/self-improve` succeeds.
- [x] `.claude-plugin/marketplace.json#plugins` lists only `agentdev`.
  `agentdev`.
  - **Evidence:** Removed the `self-improve` element; `plugins` now holds only
    `agentdev`.
- [x] `uv run validate_agent_files --recommend . --require-marketplace claude`
  exits 0.
  `uv run validate_agent_files --recommend . --require-marketplace claude` exits
  0: "Errors: 0, Warnings: 0".
  - **Evidence:**
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    exits 0: "Errors: 0, Warnings: 0".

### Task 2: Remove the connections to the plugin

**Files:** Modify: `Makefile`, `pyproject.toml`, `.github/workflows/ci.yml`,
`.github/workflows/validate-agent-files.yml`, `.gitignore`,
`.agents/plugins/agentdev/tests/test_macos_bootstrap.py`

- [x] The root `Makefile` does not exist.
  - **Evidence:** `git rm Makefile`; `test ! -e Makefile` succeeds.
- [x] `pyproject.toml#tool.pytest.ini_options.testpaths` does not hold
  `.agents/plugins/self-improve/tests`.
  - **Evidence:** Removed the entry; `testpaths` holds the agentdev tests,
    `docs/knowledge/tests`, `py_packages`, and `scripts/tests`.
- [x] `pyproject.toml#tool.pytest.ini_options.markers` does not hold the pytest
  markers `smoke`, `interactive`, `pty`, `harness`, and `auto_memory`.
  - **Evidence:** Removed the five entries; `markers` holds `stress` and
    `requires_root`. `uv run pytest --collect-only -q` collects 1551 tests.
- [x] The pytest command in `.github/workflows/ci.yml` does not name
  `.agents/plugins/self-improve/tests`.
  - **Evidence:** The command is
    `uv run pytest -n 8 py_packages .agents/plugins/agentdev/tests scripts/tests`.
- [x] `.github/workflows/validate-agent-files.yml` does not have the step
  `Test self-improve plugin` and its comment.
  - **Evidence:** Removed the step and its two comment lines.
- [x] `.gitignore` does not have the block that starts with
  `# self-improve runtime state`, and does not have the `/test-runs/` entry and
  its comment.
  - **Evidence:** Removed the block and the `/test-runs/` entry with its
    comment.
- [x] `.agents/plugins/agentdev/tests/test_macos_bootstrap.py::test_plugin_step_installs_only_agentdev`
  does not have the assertion that names `self-improve`.
  - **Evidence:** Removed the line
    `assert not any('self-improve' in call for call in claude)`.
- [x] `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py::test_plugin_step_installs_only_agentdev`
  passes.
  - **Evidence:** The test skips without `zsh` here; in a
    `ghcr.io/astral-sh/uv:python3.12-bookworm` container with `zsh` it reports
    "1 passed".

### Task 3: Remove the research of the plugin

**Files:** Modify: `docs/research/case-study/`,
`docs/research/hypothetical-extensions/`, `.ruff.toml`

- [x] `docs/research/case-study/` does not exist.
  - **Evidence:** `git rm -r docs/research/case-study`; `docs/research/` holds
    only `vscode-vulnerability`.
- [x] `docs/research/hypothetical-extensions/` does not exist.
  - **Evidence:** `git rm -r docs/research/hypothetical-extensions`.
- [x] `.ruff.toml` does not have the `extend-exclude` entry, the `force-exclude`
  entry, and the comment above them.
  - **Evidence:** Removed the three lines and the comment; `uv run ruff check .`
    passes.

### Task 4: Remove the plugin from the README

**Files:** Modify: `README.md`

- [x] The feature list at the start of `README.md` does not have the item about
  the `self-improve` plugin.
  - **Evidence:** Removed the item; the list goes from the catalog line to the
    Xpra desktop line.
- [x] `README.md#the-plugin-catalog` says that Claude Code installs one plugin,
  `agentdev`.
  - **Evidence:** The section says "Claude Code installs one plugin,
    `agentdev`".
- [x] `README.md` does not have the `### self-improve` section.
  - **Evidence:** Removed the section; `grep -n -i self-improve README.md`
    prints nothing.
- [x] The paragraph about the plugin sources in `README.md` names only
  `.agents/plugins/agentdev/`.
  - **Evidence:** The paragraph says "The canonical plugin source is
    `.agents/plugins/agentdev/`".

### Task 5: Remove the glossary terms of the plugin

**Files:** Modify: `docs/knowledge/data/glossary.md`

- [x] `docs/knowledge/data/glossary.md` does not have the entries `fingerprint`,
  `preimage`, and `umbrella`.
  - **Evidence:** Removed the three entries (19 lines removed for the whole
    task).
- [x] `docs/knowledge/data/glossary.md` does not have the entries of
  `candidate`, `gate`, `owner`, `reviewer`, and `signal` that start with "In
  self-improve". The other entry for `candidate` stays.
  - **Evidence:** Removed the five "In self-improve" entries; `candidate` keeps
    its image-publishing entry.
- [x] `docs/knowledge/data/glossary.md` does not have the entry `proposal`.
  - **Evidence:** Removed the entry;
    `grep -n -i self-improve docs/knowledge/data/glossary.md` prints nothing.

### Task 6: Close the graph documents about the plugin

**Files:** Modify: `docs/knowledge/data/bugs/`,
`docs/knowledge/data/backlog/self-improve-execution-tracing.md`,
`docs/knowledge/data/someday/self-improve-hermes-prompt-stack.md`,
`docs/knowledge/data/adr/`, `docs/knowledge/data/bugs.md`,
`docs/knowledge/data/backlog.md`, `docs/knowledge/data/someday.md`,
`docs/knowledge/data/adr.md`, `docs/knowledge/data/archive/next-release/`

- [x] `bugs/readme-says-self-improve-not-enabled` is at `stage: cancelled` in
  `data/archive/next-release/bugs/`.
  - **Evidence:** `iwe update --set stage=cancelled`, then `iwe rename` to
    `data/archive/next-release/bugs/readme-says-self-improve-not-enabled`; hub
    link removed from `data/bugs.md`.
- [x] `bugs/self-improve-allowlist-accepts-nested-rules` is at
  `stage: cancelled` in `data/archive/next-release/bugs/`.
  - **Evidence:** `iwe update --set stage=cancelled`, then `iwe rename` to
    `data/archive/next-release/bugs/self-improve-allowlist-accepts-nested-rules`;
    hub link removed from `data/bugs.md`.
- [x] `bugs/self-improve-reviewer-decline-asymmetry` is at `stage: cancelled` in
  `data/archive/next-release/bugs/`.
  - **Evidence:** `iwe update --set stage=cancelled`, then `iwe rename` to
    `data/archive/next-release/bugs/self-improve-reviewer-decline-asymmetry`;
    hub link removed from `data/bugs.md`.
- [x] `bugs/self-improve-unstageable-routing-option` is at `stage: cancelled` in
  `data/archive/next-release/bugs/`.
  - **Evidence:** `iwe update --set stage=cancelled`, then `iwe rename` to
    `data/archive/next-release/bugs/self-improve-unstageable-routing-option`;
    hub link removed from `data/bugs.md`.
- [x] `backlog/self-improve-execution-tracing` is at `stage: cancelled` in
  `data/archive/next-release/backlog/`.
  - **Evidence:** `iwe update --set stage=cancelled`, then `iwe rename` to
    `data/archive/next-release/backlog/`; hub link removed from
    `data/backlog.md`.
- [x] `iwe delete` removed `someday/self-improve-hermes-prompt-stack`.
  - **Evidence:** `iwe delete data/someday/self-improve-hermes-prompt-stack`
    removed the file and its link in `data/someday.md`.
- [x] `adr/0087-self-improve-authorization-from-typed-commands` is at
  `stage: deprecated` in `data/archive/next-release/adr/`.
  - **Evidence:** `iwe update --set stage=deprecated`, then `iwe rename` to
    `data/archive/next-release/adr/0087-self-improve-authorization-from-typed-commands`;
    hub link removed from `data/adr.md`.
- [x] `adr/0088-self-improve-lives-in-this-repository` is at `stage: deprecated`
  in `data/archive/next-release/adr/`.
  - **Evidence:** `iwe update --set stage=deprecated`, then `iwe rename` to
    `data/archive/next-release/adr/0088-self-improve-lives-in-this-repository`;
    hub link removed from `data/adr.md`.
- [x] `adr/0089-self-improve-reviewer-holds-no-tools` is at `stage: deprecated`
  in `data/archive/next-release/adr/`.
  - **Evidence:** `iwe update --set stage=deprecated`, then `iwe rename` to
    `data/archive/next-release/adr/0089-self-improve-reviewer-holds-no-tools`;
    hub link removed from `data/adr.md`.
- [x] `adr/0090-self-improve-runtime-uses-only-the-standard-library` is at
  `stage: deprecated` in `data/archive/next-release/adr/`.
  - **Evidence:** `iwe update --set stage=deprecated`, then `iwe rename` to
    `data/archive/next-release/adr/0090-self-improve-runtime-uses-only-the-standard-library`;
    hub link removed from `data/adr.md`.
- [x] `iwe schema validate` exits 0.
  - **Evidence:** `iwe normalize`, then `iwe schema validate` exits 0;
    `uv run scripts/check-anchors.py` exits 0.

### Task 7: Remove the plugin path from the open bugs

**Files:** Modify:
`docs/knowledge/data/bugs/consumption-guide-keeps-publisher-source-references.md`,
`docs/knowledge/data/bugs/custom-image-bundle-misses-runtime-inputs.md`

- [x] The `## Reproduction` of
  `bugs/consumption-guide-keeps-publisher-source-references` does not name
  `.agents/plugins/self-improve/tests` or a `self-improve` step.
  - **Evidence:** Steps 3 and 4 now name only `scripts/tests` and the `bun`
    steps; the `description` no longer names the self-improve tests.
- [x] The `## Root cause` of `bugs/custom-image-bundle-misses-runtime-inputs`
  does not name `.agents/plugins/self-improve/tests`.
  - **Evidence:** The `ci.yml` sentence names `py_packages`,
    `.agents/plugins/agentdev/tests`, and `scripts/tests`.

### Task 8: Remove the instrumentation rule from `AGENTS.md`

**Files:** Modify: `AGENTS.md`

- [x] `AGENTS.md#project-memory` does not have this paragraph:

  - **Evidence:** Removed the paragraph and its blank line;
    `grep -n -F 'Do not build instrumentation' AGENTS.md` prints nothing.

  ```
  **Do not build instrumentation for a question nobody has framed.** Work proposed
  to answer an open finding stays behind a named hypothesis its output could
  confirm or kill. A facility built because its design is finished, rather than
  because a question needs it, becomes a second product.
  ```

## Acceptance

### Scenario: `.claude-plugin/marketplace.json` does not list the plugin

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
7. `grep -n -F 'Do not build instrumentation' AGENTS.md` prints nothing.
8. Run `iwe normalize`. Then `iwe schema validate` exits 0.

## Out of scope

- The changes of pull request #134 to the review responder and the plan for
  reviews that continue after a stop.
- The documents in `docs/knowledge/data/archive/`. They record completed work
  and do not change.
- `docs/research/vscode-vulnerability/`.
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py::claude` and
  `py_packages/agentdev_runtime/agentdev_runtime/worktree.py`.

## Key references

- `AGENTS.md#project-memory` — the section that has the instrumentation rule.
- `.claude-plugin/marketplace.json#plugins` — the list of plugins that Claude
  Code installs from this repository.
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py::claude` — installs
  each plugin in the list, and it does not change.
- `pyproject.toml#tool.pytest.ini_options` — the test paths and the markers.
- `.github/workflows/ci.yml › "uv run pytest -n 8 py_packages"` — the pytest
  command that names the plugin tests.
- `.agents/plugins/agentdev/tests/test_macos_bootstrap.py::test_plugin_step_installs_only_agentdev`
  — the test of the plugin step of the macOS bootstrap.
- `README.md#the-plugin-catalog` — the catalog section that names the plugin.
- `docs/knowledge/data/glossary.md` — the terms of the plugin.
