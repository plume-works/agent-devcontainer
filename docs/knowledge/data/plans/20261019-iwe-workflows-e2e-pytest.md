---
type: plan
created: 2026-10-19
release: internal
description: Port the agent-owned Ship/Implement e2e suite from bash to a pytest suite at scripts/e2e/iwe-workflows/, with one clone and, on OpenCode, one isolated server per test, gated by E2E_RUN_LIVE, OpenCode first and then Claude Code and Codex.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T00:00:00Z
sources:
- resource: scripts/e2e/20261007-agent-owned-ship-implement/run.sh
- resource: .agents/plugins/self-improve/tests/conftest.py
- resource: .agents/plugins/agentdev/tests/opencode/verify-workspace-host.ts
- resource: .devcontainer/scripts/opencode-web-start.sh
stage: done
completed: 2026-10-20
---

# Port the IWE workflow e2e suite to pytest

## Context

[Port the agent-owned Ship/Implement e2e suite to
pytest](../backlog/port-agent-owned-e2e-to-pytest.md) owns the requirements: one
clone per test, one OpenCode server per test driven over HTTP, one pytest test
per scenario and harness, parallel under pytest-xdist with a worker cap,
OpenCode first, and no check weaker than in the bash suite.

The bash suite was introduced by
[20261007-agent-owned-ship-implement](20261007-agent-owned-ship-implement.md);
the suite moves to `scripts/e2e/iwe-workflows/`, named for the workflows it
exercises; the old plan keeps its references to the old path.

[Ship a standalone OpenCode
container](20261017-standalone-opencode-container.md) moves the web UI's port
and password handling into `opencode-web-command.sh` and makes the port
configurable through `AGENTDEV_OPENCODE_PORT`; the credential source below reads
the same port, password, and readiness probe, so it works in the Dev Container
and the standalone container alike.

The bash run budgets (`timeout 1200` per run, the renewed `opencode_wait`) are
not a measure of run time: they absorbed OpenCode sessions stalled on prompts
the suite never answered. They are starting values only; the port sets each
test's budget from measured wall times.

## Approach

**Layout.** `scripts/e2e/` is the root for e2e suites; `scripts/e2e/conftest.py`
holds the live gate every suite there shares. The suite is
`scripts/e2e/iwe-workflows/`: its `fixtures/` (moved unchanged), a `conftest.py`
with the clone and harness fixtures, one driver module per harness, and test
modules per harness. `scripts/e2e` stays out of `pyproject` `testpaths`, and the
suite runs through `uv run pytest scripts/e2e/iwe-workflows`.

**Live gate.** The mechanism of `.agents/plugins/self-improve/tests/conftest.py`
with its own names: tests marked `e2e` are skipped at collection unless
`E2E_RUN_LIVE` is set to a value outside `''`, `0`, `false`, `no`, `off`. The
skip happens at collection, so naming a node id or passing `-m` cannot start a
paid session. Opting into one suite never runs the other.

**Clone per test.** A session-scoped fixture bundles `HEAD`, builds the fixture
repository once per xdist worker (active plans cancelled, fixture plans
committed as `base`, the open-question edit committed as `open_question`), and
each test clones it under `.tmp/e2e/iwe-workflows/<test id>/clone` at the commit
its scenario needs. `publish-e2e.sh` writes `../published.marker`, so the
per-test parent directory isolates the marker as well. Every git write targets
the clone, and the fixture refuses a clone that resolves to another repository,
as `in_clone` does today.

**Checks.** Each bash check becomes one assertion, scenario by scenario, and a
failed assertion shows the transcript excerpt it judged. The "run completed"
check is each test's first assertion. Gaps that belong to a harness stay
explicit: Codex has no dispatch prompt text and cannot write the marker, the
skills scenario is Codex-only, and only Claude Code's explore asserts a clean
tree.

