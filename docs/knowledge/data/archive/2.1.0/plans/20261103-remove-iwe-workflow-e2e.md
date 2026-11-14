---
type: plan
created: 2026-11-03
release:
- features/agentdev-iwe-workflow-skills
description: Delete the IWE workflow e2e suite under scripts/e2e/ with its unit tests and pytest marker, drop e2e claims from living project memory, and add a standing rule that plans add no live-model end-to-end test of the workflow skills.
sources:
- resource: scripts/e2e/conftest.py
- resource: scripts/e2e/iwe-workflows/scenarios.py
- resource: pyproject.toml
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
stage: done
completed: 2026-11-03
---

# Remove the IWE workflow e2e suite

## Context

The maintainer decided to remove every e2e test in the repository and to stop
plans from adding new ones. The e2e tests are the IWE workflow suite under
`scripts/e2e/`: pytest scenarios that drive Claude Code and OpenCode sessions
through the agentdev workflow skills against a live model, gated by
`E2E_RUN_LIVE` and the `e2e` marker, plus the unit tests in `scripts/tests/`
that cover the suite's own harness.

Filing this plan also revises the active plans [Let any session asked to ship a
named plan start Ship](../../3.0.0/plans/20261102-model-invocable-ship.md) and
[Add an adversarial review for plans and their
code](20261102-adversarial-review.md): their e2e tasks become observation tasks.
That is planning state, so no task below carries it.

The planner rule changes what [IWE workflow skills in the agentdev
catalog](../../1.0.0/features/agentdev-iwe-workflow-skills.md) ships to template
consumers.

## Approach

Delete the suite and everything that exists only to serve it, then remove the
sentences in living project memory that say the suite exists or runs. Add the
rule to `AGENTS.md` `### Tests` and to the `iwe-planner` rulebook, so behaviour
only a live agent session can show becomes an observation task under the
existing observation-task rule.

Done plans, done backlog tasks, done bug documents, and `data/log.md` stay as
they are: they record what shipped, and the e2e runs were part of that.

Rejected:

- **Keep the suite but stop running it.** Unrun tests rot and still read as
  coverage.
- **Ban every live-model test.** The self-improve plugin's `smoke`, `pty`, and
  `auto_memory` tests also drive live sessions; the maintainer kept them, so the
  rule names the workflow skills only.

## Implementation Steps

### Task 1: Delete the e2e suite and its unit tests

**Files:** Delete: `scripts/e2e/` (all 28 tracked files),
`scripts/tests/test_e2e_iwe_workflows_claude_transcript.py`,
`scripts/tests/test_e2e_iwe_workflows_clone.py`,
`scripts/tests/test_e2e_iwe_workflows_credential.py`,
`scripts/tests/test_e2e_iwe_workflows_opencode_server.py`,
`scripts/tests/test_e2e_iwe_workflows_opencode_transcript.py`,
`scripts/tests/test_e2e_iwe_workflows_report_shown.py`,
`scripts/tests/test_e2e_live_gate.py`; Modify: `pyproject.toml`

- [x] `git ls-files scripts/e2e 'scripts/tests/test_e2e_*'` prints nothing.
  - **Evidence:** commit 920ac34;
    `git ls-files scripts/e2e 'scripts/tests/test_e2e_*'` printed nothing.
- [x] The `e2e` entry is gone from `[tool.pytest.ini_options].markers`; the
  `smoke`, `interactive`, `pty`, `harness`, and `auto_memory` markers stay.
  - **Evidence:** commit 920ac34 removes only the `e2e` line from
    `pyproject.toml`'s `markers`; the other five entries are unchanged.
- [x] `uv run pytest --collect-only -q` collects with no error.
  - **Evidence:** commit 920ac34; `uv run pytest --collect-only -q` collected
    1865 tests with no error.

### Task 2: The standing rule and the OpenCode model rule in AGENTS.md

**Files:** Modify: `AGENTS.md`, `docs/knowledge/data/product.md`

- [x] `AGENTS.md` `### Tests` gains this bullet after "Behaviour no such test
  can reach stays untested.", verbatim:

  ``` markdown
  - NEVER WRITE AN END-TO-END TEST THAT DRIVES AN AGENT SESSION (Claude Code, OpenCode) through the agentdev catalog's workflow skills against a live model. Behaviour only such a session can show is an observation task in its plan.
  ```

  - **Evidence:** commit d289b1e adds the bullet verbatim to `AGENTS.md`
    `### Tests`, after "Behaviour no such test can reach stays untested."

