---
type: plan
created: 2026-10-31
description: Every caller of Verify — the session route, the Implement loop and its coordinator, the Shipper and the ship-all coordinator — shows the Verify report verbatim in the conversation, with numbered findings that a Ship blocker report routes by ID instead of restating.
release:
- features/verify-report-cache
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T15:43:54Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
- resource: scripts/e2e/iwe-workflows/scenarios.py
---

# Show the Verify report in the conversation

## Context

[Verify report cache](../features/verify-report-cache.md) saves each Verify
report to `.tmp/verify/<plan>.md`. Every caller except the session route then
reduces the report before it reaches the user:

- The Implement loop's final report and the `iwe-implement-all` rollup carry
  "each Verify verdict", not the report.
- The Shipper's report carries the CRITICAL count and
  `saved report from <commit>`, and `iwe-ship-all` re-posts only "each Shipper's
  Verify verdict and outcome".
- On a `HIT`, and after a save, the `iwe-verify` skill says "return the report"
  without saying where, so a session can count the report as shown once it has
  appeared in a `Read` result or a save heredoc, and reply with the path.

The findings then live only in a file the user has to open. [Fresh-context
Verify](../architecture/fresh-context-verify.md) makes the report the
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

- [ ] In `## Report`, the **Findings** bullet requires each finding to open with
  its ID — `C<n>` for CRITICAL, `W<n>` for WARNING, `S<n>` for SUGGESTION,
  numbered from 1 per severity in report order — followed by its `path:line`
  evidence or "unverified", and its recommendation. The same applies in audit
  mode.

### Task 2: Make the iwe-verify skill show the report as message text

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md`

- [ ] The lookup table's `HIT` row, the save table's `SUCCESS` row and its
  unsaved rows, session route step 1's `HIT` re-post, and step 5's re-post all
  say that the report body goes verbatim into the final message text. A path to
  the saved report, or the report appearing only in a tool call or tool result,
  does not count as returning it. On the route inside `iwe-shipper`, the
  Shipper's report carries it (Task 3).

### Task 3: Lead the Shipper's report with the Verify report

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`

- [ ] In `## Report`, replace the **Verify verdict** bullet: whenever Verify
  produced a report, the Shipper's report carries it verbatim, after the lead
  line and before the Ship summary, led by `Saved Verify report from <commit>`
  when the skill returned a saved one.
- [ ] The **Ship blocker report** paragraph lists a Verify CRITICAL by its ID
  and route only, without restating its evidence. Each blocker that Ship found
  on its own (intent-versus-implementation mismatch, failed spec merge, missing
  or unresolvable `release` declaration) is written out in full with its
  `path:line` evidence and route. The dirty-worktree blocker is unchanged.

### Task 4: Re-post each Shipper's report in ship-all

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md`

- [ ] Replace "Re-post each Shipper's Verify verdict and outcome here" with a
  verbatim re-post of each Shipper's report, one plan per entry, followed by the
  summary across plans of what shipped, what is blocked, and what needs a
  decision.

### Task 5: Carry the Verify report in the Implement loop's report

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`,
`.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md`

- [ ] `## Running the loop` step 6 (**Report once**): the Finish rollup, then
  the last Verify report verbatim, then each earlier round's verdict with the
  first line of each finding fixed in it, each evaluator verdict with the
  finding it answered, and the reason the run ended.
- [ ] `iwe-implement-all` re-posts each plan's rollup with that plan's final
  Verify report verbatim, each earlier Verify verdict, each evaluator verdict,
  and any decision it stopped for.

### Task 6: Record the behavior in the feature doc

**Files:** Modify: `docs/knowledge/data/features/verify-report-cache.md`

- [ ] Add a `## Behaviour` bullet: every caller shows the Verify report verbatim
  in the conversation, with findings numbered by severity, and the saved file is
  a cache, never the only place the report appears. Restamp `generated` and add
  this plan's sources for the changed files.

### Task 7: Give the e2e harnesses a report-shown check