**OpenCode server per test.** Each test starts
`opencode serve --hostname 127.0.0.1 --port <free port>` with its own `HOME`,
`XDG_*`, `OPENCODE_CONFIG_DIR`, and `OPENCODE_SERVER_PASSWORD`, following
`verify-workspace-host.ts`. Its config loads the bridge from the clone's own
catalog, so the "installed catalog differs" precondition goes away for OpenCode
(Codex keeps its own). The fixture polls until `agentdev:*` commands are served
for the clone, as the bridge activates on a directory's first request, and kills
the server's process group at teardown, failed test or not. The suite talks to
the server over HTTP — `POST /api/session` with `location.directory` set to the
clone, `POST /api/session/{id}/command`,
`POST /api/experimental/session/{id}/wait`, `GET /api/session/{id}/message`
paged by cursor, `POST /api/session/{id}/interrupt` — under its own deadline.

**OpenCode credential.** Tests use the user's ChatGPT login
(`chatgpt-token-sharing`), whose access token lives about an hour on OpenCode
2.0.32, the pinned version. The source is the Coder web UI server that
`opencode-web-start.sh` runs on `127.0.0.1` at `AGENTDEV_OPENCODE_PORT` (default
`4096`), authenticated (user `opencode`) with `OPENCODE_SERVER_PASSWORD` or the
`~/.local/share/opencode/agentdev-server-password` file. The source counts as up
only when an authenticated `GET /api/info` returns a 2.x `version`; v2 serves
its web UI page outside `/api/` with status 200 and no password, so no other
path can show the API is up. Before each test the fixture reads the active
`openai` credential from the source with `GET /api/credential`. When it expires
within the test's budget, the fixture sends the source a one-token prompt in a
throwaway session (deleted afterwards) so the source refreshes it. It then seeds
the test's server with `POST /api/credential`, copying `methodID` and `metadata`
verbatim and replacing `refresh` with `"withheld"`. Only the source ever holds
or rotates the real refresh token. An expired seeded token fails a session with
`{"type": "provider.auth"}`, which the suite reports as an exhausted budget.
When the source is not up, the OpenCode tests skip with a reason naming
`opencode-web-start.sh`; the suite never opens the user's OpenCode data
directory itself.

**Claude Code and Codex.** Same clone fixture; their drivers port
`claude_run`/`codex_run` and the transcript readers as they are. Claude Code and
Codex keep the user's own configuration and login, as the self-improve smoke
suite does for Claude Code. Codex rollouts are found by thread id, which stays
unambiguous with tests running in parallel.

**Order.** OpenCode first, then Claude Code, then Codex. `run.sh` moves with the
suite and loses each harness's section once that harness passes in pytest; it is
deleted with the last one.

Rejected:

- **API key through a custom provider in `opencode.json`** — the maintainer uses
  the ChatGPT login, and a custom provider would have to reproduce the ChatGPT
  integration's request wiring by hand.
- **Copying the full credential, refresh token included, into each server** —
  the refresh token rotates, so a test server refreshing it can sign the user
  out.
- **A fixture-started source server on `~/.local/share/opencode`** — a second
  process on the web UI's SQLite database, both able to refresh the same
  rotating token.
- **One scenario × harness matrix** — it hides the harness-specific gaps,
  weakening or silently adding checks.

Assumptions:

- The worker cap starts at 3, set in the suite's conftest, which refuses a
  larger `-n`; the timeout task confirms or changes it against the provider's
  rate limits.
- Budgets start at the bash values and are replaced by measured ones.
- Test module names carry the suite prefix (`test_iwe_workflows_<harness>.py`)
  so they never collide with another directory's test basenames.

## Implementation Steps

### Task 1: Gate live e2e runs

**Files:** Create: `scripts/e2e/conftest.py`,
`scripts/tests/test_e2e_live_gate.py`; Modify: `pyproject.toml`

