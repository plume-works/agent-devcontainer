---
type: codebase
description: The pytest suite that pins the exit code and RESULT line of every script the plugin ships, resolved from the plugin root so it runs from a consumer cache.
source: .agents/plugins/agentdev/tests
source_digest: sha256:1e8a8beb10bf254bc2c0233c4c008475c33cd1be4e0570e74a9b6c6322eee6c9
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
sources:
- id: code
  resource: .agents/plugins/agentdev/tests
---

# Plugin tests

8 test modules plus `conftest.py`, run with
`uv run pytest .agents/plugins/agentdev/tests` and in CI by
`validate-agent-files.yml`.

## Public surface

- `plugin_root` fixture — the plugin directory, from which every script under
  test is resolved
- `plugin_tmp_path` fixture — a scratch directory under the plugin's `.tmp/`,
  removed after each test
- Modules: `test_close_issue.py`, `test_discover_ai_responder.py`,
  `test_fetch_issue.py`, `test_remote_codespace_session.py`,
  `test_result_codes.py`, `test_stale_map_docs.py`,
  `test_template_consume_check_updates.py`, `test_update_branch.py`

## How it works

Each module builds a throwaway world — a `git init` repository, stub `gh` or
`git` executables placed first on `PATH` — runs the script with
`subprocess.run`, and asserts on the pair `(returncode, last stdout line)`.
Signal handling is exercised by sending the signal to the running process.

## Depends on

`pytest`, `git`, `bash`; nothing from the rest of the repository.

## Invariants & gotchas

- A path that climbs out of the plugin resolves nowhere once installed, so tests
  never use one; `plugin_root / 'skills/<name>/scripts/<script>.sh'` is the only
  way to reach a script.
- Fixtures use invented identities, never this repository's published names.
- Tests for the validator package live with that package, not here.

## Key references

Verified anchor points (line numbers as of 2026-09-04):

- `.agents/plugins/agentdev/tests/conftest.py:22` — `plugin_root`
- `.agents/plugins/agentdev/tests/conftest.py:28` — `plugin_tmp_path`
- `.agents/plugins/agentdev/tests/test_update_branch.py:11` —
  `initialize_repository`, the shared mock-repository builder
