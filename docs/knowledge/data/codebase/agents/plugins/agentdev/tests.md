---
type: codebase
description: The pytest suite that pins the exit code and RESULT line of every script the plugin ships, resolved from the plugin root so it runs from a consumer cache.
source: .agents/plugins/agentdev/tests
source_digest: sha256:3825f103a624f210ffc17ed3e05ad57308fa6d0968e377fa7f2b3989cd08c191
verified:
  by: claude-code/opus-5
  at: 2026-09-06T00:00:00Z
stale_after: 2026-12-05
generated:
  by: claude-code/opus-5
  at: 2026-09-06T00:00:00Z
sources:
- id: code
  resource: .agents/plugins/agentdev/tests
---

# Plugin tests

9 test modules plus `conftest.py`, run with
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
  `test_stale_map_docs_masks.py`, `test_template_consume_check_updates.py`,
  `test_update_branch.py`

## How it works

Each module builds a throwaway world — a `git init` repository, stub `gh` or
`git` executables placed first on `PATH` — runs the script with
`subprocess.run`, and asserts on the pair `(returncode, last stdout line)`.
Signal handling is exercised by sending the signal to the running process, for
both result-code libraries: `test_result_codes.py` drives the bash one through a
fixture script and the Python one by generating a `main()` around a body of
source. The two `stale_map_docs` modules also import the script by path so a
fixture computes the expected digest from the same code under test rather than
restating it; the masks module builds `.agent.metadata.json` files and checks
that a masked pin bump stays `FRESH`, that structure around a masked value still
moves the digest, that a rule reaches a subdirectory and a child adds to it, and
that unreadable or uncompilable metadata is `BROKEN_METADATA` confined to its
own subtree. `test_template_consume_check_updates.py` builds the same metadata
file to hold the marker section, and pins `NO_MARKER` for an absent file and for
an absent section, and `INVALID_MARKER` for malformed metadata or a section
missing `consumed_ref` or `tracked_paths`.

## Depends on

`pytest`, `git`, `bash`; nothing from the rest of the repository.

## Invariants & gotchas

- A path that climbs out of the plugin resolves nowhere once installed, so tests
  never use one; `plugin_root / 'skills/<name>/scripts/<script>.sh'` is the only
  way to reach a script.
- Fixtures use invented identities, never this repository's published names.
- Tests for the validator package live with that package, not here.

## Key references

Verified anchor points (line numbers as of 2026-09-06):

- `.agents/plugins/agentdev/tests/conftest.py:22` — `plugin_root`
- `.agents/plugins/agentdev/tests/conftest.py:28` — `plugin_tmp_path`
- `.agents/plugins/agentdev/tests/test_update_branch.py:11` —
  `initialize_repository`, the shared mock-repository builder
- `.agents/plugins/agentdev/tests/test_stale_map_docs.py:18` —
  `_load_script_module`, the by-path import the digest fixtures share
- `.agents/plugins/agentdev/tests/test_result_codes.py:49` — `run_python_helper`
- `.agents/plugins/agentdev/tests/test_stale_map_docs_masks.py:33` —
  `write_metadata`, the masking-rule fixture builder
- `.agents/plugins/agentdev/tests/test_template_consume_check_updates.py:321` —
  an absent marker section is `NO_MARKER`