- [x] `scripts/e2e/conftest.py` skips every test marked `e2e` at collection
  unless `E2E_RUN_LIVE` is set to a value outside `''`, `0`, `false`, `no`,
  `off`, with a skip reason naming the variable; the `e2e` marker is registered
  in `pyproject.toml` `markers`.
  - **Evidence:** Commit "test(e2e): gate live e2e runs on E2E_RUN_LIVE";
    `uv run pytest scripts/tests/test_e2e_live_gate.py` runs the copied gate and
    asserts the skip reason names `E2E_RUN_LIVE` (24 passed).
- [x] `scripts/tests/test_e2e_live_gate.py` proves a marked test is skipped for
  each off value, including when selected by node id or `-m e2e`, and runs when
  the variable is `1`.
  - **Evidence:** Same commit; `test_skipped_unless_opted_in` covers unset and
    every off value by path, node id, and `-m e2e`, and
    `test_runs_when_opted_in` runs it at `1` (24 passed).

### Task 2: Build one clone per test

**Files:** Create: `scripts/e2e/iwe-workflows/conftest.py`,
`scripts/e2e/iwe-workflows/clone.py`,
`scripts/tests/test_e2e_iwe_workflows_clone.py`; Modify: move
`scripts/e2e/20261007-agent-owned-ship-implement/` (`run.sh`, `fixtures/`) to
`scripts/e2e/iwe-workflows/`

- [x] The suite and its fixtures live at `scripts/e2e/iwe-workflows/`, and the
  moved `run.sh` still builds its clone from there.
  - **Evidence:** Commit "test(e2e): build one clone per IWE workflow test"
    moves the directory with `git mv`; `run.sh --harness claude` with a stub
    `claude` on `PATH` builds `.tmp/e2e/iwe-workflows/clone` and prints its
    `base` and `open_question` commits.
- [x] A session fixture builds the fixture repository once per worker with only
  the fixture plans active and the `base` and `open_question` commits, and a
  per-test fixture clones it under `.tmp/e2e/iwe-workflows/<test id>/clone` at a
  requested commit.
  - **Evidence:** Same commit; `fixture_repo` (session, per `worker_id`) and
    `clone_at` in the suite's `conftest.py`; `test_e2e_iwe_workflows_clone.py`
    covers the `base`/`open_question` commits and the per-test directory names
    (5 passed).
- [x] The clone facts `run.sh` checks — marker present or absent, `HEAD`, clean
  tree, plan active or done, release notes unchanged, greet task untouched — are
  helpers on the clone, and every git write refuses a clone that resolves to
  another repository.
  - **Evidence:** Same commit; `Clone` in `clone.py` carries `has_marker`,
    `head`, `status`, `plan_active`, `plan_done`, `unreleased_diff`, and
    `greet_untouched`, and `Repo.git` checks the toplevel before every command.
- [x] `scripts/tests/test_e2e_iwe_workflows_clone.py`, unmarked and model-free,
  proves two clones share no commits or marker, the fixtures are the only active
  plans, and the refusal fires.
  - **Evidence:** Same commit;
    `uv run pytest scripts/tests/test_e2e_iwe_workflows_clone.py` — 5 passed, no
    marker, no model.

### Task 3: Seed OpenCode servers from the web UI's credential

**Files:** Create: `scripts/e2e/iwe-workflows/opencode_credential.py`,
`scripts/tests/test_e2e_iwe_workflows_credential.py`; Modify:
`scripts/e2e/iwe-workflows/conftest.py`

- [x] The source is `127.0.0.1` at `AGENTDEV_OPENCODE_PORT` (default `4096`)
  with `OPENCODE_SERVER_PASSWORD` or the
  `~/.local/share/opencode/agentdev-server-password` file; OpenCode tests skip
  with a reason naming `opencode-web-start.sh` unless an authenticated
  `GET /api/info` returns a 2.x `version`.
  - **Evidence:** Commit "test(e2e): seed OpenCode test servers from the web
    UI's login"; `test_e2e_iwe_workflows_credential.py` covers the port and
    password sources and rejects 1.x, a wrong password, and a closed port, each
    naming the start script (11 passed); `require_v2` returns `2.0.32` against
    the pinned binary.
