# `validate_agent_files` package contributor instructions

These instructions apply to the standalone validator package and its tests.

- Tests for validator library and CLI behavior belong in this package's `tests/` directory.
  Tests for scripts shipped by the `agentdev` plugin belong in the plugin test suite, not
  here.
- **Always run this package's commands with `uv run --isolated`.** From this directory a
  bare `uv run` resolves the project root here and writes a `uv.lock` beside the
  `pyproject.toml` — a pin this released library must not carry, since it resolves against
  its consumer's constraints. `--isolated` also gives the extracted-package shape, which is
  what makes a green run evidence about the published package rather than about this
  checkout.
- This package is released independently, so no package test may reference a path outside
  this package root. Verify that constraint with
  `uv run --isolated --extra dev pytest` from this directory.
- The package owns its `package_tmp_path` scratch fixture and `.gitignore` because root
  ignore rules do not travel with a published package; the `.gitignore` covers `uv.lock`
  for the reason above.
- Keep mock catalog identity in `tests/mock_catalog.py`; import its constants and builders
  instead of repeating fixture identities. Keep that module in `.ruff.toml`'s
  `known-first-party` list.
- Use invented marketplace, plugin, organization, and path values in tests. A published
  identity rename must not require validator test changes.
- Import manifest locations, CLI flags, entry points, and other contract values from the
  code under test rather than restating them as literals.
