---
type: plan
created: 2026-10-31
description: Every caller of Verify — the session route, the Implement loop and its coordinator, the Shipper and the ship-all coordinator — shows the Verify report verbatim in the conversation, with numbered findings that a Ship blocker report routes by ID instead of restating.
release:
- features/verify-report-cache
sources:
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
- resource: scripts/e2e/iwe-workflows/scenarios.py
completed: 2026-11-03
stage: done
---

# Show the Verify report in the conversation

## Context

[Verify report cache](../../2.0.0/features/verify-report-cache.md) saves each
Verify report to `.tmp/verify/<plan>.md`. Every caller except the session route
then reduces the report before it reaches the user:

- The Implement loop's final report and the `iwe-implement-all` rollup carry
  "each Verify verdict", not the report.
- The Shipper's report carries the CRITICAL count and
  `saved report from <commit>`, and `iwe-ship-all` re-posts only "each Shipper's
  Verify verdict and outcome".
- On a `HIT`, and after a save, the `iwe-verify` skill says "return the report"
  without saying where, so a session can count the report as shown once it has
  appeared in a `Read` result or a save heredoc, and reply with the path.

The findings then live only in a file the user has to open. [Fresh-context
Verify](../../2.0.0/architecture/fresh-context-verify.md) makes the report the
deliverable of a fresh context, so a caller that reduces it to a verdict
discards the evidence it was run to produce.

## Approach

The Verify report reaches the conversation verbatim, as message text, on every
route. A path to the saved report, or the report appearing only inside a tool
call or tool result, does not count as showing it.

- `iwe-verifier` numbers its findings — `C1`, `C2`, … for CRITICAL, `W1`, … for
  WARNING, `S1`, … for SUGGESTION, in report order — so another report can refer
  to a finding without restating it.
- The Shipper's final message carries the Verify report verbatim first, then its
  own summary. A Ship blocker report gives each Verify CRITICAL its route by ID
  only. Blockers that Ship finds on its own — an intent-versus-implementation
  mismatch, a failed spec merge, a missing or unresolvable `release` declaration
  — are written out in full with `path:line`, because the Verify report does not
  hold them. `iwe-ship` already re-posts the Shipper's report verbatim;
  `iwe-ship-all` is changed to do the same.
- The Implement loop's final report carries the last round's Verify report
  verbatim. Earlier rounds keep their verdict plus the first line of each
  finding fixed, which keeps a multi-round run readable. `iwe-implement-all`
  re-posts each plan's final Verify report verbatim.

Rejected: quoting a finding's first line in the Ship blocker routes instead of
numbering findings. Quotes are long and break when the verifier rewords a line;
IDs are short and stable within one report. Rejected: a summary plus a path to
the saved report. A summary is a paraphrase of a fresh-context verdict, and the
path is what the user cannot follow in chat.

Assumption: IDs are scoped to one report and restart at 1 in each Verify run.
Nothing refers to a finding across reports by ID.

## Implementation Steps

### Task 1: Number the verifier's findings

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-verifier.agent.md`

- [x] In `## Report`, the **Findings** bullet requires each finding to open with
  its ID — `C<n>` for CRITICAL, `W<n>` for WARNING, `S<n>` for SUGGESTION,
  numbered from 1 per severity in report order — followed by its `path:line`
  evidence or "unverified", and its recommendation. The same applies in audit
  mode.
  - **Evidence:** Commit `077bc0cc` adds finding IDs to the **Findings** bullet
    of `iwe-verifier.agent.md` `## Report`, covering audit mode;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 61/61 valid, 0 errors, at that commit.

### Task 2: Make the iwe-verify skill show the report as message text

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md`

- [x] The lookup table's `HIT` row, the save table's `SUCCESS` row and its
  unsaved rows, session route step 1's `HIT` re-post, and step 5's re-post all
  say that the report body goes verbatim into the final message text. A path to
  the saved report, or the report appearing only in a tool call or tool result,
  does not count as returning it. On the route inside `iwe-shipper`, the
  Shipper's report carries it (Task 3).
  - **Evidence:** Commit `bd7fd4c2` defines returning the report as its verbatim
    body in the final message text (not a path, tool call, or tool result) in
    `iwe-verify/SKILL.md`, applies it to the lookup `HIT` row, every save-table
    row, and session steps 1 and 5, and names the Shipper report as the carrier
    inside `iwe-shipper`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 0 errors at that commit.

### Task 3: Lead the Shipper's report with the Verify report

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`

