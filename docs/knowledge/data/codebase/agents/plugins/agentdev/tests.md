---
type: codebase
description: The pytest suite that pins the exit code and RESULT line of every script the plugin ships, resolved from the plugin root so it runs from a consumer cache.
source: .agents/plugins/agentdev/tests
source_digest: sha256:32e14aa6d53f9b20e645506ea823e1c465b30e2d9e960e591a9be7a182199293
verified:
  by: claude-code/opus-5.5
  at: 2026-10-04T12:00:00Z
stale_after: 2027-01-02
generated:
  by: claude-code/opus-5.5
  at: 2026-10-04T12:00:00Z
sources:
- id: code
  resource: .agents/plugins/agentdev/tests
---

# Plugin tests

13 test modules plus `conftest.py` and the `git_fixtures.py` helper module, run
with `uv run pytest .agents/plugins/agentdev/tests` and in CI by
`validate-agent-files.yml`. `opencode/bridge.test.ts` is a separate `bun test`
suite for the [OpenCode bridge](opencode-plugin.md), run with
`bun test ./.agents/plugins/agentdev/tests/opencode` in the same job.

## Public surface

- `plugin_root` fixture — the plugin directory, from which every script under
  test is resolved
- `plugin_tmp_path` fixture — a scratch directory under the plugin's `.tmp/`,
  removed after each test
- `git_fixtures.py` — `FIXTURE_ENV`, `git()`, `outcome()`, and `stub_gh()`,
  shared by the git-skill modules and the push-branch module
- Modules: `test_capture_close_issue.py`, `test_close_issue.py`,
  `test_discover_ai_responder.py`, `test_fetch_issue.py`, `test_git_commit.py`,
  `test_git_new_branch.py`, `test_push_branch_map_check.py`,
  `test_remote_codespace_session.py`, `test_result_codes.py`,
  `test_stale_map_docs.py`, `test_stale_map_docs_masks.py`,
  `test_template_consume_check_updates.py`, `test_update_branch.py`

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
moves the digest, that a rule reaches a subdirectory and a child adds to it,
that a metadata file is not itself tracked content, and that unreadable,
uncompilable, or inapplicable metadata is `BROKEN_METADATA` confined to its own
subtree, including invalid replacements and masked binary files.
`test_capture_close_issue.py` reuses `initialize_repository` from
`test_update_branch.py` and a stub `gh` that logs closes, and pins each
`close-issue.sh` result, including an already-closed issue left alone.
`test_template_consume_check_updates.py` builds the same metadata file to hold
the marker section, and pins `NO_MARKER` for an absent file and for an absent
section, and `INVALID_MARKER` for malformed metadata or a section missing
`consumed_ref` or `tracked_paths`.

`test_git_new_branch.py` builds a bare remote, a working clone, and a publisher
clone that advances the remote behind the working clone's back; the
`gh`-fallback cases set `remote.origin.followRemoteHEAD=never` so a fetch does
not recreate `origin/HEAD`. `test_git_commit.py` commits in a throwaway
repository with and without a configured remote. `test_push_branch_map_check.py`
pushes to a bare remote from a repository that carries an IWE config and one map
doc, computes that doc's digest through the by-path import of
`stale-map-docs.py`, and pins `pr-open`'s `push-branch.sh` map gate: `MAP_STALE`
leaves the remote ref untouched on both push paths, `--skip-map-check` pushes
anyway, a repository without an IWE config is not gated, an up-to-date head is
still checked and a stale one pushed outside the helper stops at `MAP_STALE`, an
uncommitted edit does not change the verdict, and the temporary check worktree
is removed.

## Depends on

`pytest`, `git`, `bash`, and `bun` for the OpenCode suite; nothing from the rest
of the repository.

## Invariants & gotchas

- A path that climbs out of the plugin resolves nowhere once installed, so tests
  never use one; `plugin_root / 'skills/<name>/agent-code/<script>.sh'` is the
  only way to reach a script.
- Fixtures use invented identities, never this repository's published names.
- Tests for the validator package live with that package, not here.

## Key references

Verified anchor points (line numbers as of 2026-10-04):

- `.agents/plugins/agentdev/tests/conftest.py:22` — `plugin_root`
- `.agents/plugins/agentdev/tests/conftest.py:28` — `plugin_tmp_path`
- `.agents/plugins/agentdev/tests/test_update_branch.py:11` —
  `initialize_repository`, the shared mock-repository builder
- `.agents/plugins/agentdev/tests/git_fixtures.py:37` — `stub_gh`
- `.agents/plugins/agentdev/tests/test_git_new_branch.py:24` — `Fixture`, the
  remote/work/publisher triple
- `.agents/plugins/agentdev/tests/test_stale_map_docs.py:18` —
  `_load_script_module`, the by-path import the digest fixtures share
- `.agents/plugins/agentdev/tests/test_capture_close_issue.py:19` —
  `install_gh_stub`
- `.agents/plugins/agentdev/tests/test_result_codes.py:50` — `run_python_helper`
- `.agents/plugins/agentdev/tests/test_stale_map_docs_masks.py:33` —
  `write_metadata`, the masking-rule fixture builder
- `.agents/plugins/agentdev/tests/test_stale_map_docs_masks.py:286` — invalid
  replacement and masked binary regressions
- `.agents/plugins/agentdev/tests/test_push_branch_map_check.py:54` —
  `build_repository`, the remote-plus-map fixture
- `.agents/plugins/agentdev/tests/test_template_consume_check_updates.py:321` —
  an absent marker section is `NO_MARKER`
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts:38` — `configured`,
  the hook driver every config case shares
