---
type: codebase
description: Plugin script contract tests under pytest and catalog/workspace bridge tests under Bun.
source: .agents/plugins/agentdev/tests
source_digest: sha256:d40f8ff025e7c6adcb6c0e2e895d589abea0e3a1296ece323ffd77a77d1ad1db
verified:
  by: claude-code/opus-5
  at: 2026-10-25T16:37:10Z
stale_after: 2027-01-23
generated:
  by: claude-code/opus-5
  at: 2026-10-25T16:37:10Z
sources:
- id: code
  resource: .agents/plugins/agentdev/tests
---

# Plugin tests

18 test modules plus `conftest.py` and the `git_fixtures.py` helper module, run
with `uv run pytest .agents/plugins/agentdev/tests` and in CI by
`validate-agent-files.yml`. `opencode/bridge.test.ts` and
`opencode/workspace-index.test.ts` are separate Bun suites for the [OpenCode
bridge](opencode-plugin.md), run with
`bun test ./.agents/plugins/agentdev/tests/opencode` in the same job; the bridge
suite drives the v1 hooks directly and the v2 setup against a fake plugin ctx.
Two host checks are not Bun test files and stay out of CI; each runs directly
with `bun` against an OpenCode v2 executable (`OPENCODE_BIN`, else `opencode`):
`opencode/verify-workspace-host.ts` checks workspace registration with the
installed CBM, isolated in a private mount namespace under `.tmp/`, and
`opencode/verify-agent-limits-host.ts` drives a local mock model to check
catalog agent tool limits under full access, user replacement of agents,
commands, and skills, and the bridge's CBM warning in `opencode.log`.

## Public surface

- `plugin_root` fixture — the plugin directory, from which every script under
  test is resolved
- `plugin_tmp_path` fixture — a scratch directory under the plugin's `.tmp/`,
  removed after each test
- `installed_iwe_bootstrap` and `unrelated_repository` fixtures — a copy of only
  `bin/` and `skills/iwe-bootstrap/` in a scratch plugin layout, and a fresh git
  repository for it to initialize
- `git_fixtures.py` — `FIXTURE_ENV`, `git()`, `outcome()`, and `stub_gh()`,
  shared by the git-skill modules and the push-branch module
- Modules: `test_capture_close_issue.py`, `test_close_issue.py`,
  `test_discover_ai_responder.py`, `test_explicit_only_parity.py`,
  `test_fetch_issue.py`, `test_gh_stack_guard.py`, `test_git_commit.py`,
  `test_install_codex_agents.py`, `test_iwe_bootstrap.py`,
  `test_git_new_branch.py`, `test_push_branch_map_check.py`,
  `test_remote_codespace_session.py`, `test_result_codes.py`,
  `test_stale_map_docs.py`, `test_stale_map_docs_masks.py`,
  `test_stale_map_docs_replay.py`, `test_template_consume_check_updates.py`,
  `test_update_branch.py`

## How it works

Each module builds a throwaway world — a `git init` repository, stub `gh` or
`git` executables placed first on `PATH` — runs the script with
`subprocess.run`, and asserts on the pair `(returncode, last stdout line)`.
Signal handling is exercised by sending the signal to the running process, for
both result-code libraries: `test_result_codes.py` drives the bash one through a
fixture script and the Python one by generating a `main()` around a body of
source. The `stale_map_docs` and masks modules also import the script by path so
a fixture computes the expected digest from the same code under test rather than
restating it; the masks module builds `.agent.metadata.json` files and checks
that a masked pin bump stays `FRESH`, that structure around a masked value still
moves the digest, that a rule reaches a subdirectory and a child adds to it,
that a metadata file is not itself tracked content, and that unreadable,
uncompilable, or inapplicable metadata is `BROKEN_METADATA` confined to its own
subtree, including invalid replacements and masked binary files. The replay
module reuses both modules' helpers, commits fixtures at fixed future dates so
`--since` and `verified.at` cut history predictably, and pins `--replay`: a pin
bump a new uncommitted rule covers is `ABSORBED` and its doc `RESTAMP` with the
digest a plain run then records, working-tree absorption emits `WORKTREE` and
`HIDDEN` evidence, and verdict ancestry cannot be narrowed by commit dates or
`--since`. It also covers stale starting digests, current hidden values in
unchanged files, non-ASCII and quoted filenames, historical masked-text decode
failures, and a CRLF masked file whose starting digest still validates. A change
outside the rule or an uncommitted unmasked edit is `REFRESH`; malformed
metadata is `BROKEN_METADATA` even on an early refresh path.
`test_gh_stack_guard.py` builds a two-layer stack on a bare remote with a peer
clone that pushes behind the working clone's back, a stub `git` with
after-ls-remote and before-push hooks, and a stub `gh` that models `stack view`,
`api` for the stack number, `stack link` (a non-force atomic push of the named
branches, in create or add mode), and `stack checkout`; it pins each
`stack-guard.sh` result, including a squash-merged lower layer that GitHub-style
rebasing leaves `SUCCESS`, a peer merge of trunk, a whitespace-only remote
rewrite, a push leased on the checked tip, queued layers, link create and add
modes, and a `publish` rerun after a failed link. `test_capture_close_issue.py`
reuses `initialize_repository` from `test_update_branch.py` and a stub `gh` that
logs closes, and pins each `close-issue.sh` result, including an already-closed
issue left alone. `test_template_consume_check_updates.py` builds the same
metadata file to hold the marker section, and pins `NO_MARKER` for an absent
file and for an absent section, and `INVALID_MARKER` for malformed metadata or a
section missing `consumed_ref` or `tracked_paths`.

