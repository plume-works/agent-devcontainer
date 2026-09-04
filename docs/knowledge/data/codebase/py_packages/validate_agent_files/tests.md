---
type: codebase
description: The self-contained pytest suite for the validator package, built on an invented mock catalog so it passes from an extracted package.
source: py_packages/validate_agent_files/tests
source_digest: sha256:a85bc865846cdfa35a75bdd5b2fe660b73f01772f974fddc136b8ffc849735bc
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
sources:
- id: code
  resource: py_packages/validate_agent_files/tests
---

# Validator package tests

15 modules plus `conftest.py` and `mock_catalog.py`; run from the package
directory with `pytest`, or in isolation with
`uv run --isolated --extra dev pytest`.

## Public surface

- `mock_catalog.py` — the one place fixture identities (marketplace, plugin,
  organization, paths) are defined
- `package_tmp_path` fixture — scratch inside the package
- Modules: `test_agent_validation.py`, `test_bundled_markdown_containment.py`,
  `test_cli.py`, `test_download_claude_responder_runs.py`,
  `test_entrypoints.py`, `test_formatters.py`, `test_gitignore_discovery.py`,
  `test_loaders.py`, `test_path_resolution.py`, `test_plugin_layout.py`,
  `test_plugin_link_containment.py`, `test_plugin_mode.py`,
  `test_prompt_validation.py`, `test_require_marketplace.py`,
  `test_skill_validation.py`

## How it works

Each module builds a fictional catalog on disk from `mock_catalog` builders and
drives either the engine directly or the CLI entry point, asserting on issues
and exit codes. Contract values — manifest locations, flags, entry points — are
imported from the code under test rather than restated.

## Depends on

`pytest`, `git` for the ignore-aware discovery tests.

## Invariants & gotchas

- No test may reference a path outside the package root, and none may encode
  this repository's published identity.
- Tests for plugin-shipped scripts belong to the
  [plugin suite](../../agents/plugins/agentdev/tests.md), never here.

## Key references

Verified anchor points (line numbers as of 2026-09-04):

- `py_packages/validate_agent_files/tests/mock_catalog.py:1` — fixture identity
- `py_packages/validate_agent_files/AGENTS.md:1` — the package's own contributor
  rules
