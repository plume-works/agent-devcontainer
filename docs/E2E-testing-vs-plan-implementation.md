# E2E testing vs plan implementation — Nov 1 to Nov 3, 2026

Window: 2026-11-01 00:00 → 2026-11-03 09:36 UTC. No tests were run to produce this report; every
number comes from existing logs.

**Tokens** = input + cache write + cache read + output. Cache reads make up about 90–95% of most
totals, so output tokens are shown alongside. The cost asked for is token usage. The USD figure
for Claude sessions is the list-price `costUSD` their logs record, given for reference only.

## Sources

| Source                                                                             | What it gives                                                                                                                            |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| agent-dev1 `~/.claude/projects/-tmp-agentdev-tests-e2e-*`, copied over `coder ssh` | Exact usage of **all 127 Claude Code e2e test sessions** in the window, including subagents, in 4 batches                                |
| agent-dev1 `/tmp/agentdev-tests/e2e/*/…/opencode/data/opencode/opencode.db`        | OpenCode e2e usage, but **only the last run of 12 tests** in the #663 batch                                                              |
| agent-dev2 `~/.claude/projects/-tmp-agentdev-tests-e2e-*`                          | 65 Claude Code e2e runs from Oct 30–31, used only as an extra baseline                                                                   |
| agent-dev2 local transcripts, including subagents                                  | Exact usage of the agent-dev2 sessions, none of which ran e2e                                                                            |
| Session API `result` events, agent-dev1, 3 and 4                                   | Per-turn usage, including subagents, of 31 Remote Control sessions. A session's own figure does not include the e2e processes it started |

**Not available:**

- **OpenCode e2e cost**, except for those 12 runs. Each OpenCode test keeps its database in a
  per-test folder, and the next run of that test overwrites it. The folders for the #616 and
  autonomy-loop batches no longer exist on agent-dev1.
- **Development cost of tests written before the window.** No transcript in reach shows that
  work.

## 1. Where e2e ran, what the tests were, and what they caught