**Files:** Modify: `scripts/e2e/iwe-workflows/harness_claude.py`,
`scripts/e2e/iwe-workflows/harness_opencode.py`,
`scripts/e2e/iwe-workflows/scenarios.py`

- [ ] `ClaudeTranscript` and the OpenCode `Transcript` each expose the session's
  final message text: the last `result` event's `result` for Claude, and the
  text parts of the last assistant message for OpenCode.
- [ ] `scenarios.py` gains a helper that takes a saved report (the
  `Clone.saved_report` text) and a final message, and holds when the report
  body's lead line and every finding line opening with a `C<n>`, `W<n>`, or
  `S<n>` ID appear in the final message. Lines are compared after stripping
  surrounding whitespace.

### Task 8: Assert the report is shown on Claude Code

**Files:** Modify: `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py`

- [ ] `test_verify_approved`, `test_ship_approved`,
  `test_ship_reuses_saved_report`, `test_ship_all`, `test_implement_verifies`,
  and `test_implement_all` (for each of its plans) assert the Task 7 helper
  against the saved report of each plan the run verified.

### Task 9: Assert the report is shown on OpenCode

**Files:** Modify: `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py`

- [ ] The same six scenarios as Task 8 assert the Task 7 helper.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — add a requirement; no
existing requirement or scenario changes.

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

- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- `uv run pytest .agents/plugins/agentdev/tests`
- `iwe normalize` then `iwe schema validate`, from the repository root
- `E2E_RUN_LIVE=1 uv run pytest -m e2e scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py -k 'verify_approved or ship_approved or saved_report or ship_all or implement_verifies or implement_all'`,
  and the same selection for `test_iwe_workflows_opencode.py`. Each run spends
  model usage, so Verify runs it only under a quoted approval.

## Out of scope

- Codex e2e assertions: [Remove Codex support](20261031-remove-codex.md) retires
  that harness.
- Changing the saved report's location, frontmatter, or cache key.
- [Ship ships a plan whose prerequisite has not
  shipped](../bugs/ship-ignores-unshipped-dependency.md), which ship-all exposes
  within one run.
- Referring to findings across Verify rounds by ID.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md:126` — `## Report`
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md:132` — **Findings**
  bullet
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:32` — lookup `HIT` row
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:66` — save `SUCCESS` row
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:86` — session step 1,
  `HIT` re-post
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:102` — session step 5,
  re-post
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:71` — step 3, Run Verify
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:166` — `## Report`
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:172` — **Verify
  verdict** bullet
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:178` — Ship blocker
  report
- `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md:18` — Shipper re-post
  line
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:180` — step 6,
  Report once
- `.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md:25` — rollup
  re-post line
- `docs/knowledge/data/features/verify-report-cache.md:26` — `## Behaviour`
- `docs/knowledge/data/spec/iwe-workflow-skills.md:420` — Normal shipping
  requires a clean independent verification
- `scripts/e2e/iwe-workflows/harness_claude.py:54` — `ClaudeTranscript.results`
- `scripts/e2e/iwe-workflows/harness_claude.py:93` —
  `ClaudeTranscript.agent_results`
- `scripts/e2e/iwe-workflows/harness_opencode.py:96` —
  `Transcript.assistant_parts`
- `scripts/e2e/iwe-workflows/clone.py:293` — `Clone.saved_report`
- `scripts/e2e/iwe-workflows/scenarios.py:47` — `mentions`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py:56` —
  `test_verify_approved`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py:82` —
  `test_ship_approved`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py:99` —
  `test_ship_reuses_saved_report`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py:165` — `test_ship_all`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py:192` —
  `test_implement_verifies`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py:218` —
  `test_implement_all`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:71` —
  `test_verify_approved`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:97` —
  `test_ship_approved`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:114` —
  `test_ship_reuses_saved_report`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:188` —
  `test_ship_all`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:217` —
  `test_implement_verifies`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:249` —
  `test_implement_all`