- [x] Best Practice 9 reads "When a test or check runs OpenCode" in place of
  "When a test, e2e harness, or check runs OpenCode".

  - **Evidence:** commit d289b1e; `AGENTS.md` Best Practice 9 now opens "When a
    test or check runs OpenCode".

- [x] `data/product.md` `## Authoring rules` reads "OpenCode tests default to"
  in place of "OpenCode tests and e2e runs default to", and gains a bullet
  restating the new `### Tests` rule.

  - **Evidence:** commit d289b1e; `data/product.md` reads "OpenCode tests
    default to" and carries the restated rule after the Python testing bullet.

### Task 3: The standing rule in the iwe-planner rulebook

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [x] `## Rules` gains this bullet directly after the "A scenario is covered by
  a test only when" bullet, verbatim:

  ``` markdown
  - A plan adds no end-to-end test that drives an agent session through the workflow skills against a live model; behaviour only such a session can show is an observation task naming who closes it, and Ship waits for it.
  ```

  - **Evidence:** commit b6d6fca adds the bullet verbatim to
    `iwe-planner.agent.md` `## Rules`, directly after the "A scenario is covered
    by a test only when" bullet.

- [x] `uv run validate_agent_files --recommend . --require-marketplace claude`
  reports no errors.

  - **Evidence:** commit b6d6fca;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reported 61/61 valid, 0 errors, 0 warnings.

### Task 4: Drop e2e claims from living project memory

**Files:** Modify:
`docs/knowledge/data/features/claude-and-opencode-only-harnesses.md`,
`docs/knowledge/data/archive/2.0.0/architecture/supported-harnesses.md`,
`docs/knowledge/data/someday/revision-evaluator-calibration.md`,
`docs/knowledge/data/archive/2.0.0/architecture/fresh-context-verify.md`,
`docs/knowledge/data/features/verify-report-cache.md`,
`docs/knowledge/data/backlog/incremental-re-verify.md`

- [x] `claude-and-opencode-only-harnesses`: the `description` and `## Purpose`
  list "the images, runtime, agentdev catalog, and CI" with no e2e suites; the
  `scripts/e2e/iwe-workflows/harness_codex.py` source is removed; the Behaviour
  bullet reads "CI requires only the Claude marketplace."
  - **Evidence:** commit 0419bea edits the `description`, `## Purpose`,
    `sources`, and Behaviour bullet as stated.
- [x] `supported-harnesses`: the `description` drops "and e2e suites"; the
  `## Decision` bullet reads "CI validates the catalog with
  `--require-marketplace claude`."
  - **Evidence:** commit 0419bea edits the `description` and the `## Decision`
    bullet as stated.
- [x] `revision-evaluator-calibration`: the `scripts/e2e/...` source is removed,
  and the sentence on the e2e suite reads "No check compares any of its verdicts
  with a human verdict."
  - **Evidence:** commit 0419bea removes the source and replaces the sentence as
    stated.
- [x] `fresh-context-verify`, `verify-report-cache` (`description` and
  `## Purpose`), and `incremental-re-verify` say "test runs" or "full test
  suites" with no "e2e runs".
  - **Evidence:** commit 0419bea; `grep -n -i e2e` over the three documents
    prints nothing.
- [x] Each changed document's `generated` stamp is refreshed.
  - **Evidence:** commit 0419bea sets `generated.at: 2026-11-03T21:00:00Z` on
    all six documents.

## Spec changes

IWE workflow skills — the Plan testing requirement gains the no-e2e rule and a
scenario for it.

``` markdown
## MODIFIED Requirements

### Requirement: Plans test behaviour and leave CI to the merge gate

Plan SHALL write no task or verification step whose only claim is that CI
passes, SHALL record behaviour observable only after merge as a task carrying a
`**Closed by:**` line, SHALL name a test as coverage only when it runs the
behaviour, and SHALL scope a verification search for leftover text to the files
the plan changes. Plan SHALL add no end-to-end test that drives an agent
session through the workflow skills against a live model; behaviour only such a
session can show SHALL be an observation task naming who closes it. Before
validation, Plan SHALL check each requirement it adds or modifies against the
plan's `## Approach` and the code that requirement describes. Every
`## Verification` command SHALL run in the checkout the `iwe-verifier` agent
works in, inside the Dev Container or container the agent already runs in,
without starting a nested Dev Container or CI. A requirement SHALL claim only
what its mechanism delivers and name each limit of that mechanism Plan knows.

#### Scenario: A plan's work needs CI

- **WHEN** Plan writes a plan whose change is checked by CI
- **THEN** the plan carries no "CI passes" task or verification step