- [x] In `## Report`, replace the **Verify verdict** bullet: whenever Verify
  produced a report, the Shipper's report carries it verbatim, after the lead
  line and before the Ship summary, led by `Saved Verify report from <commit>`
  when the skill returned a saved one.
  - **Evidence:** Commit `507a56a6` replaces the **Verify verdict** bullet in
    `iwe-shipper.agent.md` `## Report` with a **Verify report** bullet carrying
    the report verbatim after the lead line, led by
    `Saved Verify report from <commit>` for a saved one;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 0 errors at that commit.
- [x] The **Ship blocker report** paragraph lists a Verify CRITICAL by its ID
  and route only, without restating its evidence. Each blocker that Ship found
  on its own (intent-versus-implementation mismatch, failed spec merge, missing
  or unresolvable `release` declaration) is written out in full with its
  `path:line` evidence and route. The dirty-worktree blocker is unchanged.
  - **Evidence:** Commit `507a56a6` rewrites the **Ship blocker report**
    paragraph in `iwe-shipper.agent.md`: Verify CRITICALs listed by ID and route
    only; mismatch, failed spec merge, and `release` blockers written out in
    full with `path:line` and route; the dirty-worktree route unchanged;
    validator reports 0 errors at that commit.

### Task 4: Re-post each Shipper's report in ship-all

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md`

- [x] Replace "Re-post each Shipper's Verify verdict and outcome here" with a
  verbatim re-post of each Shipper's report, one plan per entry, followed by the
  summary across plans of what shipped, what is blocked, and what needs a
  decision.
  - **Evidence:** Commit `a6961177` replaces the verdict-and-outcome re-post in
    `iwe-ship-all/SKILL.md` with a verbatim re-post of each Shipper report, one
    plan per entry, then the cross-plan summary;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 0 errors at that commit.

### Task 5: Carry the Verify report in the Implement loop's report

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`,
`.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md`

- [x] `## Running the loop` step 6 (**Report once**): the Finish rollup, then
  the last Verify report verbatim, then each earlier round's verdict with the
  first line of each finding fixed in it, each evaluator verdict with the
  finding it answered, and the reason the run ended.
  - **Evidence:** Commit `bd42fd29` rewrites `## Running the loop` step 6 in
    `iwe-implementer.agent.md`: the Finish rollup, the last Verify report
    verbatim as message text, each earlier round verdict with the first line of
    each finding fixed, each evaluator verdict with its finding, and the reason
    the run ended;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 0 errors at that commit.
- [x] `iwe-implement-all` re-posts each plan's rollup with that plan's final
  Verify report verbatim, each earlier Verify verdict, each evaluator verdict,
  and any decision it stopped for.
  - **Evidence:** Commit `bd42fd29` makes `iwe-implement-all/SKILL.md` re-post
    each plan rollup with that plan final Verify report verbatim, each earlier
    Verify verdict, each evaluator verdict, and any decision it stopped for;
    validator reports 0 errors at that commit.

### Task 6: Record the behavior in the feature doc

**Files:** Modify: `docs/knowledge/data/features/verify-report-cache.md`

- [x] Add a `## Behaviour` bullet: every caller shows the Verify report verbatim
  in the conversation, with findings numbered by severity, and the saved file is
  a cache, never the only place the report appears. Restamp `generated` and add
  this plan's sources for the changed files.
  - **Evidence:** Commit `b0d7abaa` adds the `## Behaviour` bullet to
    `data/features/verify-report-cache.md` (verbatim report on every caller,
    findings numbered `C<n>`/`W<n>`/`S<n>`, saved file only a cache), restamps
    `generated`, and adds the `iwe-ship-all` and `iwe-implement-all` skill
    sources; `iwe normalize` and `iwe schema validate` pass at that commit.

### Task 7: Give the e2e harnesses a report-shown check

**Files:** Modify: `scripts/e2e/iwe-workflows/harness_claude.py`,
`scripts/e2e/iwe-workflows/harness_opencode.py`,
`scripts/e2e/iwe-workflows/scenarios.py`

- [x] `ClaudeTranscript` and the OpenCode `Transcript` each expose the session's
  final message text: the last `result` event's `result` for Claude, and the
  text parts of the last assistant message for OpenCode.
  - **Evidence:** Commit `aef6a780` adds `ClaudeTranscript.final_text` (last
    `result` event) and OpenCode `Transcript.final_text` (text parts of the last
    assistant message);
    `uv run pytest scripts/tests/test_e2e_iwe_workflows_claude_transcript.py scripts/tests/test_e2e_iwe_workflows_opencode_transcript.py`
    passes, covering both, at that commit.