`test_update_branch.py` builds a bare remote, a working clone on a pushed
feature branch, and a publisher clone, and pins `update-branch.sh`'s upstream
sync: fast-forward and merge before the base, `ALREADY_UP_TO_DATE` after a
fast-forward onto an upstream holding the base, a conflicted upstream merge
followed by a rerun, a conflicted base merge, a gone upstream, an upstream that
is the base ref, and an upstream on a second remote, reachable or not.

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

`test_iwe_bootstrap.py` runs `bootstrap-iwe.sh` only from the
`installed_iwe_bootstrap` copy and compares full path, byte, and mtime snapshots
of the target: a fresh install equals `assets/` and validates and normalizes
cleanly, a repeat and an onboarded workspace are `ALREADY_INITIALIZED` with no
change, and partial, incompatible, colliding, symlinked, and foreign-transaction
states are `RECONCILIATION_REQUIRED` with nothing written. A restricted `PATH`
of symlinked tools plus stub `iwe` or `mv` scripts covers a missing `iwe`, a
failing validation, and `SIGTERM` during staging or commit, each followed by a
recovering run; a transaction left empty or holding only its first `OWNER.next`
write is discarded on the next run. Tests that need the real `iwe` skip without
it.

`test_explicit_only_parity.py` requires every skill that sets
`disable-model-invocation: true` to carry an `agents/openai.yaml` with
`allow_implicit_invocation: false`, and the reverse, and pins the mismatch check
on fake skills in each direction.

The workspace suite creates Git repositories, symlinks, and linked worktrees
under `.tmp/` and injects command/logging adapters. It covers registration
gates, canonical exact-root matching, pagination, concurrency, retry after
failure, MCP envelopes, and real subprocess timeout/output bounds. Bridge tests
assert catalog availability while registration remains pending, client
diagnostics, full v2 command text for bare and argument-bearing invocations, and
rebased attachment mention spans without input mutation.

## Depends on

`pytest`, `git`, `bash`, PyYAML, `bun` for the OpenCode suite, and `iwe` for the
bootstrap tests.

## Invariants & gotchas

- A path that climbs out of the plugin resolves nowhere once installed, so a
  script is reached only as
  `plugin_root / 'skills/<name>/agent-code/<script>.sh'`.
- Fixtures use invented identities, never this repository's published names.
- Tests for the validator package live with that package, not here.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.agents/plugins/agentdev/tests/conftest.py:23` — `plugin_root`
- `.agents/plugins/agentdev/tests/conftest.py:29` — `plugin_tmp_path`
- `.agents/plugins/agentdev/tests/conftest.py:40` — `installed_iwe_bootstrap`
- `.agents/plugins/agentdev/tests/test_iwe_bootstrap.py:92` — `snapshot`, the
  path, byte, and mtime record every refusal is compared against
- `.agents/plugins/agentdev/tests/test_iwe_bootstrap.py:127` —
  `restricted_path`, the tool-only `PATH` with stub scripts
- `.agents/plugins/agentdev/tests/test_iwe_bootstrap.py:422` — interrupted
  commit and its completing rerun
- `.agents/plugins/agentdev/tests/test_update_branch.py:112` —
  `UpstreamFixture`, the remote/work/publisher triple for upstream sync
- `.agents/plugins/agentdev/tests/test_update_branch.py:14` —
  `initialize_repository`, the shared mock-repository builder
- `.agents/plugins/agentdev/tests/git_fixtures.py:37` — `stub_gh`
- `.agents/plugins/agentdev/tests/test_gh_stack_guard.py:116` — `Stack`, the
  two-layer stack fixture with a peer clone and a gh-stack-like stub `gh`
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
- `.agents/plugins/agentdev/tests/test_stale_map_docs_replay.py:37` —
  `commit_dated`, the fixed-date commit helper
- `.agents/plugins/agentdev/tests/test_stale_map_docs_replay.py:67` —
  `bumped_workspace`, a mapped pin and its bump
- `.agents/plugins/agentdev/tests/test_stale_map_docs_replay.py:151` —
  working-tree evidence regression
- `.agents/plugins/agentdev/tests/test_stale_map_docs_replay.py:254` —
  digest-commit ancestry regression
- `.agents/plugins/agentdev/tests/test_push_branch_map_check.py:54` —
  `build_repository`, the remote-plus-map fixture
- `.agents/plugins/agentdev/tests/test_template_consume_check_updates.py:321` —
  an absent marker section is `NO_MARKER`
- `.agents/plugins/agentdev/tests/test_explicit_only_parity.py:33` —
  `parity_mismatches`
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts:42` — `configured`,
  the v1 hook driver every config case shares
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts:200` — `fakeV2`, the
  recording v2 plugin ctx
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts:277` — full v2
  invocation payload and attachment-span regression
- `.agents/plugins/agentdev/tests/opencode/workspace-index.test.ts:38` — command
  and logging harness