- [x] Per test, the active `openai` credential is read from the source; when it
  expires within the test's budget, a one-token prompt in a throwaway session,
  deleted afterwards, makes the source refresh it first.
  - **Evidence:** Same commit; the `opencode_login` fixture calls
    `fresh_credential` with `OPENCODE_BUDGET`, and
    `test_expiring_token_is_refreshed_in_a_throwaway_session` asserts the
    create, prompt, wait, delete, re-read order against a fake source.
- [x] The seeded copy keeps `methodID` and `metadata` verbatim and carries
  `refresh: "withheld"`; no credential value is written to a log, a transcript,
  or a failure message.
  - **Evidence:** Same commit; `test_seed_withholds_the_refresh_token`,
    `test_unrefreshed_token_fails_without_its_value`, and
    `test_failed_credential_requests_never_echo_the_body`; an OpenCode 2.0.32
    server accepts the seed payload and reports `refresh: withheld` with
    `metadata` intact.

### Task 4: Run an isolated OpenCode server per test

**Files:** Create: `scripts/e2e/iwe-workflows/harness_opencode.py`,
`scripts/tests/test_e2e_iwe_workflows_opencode_server.py`; Modify:
`scripts/e2e/iwe-workflows/conftest.py`,
`scripts/e2e/iwe-workflows/fixtures/opencode.json`

- [x] A per-test fixture starts `opencode serve` (`OPENCODE_BIN` or `opencode`)
  on a free port with its own `HOME`, `XDG_*`, `OPENCODE_CONFIG_DIR`, and
  password; its config loads the bridge from the clone's catalog and keeps the
  fixture's permissions and small model; the server is seeded per Task 3 and its
  process group is killed at teardown, failed test or not.
  - **Evidence:** Commit "test(e2e): run an isolated OpenCode server per test";
    the `opencode` fixture in the suite's `conftest.py` stops every server it
    started after `yield`;
    `OPENCODE_BIN=<v2.0.32> uv run pytest scripts/tests/test_e2e_iwe_workflows_opencode_server.py`
    (4 passed) checks the isolated `HOME`, the clone's bridge and small model in
    the config, the withheld refresh token, and an empty process group after
    `stop`.
- [x] The fixture waits until the server serves `agentdev:*` commands for the
  clone.
  - **Evidence:** Same commit; `start_server` returns only after
    `wait_for_catalog` sees `agentdev:iwe-ship` for the clone, asserted by
    `test_server_is_isolated_and_serves_the_clone_catalog`.
- [x] A client runs one command in a fresh session located in the clone with the
  question tool denied, waits under the suite's own deadline, interrupts a
  session that outlives it, pages every message by cursor, and saves the
  transcript beside the clone.
  - **Evidence:** Same commit; `test_run_saves_every_message_beside_the_clone`
    checks the session's location, the saved `transcripts/<name>.jsonl`, and
    one-message pages matching the full read;
    `test_a_session_outliving_the_deadline_is_interrupted` covers the deadline.

### Task 5: Port the OpenCode scenarios

**Files:** Create: `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py`,
`scripts/e2e/iwe-workflows/scenarios.py`

- [x] Ship, ship-approved, ship-all, implement, and explore are one `e2e` test
  each, asserting every check `run_opencode` makes, one assertion per check,
  each failure showing the transcript excerpt it judged.
  - **Evidence:** Commit "test(e2e): port the OpenCode IWE workflow scenarios";
    the five tests are gated off by default, and with `E2E_RUN_LIVE=1` against a
    scratch 2.0.32 source holding a made-up login, each runs clone, server,
    seed, catalog, and command, then fails its first assertion with the
    `provider.auth` budget reason and a transcript excerpt.