| Batch on agent-dev1           | Session and plan                                                                           | Tests                                                                                                                                                                                                                   | What they caught                                                                                                                                                                             | Effect                                                                                |
| ----------------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `4e03277f`, Nov 1 08:00–08:08 | `LtSmEM`, conflict-free layout (#616), Task 12                                             | Full Claude Code suite: 21 tests, 21 passed; full OpenCode suite: 21 passed                                                                                                                                             | Nothing                                                                                                                                                                                      | Used only as acceptance. **No loop.**                                                 |
| `10caffc3`, Nov 3 01:32–01:41 | `LrHezB`, `20261102-autonomy-loop`, planning fork                                          | 16 new autonomy scenarios, red run, Claude Code: 6 failed and 10 passed, plus 1 rerun                                                                                                                                   | Only that most scenarios were not red                                                                                                                                                        | Plan's test design rewritten (PR #656). **Loop on test design only.**                 |
| `66cc0543`, Nov 3 04:18–07:42 | `LsN5Qx`, `20261031-verify-report-in-chat` and `20261031-model-invocable-implement` (#663) | Claude Code: 22 sessions over 12 tests. `ship_reuses_saved_report` ×6, `ship_approved` ×3, `ship_all` ×3, plus `implement_relayed_narrowing`, `implement_coordinator_requested` and others. OpenCode: the same 12 tests | **Product bug:** the shipper agent reworded the Verify report (`ship_approved`, `ship_reuses_saved_report`). **Routing gap:** OpenCode rejected a relayed approval that Claude Code accepted | Fix `eba88949`. Plan revisions `0b0de304` and `5526b211`. **The only positive loop.** |
| `d409dce6`, Nov 3 08:07–09:25 | `LtSCyz`, `20261102-autonomy-loop` implementation                                          | 64 sessions over 18 tests: 12 autonomy scenarios at 3–5 runs each, plus `ship`, `implement_verifies` and the 4 `evaluator` variants as regression checks                                                                | **Harness bugs only:** permission prompts, the `section()` parser in `clone.py`, a no-op fixture, the `FAILS_OUTSIDE` regex, a flaky OpenCode test                                           | All reverted (`55025cbc`); e2e put out of scope (`2477b950`). **Net negative.**       |

No other session in the window ran e2e.

## 2. Cost of each test run (Claude Code, measured in the window)

The #616 full pass is the clean baseline: every test on `main` at that time, run once.

| Test (#616 pass, Nov 1)                               |    Tokens | Output |
| ----------------------------------------------------- | --------: | -----: |
| `implement_revises`                                   | 1,723,968 | 19,726 |
| `implement_all`                                       | 1,494,900 | 13,423 |
| `implement_stops_on_rejection`                        | 1,197,911 | 12,295 |
| `implement_on_main`                                   | 1,099,966 |  6,197 |
| `implement_stops_on_escalation`                       | 1,075,235 | 11,135 |
| `ship_all`                                            |   945,413 |  7,165 |
| `ship_reuses_saved_report` (2 sessions)               |   863,047 |  9,002 |
| `verify_fresh_reruns_without_forwarding` (2 sessions) |   740,460 | 10,628 |
| `implement_verifies`                                  |   718,642 |  5,984 |
| `needs_decision_not_reused` (2 sessions)              |   613,103 |  9,239 |
| `ship_approved`                                       |   454,536 |  5,088 |
| `verify_approved`                                     |   355,968 |  5,920 |
| `dirtying_verification_is_not_saved`                  |   312,504 |  5,023 |
| `ship`                                                |   290,085 |  2,637 |
| `verify`                                              |   284,341 |  4,003 |
| `explore`                                             |   256,478 |  2,145 |
| `implement`                                           |   119,978 |  1,328 |
| `verify_refuses_dirty_worktree`                       |   110,729 |    525 |
| `evaluator[narrowed-ESCALATE]`                        |    95,661 |  1,338 |
| `evaluator[restated-REJECT]`                          |    95,550 |  1,380 |
| `implement_stops_on_narrowing`                        |    83,108 |  1,297 |

Tests added since #616 (from the #663 batch):

| Test                                         |     Tokens |
| -------------------------------------------- | ---------: |
| `plan_does_not_implement`                    |    790,672 |
| `implement_relayed_narrowing`, later dropped |  1,268,093 |
| `implement_coordinator_requested`            |    117,580 |
| `implement_requested`                        |    117,330 |
| `evaluator[sharpened-REJECT]`                | about 127K |
| `evaluator[stray-REJECT]`                    |  about 97K |

The two new `evaluator` variants were measured in the `10caffc3` batch.

The autonomy scenarios, now deleted, were the most expensive tests:

| Scenario                   | Tokens per run |
| -------------------------- | -------------- |
| `plan_no_nested_container` | about 1.6M     |
| `plan_matches_code`        | 1.1–1.4M       |
| `plan_names_limit`         | 1.1–1.4M       |
| `implement_files_warning`  | 1.4–1.7M       |

### Cost of one full run

| Suite                                 |                   Tokens | Basis                                                                                                                                                                           |
| ------------------------------------- | -----------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Claude Code, 21 tests at #616         | **12.93M** (135K output) | Measured. Wall time about 8 minutes                                                                                                                                             |
| Claude Code, 26 tests on `main` today |          **about 14.2M** | The #616 pass plus the five tests added since (three new tests and two `evaluator` variants), at their measured cost                                                            |
| OpenCode                              |              **Partial** | 12 of 26 tests measured: **4.61M** (18K output, model `gpt-6.1-sol`). That is about 0.38M per test, roughly 40% of the Claude Code cost per test. A full pass is not measurable |
| Both assistants, today's suite        |         **about 23–24M** | Estimate: the Claude Code figure plus about 26 × 0.38M for OpenCode                                                                                                             |

**All e2e runs in the window:**

- Claude Code: **82.25M tokens** over 127 test sessions.
- OpenCode: **4.61M tokens** measured. This is a lower bound; the rest is not available.

## 3. Cost to develop the tests, plus the runs it took

The development column is the developing session's own turns. The run column is that work's e2e
batch.

| Work                                                                                                                           | Development |                                      Test runs |  Total | Fate           |
| ------------------------------------------------------------------------------------------------------------------------------ | ----------: | ---------------------------------------------: | -----: | -------------- |
| Autonomy-loop scenarios, planning fork (`LrHezB` 01:25–01:43)                                                                  |        6.2M |                              11.4M Claude Code |  17.6M | Discarded      |
| Autonomy-loop scenarios, implementation (`LtSCyz` 07:57–09:32)                                                                 |       30.7M | 45.3M Claude Code, plus OpenCode not available | ≥76.0M | Discarded      |
| `implement_coordinator_requested` and the dropped relayed-narrowing test, including both plan revisions (`LsN5Qx` 06:24–07:34) |       17.7M |               Included in the #663 batch below |        | Kept, narrowed |
| All #663 e2e work: two plans, the Ship fix, and 4 new tests (whole `LsN5Qx` session)                                           |       53.7M |              12.6M Claude Code + 4.6M OpenCode |  70.9M | Kept           |
| #616 acceptance run (`LtSmEM` 07:58–08:16)                                                                                     |        4.0M | 12.9M Claude Code, plus OpenCode not available | ≥16.9M | Nothing found  |

- **Discarded autonomy-loop e2e work:** at least **93.6M tokens**.
- **The one positive loop, the whole #663 session including its runs:** about **71M tokens**.
  Its e2e share cannot be cleanly separated from the skill work.

## 4. Sessions that ran e2e versus sessions that did not

| Group                                                                 |                           Sessions |     Tokens |    Output |   Share |
| --------------------------------------------------------------------- | ---------------------------------: | ---------: | --------: | ------: |
| Ran e2e: the sessions' own turns                                      |                                  4 |     202.7M |      863K |     19% |
| Ran e2e: their test runs (Claude Code 82.3M + measured OpenCode 4.6M) |                                    |      86.9M |      541K |      8% |
| **Ran e2e, total**                                                    |                              **4** | **289.6M** | **1.40M** | **28%** |
| No e2e, agent-dev1, 3 and 4 (session API)                             |                                 21 |     534.2M |     1.83M |     51% |
| No e2e, agent-dev2 (local transcripts, including subagents)           | 10, plus small `self-improve` runs |     215.6M |      850K |     21% |
| **Total**                                                             |                                    | **1,039M** | **4.09M** |         |

- **Average per session:** a session that ran e2e used about **72M tokens** in total. A session
  that did not used about **24M**.
- **Share of the e2e sessions' tokens:** test runs are about 30%; the sessions' own turns are
  the other 70%.
- **The e2e sessions' own turns** include implementation work that is not e2e.

**Biggest sessions with no e2e:**

- 81–120M: Docker GC (`Lr2gKx`). This is shown as a range because its per-turn sum and its
  cumulative counter disagree after compactions.
- 78.8M: manual stacked PRs, agent-dev2.
- 76.8M: re-review (`LpwXk6`).
- 67.2M: re-request bug, agent-dev2.
- 56.6M: pre-commit (`Lt6d1o`).

## 5. Data-quality notes

- **Session-API cross-checks:** for 28 of 31 sessions, the sum of the per-turn usage equals the
  session's cumulative counter exactly. The three that differ:
  - `Lr2gKx`: 81M per-turn versus 120M cumulative.
  - `Lt4Mq8`: 62.8M versus 66.5M.
  - `Lu7TQ4`, the PR #667 fork: 16.5M versus 21.9M.
- **Classification:** `Lu7TQ4` holds the e2e history imported from `LsN5Qx` but ran no e2e of its
  own, so it is counted as not running e2e.
- **E2E figures:** these come straight from the transcript files and are exact, deduplicated by
  message id.
- **Excluded:** this analysis session, and agent-dev2 sessions that started after 09:36 on Nov 3.
