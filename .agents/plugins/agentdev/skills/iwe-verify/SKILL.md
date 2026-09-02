---
name: iwe-verify
description: Verify that implementation matches the graph — check a plan's tasks, spec requirements, and scenarios against the actual code before shipping, or sweep the whole workspace for doc↔code drift.
---

# Verify implementation against the graph

The graph makes claims — tasks checked, requirements SHALL-ed, features marked
implemented. This skill tests those claims against the code and reports what
doesn't hold. It is independently invocable before, during, or after
implementation. It never fixes code or mutates project state: the report is the
deliverable, and the fixes belong to the skills and sessions it points at.

## Steps

1. **Pick the mode.** A plan named or inferable from conversation → plan mode.
   No plan ("audit the docs", "check for drift") → audit mode (step 5).
2. **Select the plan.** If ambiguous, list the plans under `## Active` in
   `data/plans.md` (a just-finished plan may also sit under `## Done`) and ask.
   Announce: "Verifying: <plan>". Read the full plan, every spec named in its
   `## Spec changes`, and the linked feature/bug docs
   (`iwe retrieve -k data/plans/<key>`).
3. **Check three dimensions**, collecting issues as CRITICAL / WARNING /
   SUGGESTION, each with a concrete recommendation:
   - **Completeness** — every unchecked `- [ ]` task is a CRITICAL, with three
     routes out: complete it, tick it if already done, or revise the plan to
     drop it via the `/agentdev:iwe-plan` skill's revise mode, which treats
     dropping a task as
     a material scope change and so asks the user before doing it. The third
     route exists because Ship refuses any CRITICAL and has no override: a task
     the user has decided against can't be ticked while undone, so without it
     the plan is unshippable. Naming a route is not taking it. Mirroring it,
     every ticked `- [x]` task whose indented `- **Evidence:**` line is missing
     or empty, or whose evidence names nothing traceable to a commit, test run,
     or CI run, is also a CRITICAL, recommendation "untick it". Audit the two
     asymmetrically, because they fail asymmetrically: an unchecked box that is
     actually done is a nuisance the next session clears in a minute, while a
     checked box that is not done is a false premise the next session builds
     on. Taking a tick on faith is how the second one survives verification.
     Every entry in `## Spec changes` is judged against the **effective
     contract**: the current durable spec plus the intent the plan records
     against it. Durable specs are not expected to describe the unshipped
     change — Ship merges them after this report — so a back-ticked
     not-yet-created spec is valid here whenever the plan explicitly introduces
     it and supplies its planned contract. Check by the form the plan chose: a
     fenced delta against the durable spec plus every `ADDED` / `MODIFIED` /
     `REMOVED` operation, a concise entry against its normative outcome, and
     `None` by confirming no externally observable behavior changed. Three
     CRITICALs live here — the chosen form is too weak for what the change
     actually touches, the implementation contradicts the recorded intent, or
     the delta would silently drop a scenario this change does not affect.
     Every `### Requirement:` in the effective contract has implementation
     evidence in the codebase — search for it; none found is a CRITICAL.
   - **Correctness** — map each requirement to `path:line` evidence and judge
     whether the implementation matches its SHALL statement (divergence is a
     WARNING with the file and lines to review). For each `#### Scenario:`,
     check the condition is handled in code and covered by a test (uncovered
     scenario is a WARNING). Run the plan's `## Verification` commands and
     report their actual output — a failing command is a CRITICAL.
   - **Coherence** — the implementation follows the plan's `## Approach` (a
     different approach that works is a WARNING: either the code or the plan
     should change); `## Out of scope` items stayed out; the
     `## Authoring rules` in `data/product.md` were honored.
4. **Report and stop.** Issues ranked most severe first, then the verdict:
   **ready to ship** (zero CRITICAL — when Ship invoked this check, return the
   report for Ship's decision) or the blocker list. Do not fix, tick, edit,
   invoke Ship, or perform any shipping state transition. A standalone Verify
   invocation always ends with its report.
5. **Audit mode** — the same discipline over the whole graph, against the
   codebase:
   - Specs whose requirements the code now contradicts (sample the
     highest-traffic specs first: `iwe find --references <key>` counts).
   - Features marked `implemented` with no trace in the code; shipped
     behavior with no feature doc.
   - Open bugs (no `stage`) — still reproducible? Point at ones whose
     `## Key references` no longer exist.
   - Stale map docs: for each `data/codebase/` doc, commits touching its
     `source` after its `commit`
     (`git log --oneline <commit>..HEAD -- <source>`) — flag for the map
     skill's refresh mode.
   - Consistency: plans with `stage: done` still linked under `## Active`
     (`iwe find --filter '{stage: done}' --included-by data/plans -f keys`
     cross-checked against the hub sections); `iwe schema validate`
     violations; `iwe stats` dangling links and `data/` orphans other than
     `data/index`.
   - Report in the same CRITICAL/WARNING/SUGGESTION format, grouped by fix
     owner: "run `/agentdev:iwe-ship` on X", "update spec Y", "close bug Z".

## Rules

- Report, never fix — even a one-character hub-section fix is someone else's
  commit, so the audit trail stays clean.
- Zero CRITICAL findings are the required handoff for normal Ship; Verify
  supplies that verdict but never performs Ship's spec or lifecycle mutations.
- Every claim cites `path:line` evidence or is explicitly labeled
  "unverified" — a requirement you couldn't trace is unverified, not failed,
  and says so.
- Run only the verification commands the plan itself names (tests, builds);
  anything with side effects beyond the working tree needs the user's go-ahead.
- Ship follows a clean verify; a verify with CRITICALs ends with the blocker
  list, not a softened verdict.