#### Scenario: Behaviour is visible only after merge

- **WHEN** a requirement can be observed only once the change is on the default
  branch
- **THEN** Plan writes a task for it carrying a `**Closed by:**` line naming who
  or what closes it

#### Scenario: Behaviour only a live agent session shows

- **WHEN** a requirement can be observed only by driving an agent session
  through the workflow skills against a live model
- **THEN** Plan writes an observation task naming who closes it and adds no
  end-to-end test for it

#### Scenario: A requirement disagrees with the code

- **WHEN** a requirement Plan adds or modifies states a restriction the code it
  describes does not hold, or contradicts the plan's `## Approach`
- **THEN** Plan changes the requirement, the `## Approach`, or adds a task
  before validation, and the plan carries no disagreement

#### Scenario: A check needs a nested Dev Container

- **WHEN** proving the work needs a command that runs only after starting a
  nested Dev Container
- **THEN** `## Verification` does not list the command; the plan cites a CI job
  that runs it or adds a task carrying a `**Closed by:**` line

#### Scenario: A mechanism has a known limit

- **WHEN** Plan writes a requirement for a mechanism with a limit it knows of
- **THEN** the requirement names that limit
```

The rule is a rulebook instruction: nothing mechanically stops a plan or a
session from adding such a test.

## Verification

- `git ls-files scripts/e2e 'scripts/tests/test_e2e_*'` prints nothing.
- `uv run pytest --collect-only -q` collects with no error.
- `grep -n -i 'e2e' pyproject.toml AGENTS.md docs/knowledge/data/product.md .agents/plugins/agentdev/agents/iwe-planner.agent.md docs/knowledge/data/features/claude-and-opencode-only-harnesses.md docs/knowledge/data/archive/2.0.0/architecture/supported-harnesses.md docs/knowledge/data/someday/revision-evaluator-calibration.md docs/knowledge/data/archive/2.0.0/architecture/fresh-context-verify.md docs/knowledge/data/features/verify-report-cache.md docs/knowledge/data/backlog/incremental-re-verify.md`
  prints nothing.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Done plans, done backlog tasks, done bug documents, and `data/log.md`: they
  record shipped work and keep their e2e mentions.
- Open bug documents that cite the deleted suite; keeping their reproductions
  runnable is separate work.
- The self-improve plugin's `smoke`, `pty`, and `auto_memory` live-session
  tests, their markers, and their `Makefile` targets.
- The `'e2e'` strings in `.agents/plugins/agentdev/tests/test_verify_cache.py`:
  arbitrary approval text, not an e2e test.

## Key references

- `scripts/e2e/conftest.py` — the `E2E_RUN_LIVE` gate
- `scripts/tests/test_e2e_live_gate.py::_spec` — loads `scripts/e2e/conftest.py`
- `pyproject.toml › "smoke: drives a real Claude Code session and spends model"`
  — the `e2e` marker
- `AGENTS.md#best-practices-for-agents › "When a test or check runs OpenCode, use"`
  — Best Practice 9
- `AGENTS.md#tests` — `### Tests`
- `docs/knowledge/data/product.md#authoring-rules › "small model); a costlier model only when the user names"`
  — the OpenCode default-model authoring rule
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#rules` — `## Rules`
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#rules › "A scenario is covered by a test only when the test runs the"`
  — "A scenario is covered by a test only when"
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-plans-test-behaviour-and-leave-ci-to-the-merge-gate`
  — Plans test behaviour requirement
- `docs/knowledge/data/features/claude-and-opencode-only-harnesses.md#behaviour › "package keeps its Codex ecosystem"`
  — the e2e Behaviour bullet
- `docs/knowledge/data/archive/2.0.0/architecture/supported-harnesses.md#decision › "CI validates the catalog with"`
  — the CI and e2e bullet
- `docs/knowledge/data/someday/revision-evaluator-calibration.md#calibrate-the-revision-evaluator-against-human-review › "any of its verdicts with a human verdict."`
  — the e2e suite sentence
- `docs/knowledge/data/archive/2.0.0/architecture/fresh-context-verify.md#decision › "repeating its test runs. The lookup and save are a bundled"`
  — "test and e2e runs"
- `docs/knowledge/data/features/verify-report-cache.md#purpose › "commands — full test suites. The"`
  — "full test suites and e2e runs"
- `docs/knowledge/data/backlog/incremental-re-verify.md#re-verify-incrementally-from-a-saved-report › "command — full test suites — even when the fix was a"`
  — "full test suites and e2e runs"