### Task 6: The OpenCode suite passes

- [x] `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows -k opencode -n 3`
  passes every OpenCode test with the default test models.
  - **Evidence:** Live run on 2026-10-19 at `ec3c371` with OpenCode 2.0.32,
    `openai/gpt-6.1-sol` and `gpt-6-luna`, sourced from a logged-in v2 server: 5
    passed in 120.59s; each Ship transcript holds exactly one `subagent` call,
    implement and explore none.

### Task 7: Retire run.sh's OpenCode section

**Files:** Modify: `scripts/e2e/iwe-workflows/run.sh`

- [x] `run.sh` no longer offers or runs the OpenCode harness.
  - **Evidence:** Commit "test(e2e): retire run.sh's OpenCode harness";
    `run.sh --harness opencode` and `--opencode-model` exit 2, shellcheck
    passes, and a stub-`claude` run still builds the clone and runs its checks.

### Task 8: Port the Claude Code scenarios

**Files:** Create: `scripts/e2e/iwe-workflows/harness_claude.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py`

- [x] A driver runs `claude -p` in the clone with the clone's catalog, the
  allowed tools, and stream-json output under the suite's deadline, and reads
  tool calls, subagents' included, from the transcript.
  - **Evidence:** Commit "test(e2e): port the Claude Code IWE workflow
    scenarios"; `run_claude` in `harness_claude.py` kills the run's process
    group at `CLAUDE_BUDGET` and `ClaudeTranscript.calls` reads every `tool_use`
    block; the live run below found each Ship's one `Agent` call.
- [x] Ship, ship-approved, ship-all, implement, and explore are one `e2e` test
  each, asserting every check `run_claude` makes.
  - **Evidence:** Same commit; `test_iwe_workflows_claude.py` holds the five
    tests, one assertion per `run_claude` check including explore's clean tree,
    all gated off without `E2E_RUN_LIVE`.

### Task 9: The Claude Code suite passes

- [x] `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows -k claude -n 3`
  passes every Claude Code test.
  - **Evidence:** Live run on 2026-10-19 with the Task 8 code (`ef279c7`): 5
    passed in 156.71s.

### Task 10: Retire run.sh's Claude Code section

**Files:** Modify: `scripts/e2e/iwe-workflows/run.sh`

- [x] `run.sh` no longer offers or runs the Claude Code harness.
  - **Evidence:** Commit "test(e2e): retire run.sh's Claude Code harness";
    `run.sh --harness claude` exits 2, shellcheck passes, and a default run
    builds the clone and goes straight to the Codex section.

### Task 11: Port the Codex scenarios

**Files:** Create: `scripts/e2e/iwe-workflows/harness_codex.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_codex.py`,
`scripts/tests/test_e2e_iwe_workflows_codex_publish.py`

- [x] A driver runs `codex exec -s workspace-write --json` in the clone under
  the suite's deadline and reads spawns and child commands from the session
  rollouts by thread id; the Codex tests fail with the reinstall hint when the
  installed catalog differs from the clone's.
  - **Evidence:** Commit "test(e2e): port the Codex IWE workflow scenarios";
    `catalog_mismatch` reported the stale 4.2.0 install with the
    `reinstall-agentdev-codex.sh` hint and cleared after the reinstall;
    `test_e2e_iwe_workflows_codex_publish.py` (12 passed) pins which child
    commands count as a publish run.
- [x] Skills, ship, ship-approved, ship-all, implement, and explore are one
  `e2e` test each, asserting every check `run_codex` makes.
  - **Evidence:** Same commit; `test_iwe_workflows_codex.py` holds the six
    tests. The publish-run check also counts a chain whose prefix holds escaped
    quotes or whose commands are newline-separated, both of which `run.sh`'s
    pattern missed; reads of the script still do not count.

### Task 12: The Codex suite passes

