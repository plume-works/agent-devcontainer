# E2E testing vs plan implementation — Nov 1 to Nov 3, 2026

Window: 2026-11-01 00:00 → 2026-11-03 09:36 UTC. No tests were run to produce this report; every
number comes from existing logs.

**Tokens** = input + cache write + cache read + output. Cache reads make up about 95% of most
totals, so output tokens are shown alongside. USD is the list-price `costUSD` the session logs
record; it is given for reference only. The cost asked for is token usage.

## Sources

| Source                                                       | What it gives                                                           | Limits                                                                 |
| ------------------------------------------------------------ | ----------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| agent-dev2 `~/.claude/projects/*.jsonl`, including subagents | Exact per-message usage for the agent-dev2 sessions                     | None of them ran e2e                                                   |
| agent-dev2 `~/.claude/projects/-tmp-agentdev-tests-e2e-*`    | Exact usage of 65 live **Claude Code** e2e test runs, 18 distinct tests | From Oct 30–31, just before the window; no OpenCode runs               |
| Session API `result` events, agent-dev1, 3 and 4             | Per-turn usage, including subagents, for 31 Remote Control sessions     | Covers only the session itself, not the e2e child processes it started |

**Not available:**

- **Token cost of the e2e runs inside the window.** pytest starts each test as a separate agent
  process. Their transcripts are on agent-dev1 under `/tmp/agentdev-tests/e2e-*` and
  `~/.claude/projects/-tmp-agentdev-tests-e2e-*`, which this machine cannot reach (`coder` is
  not logged in).
- **Any OpenCode e2e cost.** The local `opencode.db` holds no sessions.
- **Development cost of tests written before Oct 29.** No local session ever edited
  `scripts/e2e/`; that work happened on other machines or before the logs available here.

## 1. Where e2e ran, what the tests were, and what they caught