- [x] `scenarios.py` gains a helper that takes a saved report (the
  `Clone.saved_report` text) and a final message, and holds when the report
  body's lead line and every finding line opening with a `C<n>`, `W<n>`, or
  `S<n>` ID appear in the final message. Lines are compared after stripping
  surrounding whitespace.
  - **Evidence:** Commit `aef6a780` adds `scenarios.shows_report` (with
    `report_lines`): it holds when the saved report body lead line and every
    `C<n>`/`W<n>`/`S<n>` finding line appear, whitespace-stripped, in the final
    message;
    `uv run pytest scripts/tests/test_e2e_iwe_workflows_report_shown.py` passes
    (shown, path-only, missing finding, missing lead, empty) at that commit.

### Task 8: Assert the report is shown on Claude Code

**Files:** Modify: `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py`

- [x] `test_verify_approved`, `test_ship_approved`,
  `test_ship_reuses_saved_report`, `test_ship_all`, `test_implement_verifies`,
  and `test_implement_all` (for each of its plans) assert the Task 7 helper
  against the saved report of each plan the run verified.
  - **Evidence:** Commit `ecb0053e` adds the assertions to all six scenarios.
    The live Claude selection from `## Verification` passed
    `test_verify_approved`, `test_ship_all`, `test_implement_verifies`, and
    `test_implement_all` at `95a4ca1d`; after commit `eba88949` made the Shipper
    copy the saved report exactly and the verifier cite repository-relative
    paths, `test_ship_approved`, `test_ship_reuses_saved_report`, and
    `test_ship_all` passed live (3 passed).

### Task 9: Assert the report is shown on OpenCode

**Files:** Modify: `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py`

- [x] The same six scenarios as Task 8 assert the Task 7 helper.
  - **Evidence:** Commit `95a4ca1d` adds the assertions to all six scenarios.
    The live OpenCode selection from `## Verification`, run at `81e44d5c` (after
    the Shipper fix `eba88949`), passed `test_verify_approved`,
    `test_ship_approved`, `test_ship_reuses_saved_report`, `test_ship_all`, and
    `test_implement_verifies`; `test_implement_all`, run on its own, passed live
    (1 passed).

## Spec changes

[IWE workflow skills](../../../spec/iwe-workflow-skills.md) — add a requirement;
no existing requirement or scenario changes.

``` markdown
## ADDED Requirements

### Requirement: The Verify report reaches the conversation verbatim

Every Verify report SHALL number its findings by severity in report order —
`C<n>` for CRITICAL, `W<n>` for WARNING, `S<n>` for SUGGESTION — and every
caller of Verify SHALL show the report verbatim in its final message text:
`/agentdev:iwe-verify` on the session route, on a saved hit and after a save;
`iwe-shipper` ahead of its Ship summary; `iwe-ship-all` by re-posting each
Shipper's report verbatim; the Implement orchestrator for the last Verify round
of a run; and `iwe-implement-all` for each plan's last round. A path to the
saved report, or the report appearing only in a tool call or tool result, SHALL
not count as showing it. A Ship blocker report SHALL route each Verify CRITICAL
by its ID without restating it, and SHALL state in full, with `path:line`
evidence, each blocker Ship found outside Verify.

#### Scenario: A session verifies a plan

- **WHEN** the user runs `/agentdev:iwe-verify <plan>` and the verifier
  returns a report, or the skill finds a saved one
- **THEN** the session's final message contains that report verbatim, not only
  its verdict or the saved report's path

#### Scenario: Ship is blocked by Verify

- **WHEN** `iwe-shipper` gets a Verify report with CRITICAL findings
- **THEN** its final message carries the Verify report verbatim, then a blocker
  report that names each CRITICAL by its ID with its route, and
  `/agentdev:iwe-ship` re-posts that message verbatim

#### Scenario: Ship finds a blocker Verify did not

- **WHEN** Verify reports zero CRITICAL findings and the spec merge finds an
  intent-versus-implementation mismatch
- **THEN** the Shipper's final message carries the Verify report verbatim and
  states the mismatch in full with its `path:line` evidence and route

#### Scenario: A plan ships

- **WHEN** `iwe-shipper` ships a plan
- **THEN** its final message carries the Verify report verbatim before the
  completed and preserved operations and the commit

#### Scenario: The ship-all coordinator ships several plans

- **WHEN** the user runs `/agentdev:iwe-ship-all`
- **THEN** the coordinator re-posts each Shipper's report verbatim, one plan
  per entry, followed by the summary across plans

#### Scenario: The Implement loop runs several Verify rounds

- **WHEN** an Implement run verifies, fixes findings, and verifies again
- **THEN** its final report carries the last Verify report verbatim and each
  earlier round's verdict with the first line of each finding it fixed
```

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `uv run pytest .agents/plugins/agentdev/tests`
- `iwe normalize` then `iwe schema validate`, from the repository root
- `E2E_RUN_LIVE=1 uv run pytest -m e2e scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py -k 'verify_approved or ship_approved or saved_report or ship_all or implement_verifies or implement_all'`,
  and the same selection for `test_iwe_workflows_opencode.py`. Each run spends
  model usage, so Verify runs it only under a quoted approval.