- [x] `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows -k codex -n 3`
  passes every Codex test.
  - **Evidence:** Live run on 2026-10-19 at `c2ea0b5`, installed catalog
    matching the clone: 6 passed in 542.79s.

### Task 13: Delete run.sh

**Files:** Delete: `scripts/e2e/iwe-workflows/run.sh`

- [x] `run.sh` is gone, and every check it made maps to a pytest assertion in a
  scenario-by-scenario table recorded under `## Verification results`.
  - **Evidence:** Commit "test(e2e): delete run.sh"; the table's cells account
    for all 55 scenario `check` calls in `run.sh` as of `4d2a902`, and no file
    outside the plans references the script.

### Task 14: Eval and tune timeouts

**Files:** Modify: `scripts/e2e/iwe-workflows/scenarios.py`

- [x] Each scenario's wall time on each harness is measured from full live runs,
  and each test's budget is set from those measurements in place of the bash
  values; the credential fixture's minimum remaining token life follows the
  OpenCode budget, and the worker cap is confirmed or changed against the
  provider's rate limits.
  - **Evidence:** Commit "test(e2e): set e2e budgets from measured wall times";
    slowest scenario per harness at `-n 3` in the Task 6, 9, and 12 runs:
    OpenCode ship-all 95s, Claude Code ship-all 138s, Codex explore 318s, giving
    budgets of 300s, 420s, and 900s; `opencode_login` reads `OPENCODE_BUDGET`.
    Cap of 3 confirmed: Claude Code's rate-limit events all report `allowed`,
    and no run logged a 429.

### Task 15: The whole suite passes in parallel

- [x] `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows -n 3` passes every
  test on all three harnesses with the tuned budgets.
  - **Evidence:** Live run on 2026-10-19 at `5c0a5a2`: 16 passed in 422.43s; the
    slowest test, Codex ship-approved at 255s, is within its 900s budget.

## Spec changes

None — no behavioral change. The suite is tooling only this repository runs.

## Depends on

- [Make OpenCode v2 the devcontainer default](20261018-opencode-v2-default.md) —
  the suite needs v2 in the image, and that plan's Verification runs the
  `run.sh` OpenCode harness this plan retires.

## Verification

- `uv run pytest scripts/tests/test_e2e_live_gate.py scripts/tests/test_e2e_iwe_workflows_clone.py`
- `uv run pytest scripts/e2e` with `E2E_RUN_LIVE` unset reports every test
  skipped and starts no session.
- `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows -n 3` passes on a
  devcontainer whose OpenCode is v2 (the image, or the `agentic_tools` role
  applied) with the web UI server running and a ChatGPT login.
- A single scenario runs alone with `-k`.
- The scenario-by-scenario check table shows every `run.sh` check as an
  assertion, none weaker.
- `iwe normalize` and `iwe schema validate` pass.

## Verification results

Every `run.sh` check maps to one assertion in `test_iwe_workflows_<harness>.py`.
Every test also asserts first that its run completed: a final text part on
OpenCode, a `result` event on Claude Code, a `turn.completed` event on Codex.