| Session                                | Plan or PR                                                                       | Tests run                                                                                                                                                                                                                                                                                   | What they caught                                                                                                                                                                                                                                                                                                 | Effect                                                                                                                                                                           |
| -------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| agent-dev1 `LsN5Qx`, Nov 3 04:00–07:54 | `20261031-verify-report-in-chat` and `20261031-model-invocable-implement` (#663) | Claude Code: plan 2 Task 6 (8 passed); plan 1 suite (4 of 6 passed); `test_ship*` reruns; `test_implement_all`; `test_implement_relayed_narrowing`; `test_implement_coordinator_requested`; `test_explore`. OpenCode: 6 Ship cases, relayed narrowing (failed twice), coordinator requested | **Product bug:** `test_ship_approved` and `test_ship_reuses_saved_report` showed the shipper agent rewording the Verify report. The plan task requiring it to be carried verbatim was already ticked. **Routing gap:** OpenCode's `iwe-revision-evaluator` rejected a relayed approval that Claude Code accepted | Fix `eba88949`. Plan revisions `0b0de304` (new Task 9) and `5526b211` (scenario narrowed; `test_implement_coordinator_requested` replaced relayed narrowing). **Positive loop.** |
| agent-dev1 `LtSmEM`, Nov 1 08:00–08:16 | Conflict-free layout (#616), Task 12                                             | Full Claude Code and OpenCode suites at `faf2c7e0`: 21 of 21 and 21 of 21 passed. The first launch left out `E2E_RUN_LIVE`                                                                                                                                                                  | Nothing                                                                                                                                                                                                                                                                                                          | Used only as acceptance (`50acd04e`). **No loop.**                                                                                                                               |
| agent-dev1 `LrHezB`, Nov 3 01:25–01:43 | `20261102-autonomy-loop` (planning session)                                      | New autonomy scenarios, red run on Claude Code: 6 of 16 failed                                                                                                                                                                                                                              | Only that most scenarios were not red                                                                                                                                                                                                                                                                            | Plan's test design rewritten (PR #656); test code written in a planning session had to be reverted. **Loop on test design only.**                                                |
| agent-dev1 `LtSCyz`, Nov 3 07:57–09:32 | `20261102-autonomy-loop` (implementation)                                        | `test_autonomy_loop_{claude,opencode}.py` and others. Red: 9 of 14 failed. Green: 17 of 18 passed on each harness, over about 6 reruns                                                                                                                                                      | **Harness bugs only:** permission prompts; `section()` in `clone.py` stopping at a fenced heading, which made one guard check nothing; a no-op fixture; the `FAILS_OUTSIDE` regex; a flaky OpenCode test                                                                                                         | All e2e changes reverted (`55025cbc`); e2e moved to Out of scope (`2477b950`) at your request. **Net negative.**                                                                 |

Every other session in the window ran no e2e. That includes the Explore-interview plan (#624 and
#632), where e2e was put out of scope at planning time, and the re-review (#657), evidence gate
(#660) and Codex removal (#602) skill or harness changes.

## 2. Cost of each test run (Claude Code harness, measured on Oct 30–31)

Median tokens per run of each test. Each run includes its subagents.

| Test                                     | Runs | Median total | Median output | Range       |
| ---------------------------------------- | ---: | -----------: | ------------: | ----------- |
| `implement_revises`                      |    3 |    1,926,952 |        20,989 | 1.85M–2.01M |
| `implement_all`                          |    3 |    1,531,038 |        13,921 | 1.33M–1.57M |
| `implement_stops_on_rejection`           |    3 |    1,386,434 |        13,873 | 1.29M–1.51M |
| `ship_all`                               |    3 |    1,083,226 |         8,245 | 0.96M–1.36M |
| `implement_stops_on_escalation`          |    3 |      998,334 |        10,398 | 0.99M–1.14M |
| `implement_on_main`                      |    5 |      950,250 |         5,644 | 0.74M–1.03M |
| `ship_approved`                          |    3 |      798,579 |         7,414 | 0.62M–0.80M |
| `implement_verifies`                     |    4 |      786,918 |         6,306 | 0.70M–0.83M |
| `ship_reuses_saved_report`               |    8 |      473,577 |         5,369 | 0.37M–0.65M |
| `verify_fresh_reruns_without_forwarding` |    2 |      372,148 |         4,498 | 0.36M–0.39M |
| `verify_approved`                        |    3 |      368,620 |         4,996 | 0.37M       |
| `dirtying_verification_is_not_saved`     |    1 |      356,784 |         5,968 | n/a         |
| `needs_decision_not_reused`              |    8 |      356,280 |         4,968 | 0.27M–0.46M |
| `verify`                                 |    3 |      324,077 |         4,810 | 0.31M–0.35M |
| `ship`                                   |    3 |      298,228 |         3,004 | 0.30M       |
| `verify_refuses_dirty_worktree`          |    4 |      117,819 |           492 | 0.12M       |
| `implement_stops_on_narrowing`           |    3 |       87,927 |         1,402 | 0.09M–0.14M |
| `implement`                              |    3 |       87,392 |         1,187 | 0.08M–0.09M |

### Cost of one full run

- **Measured, 18 Claude Code tests:** about **12.3M tokens** (123K output) as the sum of the
  medians. The three measured passes of the suite on Oct 30 cost 14.3M, 12.2M and 12.7M tokens.
- **Claude Code suite on `main` today:** 23 test functions, plus the 4 `test_evaluator` variants.
  The 8 tests with no logged runs are `implement_requested`, `implement_coordinator_requested`,
  `plan_does_not_implement`, `explore`, and the 4 `evaluator` variants. At the measured average of
  0.68M per test, a full pass is about **17.8M tokens**. This is an extrapolation, not a
  measurement.
- **OpenCode suite:** not available, since no OpenCode run logs are reachable. It uses OpenAI
  models, so its usage would not be directly comparable anyway.
- **All 65 Claude Code test runs logged on Oct 30–31:** **42.7M tokens**.

## 3. Cost to develop the tests (the session's own usage)

These figures are the session's own turns only. The e2e runs it started are **not included**;
see the first item under "Not available".

| Work                                                                                                                                                     | Slice                | Tokens | Output | USD (list) |
| -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | -----: | -----: | ---------: |
| Autonomy-loop scenarios: writing, red and green runs, harness fixes (all reverted)                                                                       | `LtSCyz` 07:57–09:32 |  30.7M |   138K |     $12.37 |
| Autonomy-loop scenarios first drafted, plus red run                                                                                                      | `LrHezB` 01:25–01:43 |   6.2M |    47K |      $2.96 |
| `test_implement_coordinator_requested` and the dropped relayed-narrowing test, including both plan revisions                                             | `LsN5Qx` 06:24–07:34 |  17.7M |   108K |      $8.63 |
| Plan 2 implementation turn (skill changes, `test_implement_requested`, `test_plan_does_not_implement`, the Ship fix). The test share cannot be separated | `LsN5Qx` 04:40–04:53 |  14.6M |   104K |      $7.04 |
| Steering the #616 acceptance run                                                                                                                         | `LtSmEM` 07:58–08:16 |   4.0M |     8K |      $1.25 |
| Stripping e2e out of the autonomy-loop plan and shipping it                                                                                              | `LtSCyz` 09:33–09:36 |   2.6M |    13K |      $1.82 |

**Tests that were kept versus discarded:**

- **Kept:** the #663 tests, about 18–32M tokens of development.
- **Discarded:** the autonomy-loop tests, about **37M** tokens of development before any run cost.

## 4. Sessions that ran e2e versus sessions that did not

| Group                                                                               |                                                           Sessions |     Tokens |    Output | Share |
| ----------------------------------------------------------------------------------- | -----------------------------------------------------------------: | ---------: | --------: | ----: |
| Ran e2e: `LsN5Qx`, `LtSCyz`, `LrHezB`, `LtSmEM`, counting only their in-window part |                                                                  4 |     202.7M |      863K |   21% |
| No e2e, agent-dev1, 3 and 4 (session API)                                           |                                                                 21 |     534.2M |     1.83M |   56% |
| No e2e, agent-dev2 (local transcripts, including subagents)                         | 10 that used more than 100K tokens, plus small `self-improve` runs |     215.6M |      850K |   23% |
| **Total**                                                                           |                                                                    | **952.5M** | **3.55M** |       |

- **Average per session:** a session that ran e2e used about 51M tokens. A session that did not
  used about 24M (750M across 31 sessions).
- **Mix of work:** the e2e sessions are all long implementation sessions, so their size does not
  come from e2e alone.
- **Not included:** the tokens of the e2e runs themselves. Using the Claude Code medians, the
  roughly 30–40 Claude Code test runs in the window would add very roughly another 20–30M tokens,
  plus the OpenCode runs. This is an estimate, not a measurement.

**Biggest sessions with no e2e:**

- 81–120M: Docker GC (`Lr2gKx`). This is shown as a range because its per-turn sum and its
  cumulative counter disagree after compactions.
- 78.8M: manual stacked PRs, agent-dev2.
- 76.8M: re-review (`LpwXk6`).
- 67.2M: re-request bug, agent-dev2.
- 56.6M: pre-commit (`Lt6d1o`).

## 5. Data-quality notes

- **Cross-checks:** for 28 of 31 sessions, the sum of the per-turn usage equals the session's
  cumulative counter exactly. The three that differ are shown with their range or noted below:
  - `Lr2gKx`: 81M per-turn versus 120M cumulative.
  - `Lt4Mq8`: 62.8M versus 66.5M, mostly from the Oct 31 portion.
  - `Lu7TQ4`, the PR #667 fork: 16.5M versus 21.9M.
- **Classification:** `Lu7TQ4` holds the e2e history imported from `LsN5Qx` but ran no e2e of its
  own, so it is counted as not running e2e.
- **Excluded:** this analysis session, and agent-dev2 sessions that started after 09:36 on Nov 3.
- **Transcription:** the session-API figures were copied by hand from tool output by the
  collection agents. The exact cross-check matches above are the evidence they are correct.
