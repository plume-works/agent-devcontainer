# Handoff: a more autonomous IWE loop

Exploration in `/agentdev:iwe-explore` (session "agent-dev1 Autonomy rules"), 2026-10-31 to
2026-11-02. Nothing is planned yet. The full pre-cut version is this file at commit
`2f9174b4`.

## Goal and working rules from the user

- Goal: an IWE loop (Plan → Implement → Verify → Ship) that decides more on its own, with
  clear rules for when a human is involved.
- **Only observed problems earn a rule.** Imaginary scenarios bloat scope. Every item below
  cites what happened; anything without evidence was cut (see the end).
- Do not write the goal ("involve a human only when necessary") into a rule verbatim.
  Design concrete rules that approximate it.
- Present proposals in plain, human-readable language. When asking for approval, show the
  text in the message itself — the question dialog hides earlier output.
- Settle open questions one at a time.

## Settled decisions

1. **"CI passes" is not a plan task.** It is an implicit part of development. `pr-merge`
   is the only CI gate. A CI job may still be cited as evidence for behaviour only CI
   exercises; Verify checks that such a check exists, not that it ran on the current head.
2. **Post-merge observations stay plan tasks, and Ship waits for them.** Example:
   ai-review-verdicts Tasks 8-9 ("the next Renovate pull request receives the bot
   approval…"). Inside the Implement loop Verify reports them as outstanding, not
   CRITICAL. Ship requires them ticked, so "done" means seen working live. They carry a
   `**Closed by:** …` line so Verify can tell them apart.
3. **Tests run behaviour.** Committed to `AGENTS.md` `### Tests` (commit `4d41be65`).
   Cross-file consistency tests are out with no replacement: the Renovate pin test only
   checked Renovate did its job, did not prevent a pin race, and broke main and every PR
   that pulled it. Approved wording for the rulebooks, verbatim:

   For the `iwe-planner` rulebook:

   ```text
   A scenario is covered by a test only when the test runs the behaviour: it executes the code, script, hook, or command under test with inputs it controls, owns every resource it uses, and checks what results. These do not cover behaviour: a test that reads a repository file to check its text, keys, steps, or versions, or that two files agree; a test that checks another tool did its job; and a test that queries a live service or waits on CI. Behaviour no such test can reach is an observation task that names who closes it, and Ship waits for it.
   ```

   For the `iwe-verifier` rulebook:

   ```text
   An uncovered scenario is a WARNING only when a test of that kind could cover it; a check of file contents never counts as coverage.
   ```

4. **Verify is a conformance check.** It judges the plan's claims against the code and
   stops hunting for new attack angles.
5. **Adversarial review is a separate agent.** The planner may add it as a closing or
   near-closing task for plans that warrant it. It can also be run on a plan before it is
   finalized — **by hand only**; Plan never invokes it.

## Proposed changes still standing (each observed more than once)

| Change                                                                                                                                      | Evidence (sessions 2026-10-31 to 11-02)                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Label each finding "introduced by this plan" or "already there"; file the second kind instead of working it**                             | off-bash: ported-unchanged `doctor` checks became new Task 21; the integrity bypass existed in the bash manifest too. Baseline: the code (settled)               |
| **Only CRITICALs create work automatically.** A WARNING is fixed only when the fix fits an existing task and adds no promise; else filed    | `iwe-implementer` acts on "every WARNING whose recommendation names a concrete route". okf, remove-codebase-map, macOS, off-bash each gained work from a warning |
| **No promise ratchet.** A revision may add a task toward an outcome already promised, never add or sharpen a claim the code must newly meet | off-bash: a warning rewrote the integrity outcome into sharper promises; the next two Verify rounds attacked them (delete `METADATA`, then `.dist-info`)         |
| **One hunk per finding.** A revision changes only lines that answer a quoted finding                                                        | Evaluator flagged hunks answering no finding: pre-commit (3), kb-conflict-free-layout (1), macOS (1)                                                             |
| **Plan verification commands are scoped to the plan's own files**                                                                           | pre-commit: a repo-wide grep matched the macOS plan's file; remove-codex broke pre-commit's `validate_agent_files` command                                       |

Existing stops stay as they are: always-escalate deviations, Verify `Needs decision`, and
the round bounds.

## Open questions

1. **May the implement-all coordinator start Ship** for a plan it just finished? Observed
   friction: the user typed `/agentdev:iwe-ship` in a worker session. PR #587 (open, plan
   `20261031-model-invocable-implement`) deliberately keeps Ship explicit-only, so this
   reverses its choice.

## Cut for lack of evidence (do not re-propose without a new case)

- **Observed once, resolved cheaply:** an authority order for conflicts inside a plan and
  its supports (no self-authorization, "keep what worked when silent", decision markers,
  a "no rule answers" stop) — from the firewall contradiction alone, fixed by one manual
  plan revise; restriction checks in Verify (same case, Ship caught it); declaring a
  verification command's environment (`doctor` in a bare container); promises stating
  their limits (now covered by the hand-run adversarial agent).
- **Never observed:** pausing the smallest unit and batching questions; a strategy ladder
  with a fresh-Implementer retry; ready-to-answer questions; standing approvals; deriving
  `release`; Ship cleaning its own leftovers; recording every autonomous decision; PR #587
  tensions (answers scattered across workers, a coordinator forging a plan decision); an
  introduced security hole outside every promise; and the open questions on a human gate
  before main, backlog flooding, tier order, old-code evidence, approval storage, marker
  format, paused-question storage, cost as a stop, and unforeseen situations.
- **Redundant after the decisions:** delta-scoped Verify rounds and batching fixes before
  CI — both answered non-convergence that came from CI timing and adversarial probing.

## Evidence trail

- Repeat-round scan: Verify and evaluator reports from session transcripts under
  `/root/.claude/projects/` (9 plans). Causes found: evidence timing (7/9, answered by
  decisions 1-2), warnings becoming work and adversarial drift (6/9, decisions 3-5 and the
  first three changes), parallel plans moving `main` (4/9, scoped commands), revision
  overreach (4/9, one hunk per finding). Scratch extraction was in `.tmp/rc-scan/`, not in
  git.
- PR #629 removed tests that "only restated workflow and action YAML"; the `AGENTS.md`
  rule records that line.
- Leftover tests the `### Tests` rule now covers, not yet removed: the Renovate grouping
  and shared-pin tests in `scripts/tests/test_agent_runtime_ci.py`,
  `scripts/tests/test_macos_bootstrap_pins.py`, and
  `scripts/tests/test_claude_remote_control_start.py` `test_compose_does_not_pass_setup_token`.

## Next steps

1. Settle the open question.
2. Offer capture: hand the settled decisions and standing changes to `/agentdev:iwe-plan`
   (depends on `20261031-model-invocable-implement`), and file the leftover-test removal
   as a task through `/agentdev:iwe-capture`.