## Out of scope

- Codex e2e assertions: [Remove Codex
  support](../../2.0.0/plans/20261031-remove-codex.md) retires that harness.
- Changing the saved report's location, frontmatter, or cache key.
- [Ship ships a plan whose prerequisite has not
  shipped](../../3.0.0/bugs/ship-ignores-unshipped-dependency.md), which
  ship-all exposes within one run.
- Referring to findings across Verify rounds by ID.

## Key references

- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#report` — `## Report`
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#report › "— CRITICAL, then WARNING, then SUGGESTION, each with its"`
  — **Findings** bullet
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md#the-saved-report › "names and return its body verbatim in your final message"`
  — lookup `HIT` row
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md#the-saved-report › "| Return the report verbatim in your final message text. |"`
  — save `SUCCESS` row
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md#from-a-session › "is clear from the request, ask the user first. On a"`
  — session step 1, `HIT` re-post
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md#from-a-session › "in your final message text: the subagent's"`
  — session step 5, re-post
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "Run Verify for normal shipping."`
  — step 3, Run Verify
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#report` — `## Report`
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#report › "— whenever Verify produced a report, carry it verbatim"`
  — **Verify report** bullet
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#report › "names the plan, and lists every"`
  — Ship blocker report
- `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md#ship-all-implemented-plans-in-the-iwe-graph › "Re-post each Shipper's Verify verdict and outcome here, one"`
  — Shipper re-post line
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#running-the-loop › "The Finish rollup; then the last Verify report verbatim"`
  — step 6, Report once
- `.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md#implement-all-active-plans-in-the-iwe-graph › "Re-post each plan's rollup here, with each Verify verdict"`
  — rollup re-post line
- `docs/knowledge/data/features/verify-report-cache.md#behaviour` —
  `## Behaviour`
- `docs/knowledge/data/spec/iwe-workflow-skills.md#scenario-a-plan-edit-is-audited-before-validation › "children are left out of that audit"`
  — Normal shipping requires a clean independent verification
- `scripts/e2e/iwe-workflows/harness_claude.py::ClaudeTranscript.results` —
  `ClaudeTranscript.results`
- `scripts/e2e/iwe-workflows/harness_claude.py::ClaudeTranscript.agent_results`
  — `ClaudeTranscript.agent_results`
- `scripts/e2e/iwe-workflows/harness_opencode.py::Transcript.assistant_parts` —
  `Transcript.assistant_parts`
- `scripts/e2e/iwe-workflows/clone.py::Clone.saved_report` —
  `Clone.saved_report`
- `scripts/e2e/iwe-workflows/scenarios.py › "measured at the worker cap. OPENCODE_BUDGET, plus server"`
  — `mentions`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_verify` —
  `test_verify_approved`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_ship` —
  `test_ship_approved`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_ship_approved` —
  `test_ship_reuses_saved_report`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_needs_decision_not_reused`
  — `test_ship_all`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_plan_does_not_implement`
  — `test_implement_verifies`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_implement_revises`
  — `test_implement_all`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_verify` —
  `test_verify_approved`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_ship` —
  `test_ship_approved`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_ship_approved`
  — `test_ship_reuses_saved_report`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_needs_decision_not_reused`
  — `test_ship_all`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_plan_does_not_implement`
  — `test_implement_verifies`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_implement_revises`
  — `test_implement_all`