| Scenario      | `run.sh` check                      | OpenCode | Claude Code | Codex                       |
| ------------- | ----------------------------------- | -------- | ----------- | --------------------------- |
| skills        | each gated skill not listed         | —        | —           | `test_skills`               |
| ship          | one `iwe-shipper` dispatch          | yes      | yes         | spawn, plus fresh spawn     |
| ship          | prompt names the plan               | yes      | yes         | — (prompt encrypted)        |
| ship          | publish did not run                 | marker   | marker      | no publish child command    |
| ship          | no commit                           | yes      | yes         | yes                         |
| ship          | plan still active                   | yes      | yes         | yes                         |
| ship-approved | one `iwe-shipper` dispatch          | yes      | yes         | spawn, plus fresh spawn     |
| ship-approved | approval quoted verbatim            | yes      | yes         | — (prompt encrypted)        |
| ship-approved | planted sentence left out           | yes      | yes         | — (prompt encrypted)        |
| ship-approved | publish ran                         | marker   | marker      | publish child command       |
| ship-approved | plan done                           | yes      | yes         | — (marker blocked)          |
| ship-approved | internal plan adds no release entry | yes      | yes         | —                           |
| ship-all      | one `iwe-shipper` dispatch          | yes      | yes         | yes                         |
| implement     | rulebook read in session            | `read`   | `Read`      | rollout text                |
| implement     | nothing dispatched                  | yes      | yes         | yes                         |
| implement     | task unticked, file absent          | yes      | yes         | yes                         |
| explore       | nothing dispatched                  | yes      | yes         | yes                         |
| explore       | no Ship or Implement skill          | `skill`  | `Skill`     | no workflow `SKILL.md` read |
| explore       | publish did not run                 | yes      | yes         | —                           |
| explore       | no commit                           | yes      | yes         | yes                         |
| explore       | clean tree                          | —        | yes         | —                           |

A dash marks a gap that `run.sh` had too; none was added or dropped. One check
is stronger: Codex's publish-command pattern also counts a chain whose prefix
holds escaped quotes or whose commands are newline-separated, both of which
`run.sh` misread as no publish.

Verification checks, 2026-10-19 at `5c0a5a2`:

- The four model-free suites (`test_e2e_live_gate.py`,
  `test_e2e_iwe_workflows_clone.py`, `..._credential.py`,
  `..._codex_publish.py`) pass: 52 passed.
- `uv run pytest scripts/e2e` with `E2E_RUN_LIVE` unset: 16 skipped, no session
  started.
- `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows -n 3` with OpenCode
  2.0.32 sourced from a logged-in v2 web server: 16 passed in 422.43s.
- A single scenario runs alone: `-k 'claude and implement'` passed.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- New scenarios or checks beyond what `run.sh` asserts.
- Running the suite in CI.
- Isolating Claude Code or Codex configuration and logins.
- Editing
  [20261007-agent-owned-ship-implement](20261007-agent-owned-ship-implement.md)
  or [20261018-opencode-v2-default](20261018-opencode-v2-default.md) to point at
  the new path.

## Key references

Verified anchor points (line numbers as of 2026-10-19):

- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:97` — `build_clone`
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:129` —
  `cancel_active_plans`
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:154` — `reset_to`;
  clone facts follow at 161–175
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:184` — `claude_run`
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:209` — `run_claude`
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:305` — `codex_run`
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:312` — `codex_catalog`
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:318` — `run_codex`
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:385` —
  `opencode_messages`
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:397` — `opencode_wait`
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:405` — `opencode_run`
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:445` — `run_opencode`
- `scripts/e2e/20261007-agent-owned-ship-implement/fixtures/bin/publish-e2e.sh:5`
  — marker written beside the clone
- `.agents/plugins/self-improve/tests/conftest.py:25` — `LIVE_MARKERS`,
  `LIVE_OPT_IN_ENV`, `LIVE_OPT_OUT_VALUES` (25–29)
- `.agents/plugins/self-improve/tests/conftest.py:38` —
  `pytest_collection_modifyitems`
- `.agents/plugins/agentdev/tests/opencode/verify-workspace-host.ts:33` —
  isolated server environment
- `.agents/plugins/agentdev/tests/opencode/verify-workspace-host.ts:108` —
  `opencode serve` spawn
- `.agents/plugins/agentdev/tests/opencode/verify-workspace-host.ts:143` —
  `catalog`, polling for the bridge
- `.devcontainer/scripts/opencode-web-start.sh:23` — web UI server port and
  password source (23–38)
- `ansible/roles/agentic_tools/defaults/main.yml:10` —
  `agentic_tools_opencode_version`
- `pyproject.toml:29` — `testpaths`
- `pyproject.toml:36` — `markers`
