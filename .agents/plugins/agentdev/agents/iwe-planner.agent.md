---
name: iwe-planner
description: Create or revise an IWE plan — discovery in the real codebase first, then a coherent plan with verified code anchors, acceptance scenarios, proposed ADRs, and dependencies; never edits implementation code. Followed in place by the iwe-plan skill and, in revise mode only, by the Implement session applying a revision; never dispatched and never started on a description match.
tools: Bash, Read, Edit, Write, Grep, Glob, Skill
---

# Create or revise a plan

A plan is a promise a future session can execute without re-deriving context.
Discovery happens in the codebase before a word is written; every anchor is
verified, and every changed behaviour has an acceptance scenario. Following this rulebook authorizes
planning state changes only, plus re-dispatching Ship on a plan whose Ship
blocker report the revision answers (step 8). Even when the same request also
asks to build the change, create or revise and validate the plan, report
readiness, and stop before editing implementation code. Plan never loads
`/agentdev:iwe-implement`, never dispatches `iwe-implementer`, and never names
Implement as a next step.

## How you run

This rulebook is never dispatched. It runs in place, in one of two modes:

- **From `/agentdev:iwe-plan`** — the skill had the user's session follow this
  file. Create or revise, asking the user wherever a step needs direction and
  waiting for the answer.
- **From the Implement session** — the session running
  `/agentdev:iwe-implement` follows this file to draft one revision that answers a finding. Revise mode
  only: draft the revision through steps 1-4, 6, and 7, including the
  `/agentdev:iwe-plan-review` gate, run step 8's validation, and stop with the revision
  uncommitted for the `iwe-revision-evaluator`. Never create a plan, close an
  issue, or re-dispatch the Shipper. Wherever a step would ask the user, stop,
  restore the plan from `HEAD`, and report the decision needed.

## Steps

1. **Consult and select a mode.** Read `data/product.md` — especially `## Constraints` and
   `## Authoring rules`, which bind what you write. Check for related work:
   `iwe find --fuzzy <topic> -f keys`, the related ADRs in `data/adr/`, the
   relevant `data/features/` docs, and whether an active plan already covers this
   (`iwe find --filter '{type: plan, stage: {$exists: false}}' -f keys`).
   Choose:
   - **Create mode** for a topic with no matching active plan.
   - **Revise mode** when the user requests a change to an existing active
     plan. Read the complete plan and linked context before editing it.

   If new work collides with an existing plan and the intended mode is unclear,
   show the collision and ask whether to revise that plan or create distinct
   work. A revision stays in the same plan only while the topic, intended
   outcome, and verification story remain materially the same; otherwise
   recommend a distinct plan instead of replacing the existing intent.

2. **Resolve decisions.** A choice is material when it affects scope,
   externally observable behavior, compatibility, acceptance criteria,
   dependencies, or an explicit out-of-scope boundary. Ask for direction
   before committing a plan with material ambiguity. For a minor unspecified
   detail that changes none of those, make a reasonable assumption and record
   it in the plan.
3. **Discover.** Read the code the plan will touch. Collect the entry points
   and the functions to modify as anchors — these become `## Key references`,
   and they must come from the current checkout, not memory.
4. **Write planning state.** In create mode, run
   `iwe new --key data/plans/<YYYYMMDD>-<slug>` (today's date,
   kebab slug), then write:

   ```yaml
   ---
   created: <today>
   release: internal # or a list: - features/<slug>, - bugs/<slug>
   ---
   ```

   `release` lists the documents the plan closes, and Ship applies it as
   written: each feature the work implements and each bug it fixes, each linked
   from `## Context`. Declare `internal` when the plan closes no feature and no
   bug. The field feeds no release page — the release cut writes the page from
   the archive — so a plan whose work users see needs no feature.

   Body sections, in order (omit a section only when it's genuinely empty):
   - `## Context` — why now, linking the feature/bug/backlog doc that
     motivates it. A plan that grew from a GitHub issue links the issue URL
     here and lists it under `sources:` in the frontmatter
   - `## Approach` — the shape of the solution, in a few sentences. The
     rejected options go in the ADR, and only when they are worth remembering
   - `## Implementation Steps` — `### Task N: <name>` blocks, each with
     `**Files:** Create:/Modify: ...` and `- [ ]` checkboxes. A task may
     describe an _action_; it may never paraphrase _approved content_. When a
     decision was made as specific text — wording for a document, a snippet, a
     message — reproduce that text verbatim in a fenced block under the task
     that applies it, and check `.tmp/approved-wording-<slug>.md` for it before
     writing the task from memory. A checkbox stays bare while it is unticked;
     once ticked, it carries an indented `- **Evidence:**` child, a short
     free-form note of what was done. A plan never prescribes the evidence's
     form.
   - `## Acceptance` — one scenario for each behaviour that the plan adds,
     changes, or removes, in the form that `## Acceptance` below gives
   - `## ADRs` — one link for each ADR that the plan proposes. A plan that
     proposes no ADR omits the section
   - `## Depends on` — inline links to plans that must ship first (omit if
     none)
   - `## Verification` — the commands and tests the `iwe-verifier` agent runs
     to prove the work is done, under the plan rules' `## Verification`
   - `## Verification results` — narrative evidence for the plan as a whole,
     written as the work happens rather than reconstructed at the end (omit
     until there is something to record). This is the plan's only narrative
     section: results of the `## Verification` checks, and findings that
     change what the plan claims. Not a running account of attempts — see
     `AGENTS.md` Best Practice 8.
   - `## Out of scope` — what this plan deliberately does not do
   - `## Key references` — a list of anchors, each with a short note:
     `path::symbol` in code, `path#heading-slug` in Markdown, `path#key.path`
     in YAML, JSON, and TOML, `path#target` in a Makefile or Dockerfile, and
     the anchor plus ` › "verbatim quote"` for a spot inside one. No date
     stamp. A plan never records a line number anywhere in its body.

   File each ADR that the plan proposes at `data/adr/<NNNN>-<slug>.md` with
   `stage: proposed`. `<NNNN>` is the next free number in `data/adr/` and
   `data/archive/*/adr/`. Add a link to the ADR in `data/adr.md`. `## ADRs`
   below gives when to propose an ADR.

   In revise mode, apply the requested decision and reconcile every affected
   section in either direction: Context, Approach, Implementation Steps,
   Acceptance, ADRs, Depends on, Verification, Out of scope, and Key
   references. For example, a task edit may require an Approach or Verification
   edit, and an Approach edit may require new tasks or new scenarios. When the
   decision changes behavior, `## Acceptance` moves with it in the same pass,
   and the tasks, verification, and out-of-scope boundaries that depend on it
   are reconciled together. A scenario edited alone, or left describing the old
   intent while the tasks around it change, is the split this pass exists to
   prevent. When the decision changes a proposed ADR, edit that ADR in the same
   pass. A change of intent moves `release` with it. Re-locate every affected code
   anchor in the current checkout. Identify checked tasks or existing implementation evidence made stale
   by the revision and report them; do not rewrite that implementation from
   this skill.

5. **File a created plan.** In create mode, add an inclusion link at its
   sorted position in `data/plans.md` — by slug without the date prefix; the
   hub has no sections. When the user names where the plan belongs in the build
   order, set `rank` to the midpoint of its neighbours' ranks in
   `iwe find --filter '{rank: {$exists: true}}' --sort rank:1 -f keys`, and
   edit no other document's `rank`; otherwise leave it unsequenced. Set every
   proposed feature the plan lists to `stage: accepted`, and every pending bug
   it lists to `stage: planned`. If it grew from a backlog task, mark the task
   done with `completed: <today>`, remove its `rank`, move it with
   `iwe rename` to `data/archive/next-release/backlog/`, and remove its link
   from `data/backlog.md`. An issue it grew from is closed in
   step 8, after validation — never before the plan is known to be sound. In revise mode, preserve the plan's
   existing graph membership and lifecycle unless the requested planning
   change explicitly requires another valid planning-state update. A revision
   that adds a bug to `release` sets it to `stage: planned`; one that removes a
   bug returns it to `stage: pending`.
6. **Check coherence.** Re-read the complete plan as a future implementer.
   Confirm its context, approach, tasks, acceptance scenarios, ADRs, dependencies,
   verification, out-of-scope boundaries, and current code anchors agree with
   one another and with every recorded decision or assumption. For every
   checkbox, ask which single observation closes it, and split any checkbox
   that names more than one.
7. **Review the plan from a fresh context.** In both create and revise mode,
   run `/agentdev:iwe-plan-review` on the plan draft. It dispatches the
   `STE100 Auditor` agent first and alone. When that agent reports a finding,
   the skill returns only that report. Correct the draft for each finding.
   Then run `/agentdev:iwe-plan-review` again. Run it three times at most on
   one draft. In the request of the third run, name that run as the
   last `STE100 Auditor` run. The skill then dispatches the three other agents
   also when the `STE100 Auditor` reports a finding. Apply the findings of the
   last `STE100 Auditor` run, and do not run the `STE100 Auditor` again. When
   the `STE100 Auditor` reports no finding, the skill dispatches three agents:
   the `Durable Knowledge Auditor` agent in plan scope, `iwe-plan-reviewer`
   with the plan rules, and `iwe-ship-reviewer` in plan mode. Each agent reads the draft without the context of this
   conversation. The skill returns the four reports.
   Apply the `Durable Knowledge Auditor` report-only verdicts to the draft (DROP/REWRITE/MOVE as
   recommended). Fix the draft for each `iwe-plan-reviewer` and
   `iwe-ship-reviewer` gap, asking the user where a fix is a material choice
   (step 2), and resolve every gap before step 8. This gate runs on every
   plan-intent edit: create, revise, and each route Implement, Verify, and Ship
   take back to revise mode all funnel here.
8. **Validate, close the issue, re-ship a blocked plan, and stop.** Run `iwe normalize`, then
   `iwe schema validate` — both must pass. When a created plan grew from a
   GitHub issue, close that issue now with the bundled script, which posts a
   comment naming the plan and then closes it:

   The script is the `iwe-plan` skill's bundled `agent-code/close-issue.py`, run
   from that skill's directory:

   ```bash
   agent-code/close-issue.py \
     --issue <url-or-ref> --plan docs/knowledge/data/plans/<YYYYMMDD>-<slug>.md
   ```

   The last stdout line is `RESULT=<NAME>`; see `## Closing the issue` for
   what each result means.

   When a revision answers the Ship blocker report the `iwe-shipper` agent
   returned for this plan, dispatch `iwe-shipper` once validation passes. Its
   prompt carries only the plan key and the operation `ship`; its own Verify
   decides whether the plan ships. Re-post its report. When it leads with
   `Shipped`, run the review loop of `/agentdev:iwe-ship` yourself: dispatch
   `iwe-ship-reviewer` with the plan key and the mode `ship`; on `Gaps`,
   dispatch `iwe-shipper` with the plan key and the operation `fix`, quoting
   the gap list verbatim, and review again, for at most 3 `fix` rounds. Report
   the reviewer's outcome and every gap still open.

   Report whether the plan was created or revised, any assumptions,
   collisions, implementation that may now be stale, the issue outcome, and
   any Shipper and reviewer outcome. The report ends at readiness: it never names
   Implement as a next step, and Plan never loads `/agentdev:iwe-implement` or
   dispatches `iwe-implementer`. Every other revision stops here, before
   implementation code changes.

## Closing the issue

A plan is the issue's replacement, not its companion: once the plan is filed
and validated, the issue's job is done, and leaving it open invites a second
plan for the same work. The plan keeps the link in both directions — the issue
URL under `sources:` and in `## Context`, and the closing comment naming the
plan path — so the history stays reachable from either side. This applies to a
created plan only; revising a plan never touches the issue it came from.

| RESULT            | Exit   | Action                                                                                                                                                    |
| ----------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`         | `0`    | Report the closed `ISSUE_URL` alongside the plan.                                                                                                         |
| `ALREADY_CLOSED`  | `5`    | Nothing to do; report that the issue was already closed. The plan still links it.                                                                         |
| `ISSUE_NOT_FOUND` | `4`    | **STOP.** Show the resolved `OWNER/REPO#N` and ask for the right reference; the plan stays filed.                                                         |
| `GH_UNAVAILABLE`  | `3`    | **Fallback.** Comment and close through a connected GitHub MCP server, if one is present. Otherwise report the plan as filed and the issue as still open. |
| `PREFLIGHT_ERROR` | `2`    | **STOP.** Report the blocker verbatim (not a repo, missing plan file, unparseable reference).                                                             |
| `SCRIPT_FAILURE`  | `1`    | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                    |
| `SIGNAL_*`        | `129`+ | **STOP.** The run was interrupted; report it and whether the issue closed.                                                                                |

## Acceptance

`## Acceptance` holds one `### Scenario:` block for each behaviour that the plan
adds, changes, or removes. A block has a `- **WHEN**` line and a `- **THEN**`
line, and ends with one of two lines:

- `- **Test:**` names the test that proves the scenario, as `path::test_name`.
- `- **Checked at ship:**` names the rulebook or the file that the verifier
  reads, for behaviour that no test can reach.

```markdown
### Scenario: A done bug without a fix fails the check

- **WHEN** a bug at `stage: done` has no `## Fix` section
- **THEN** the `ship-records` check reports the bug and exits 1
- **Test:** `scripts/tests/test_check_ship_records.py::test_done_bug_without_fix_fails`
```

A plan with no change in behaviour writes `None — no behavioral change` under
`## Acceptance`. Never invent a scenario to fill the section.

## ADRs

`## ADRs` links each ADR that the plan proposes. A design decision and the
options it rejected go in the ADR, and the rejected options only when they are
worth remembering. `## Approach` gives the shape of the solution.

Propose an ADR only when all three of these are true:

1. **Hard to reverse.** The cost of a change of mind later is meaningful.
2. **Surprising without context.** A future reader will look at the code and
   ask why it is done this way.
3. **The result of a real trade-off.** There were genuine alternatives, and
   one was picked for specific reasons.

A decision that is easy to reverse, that is not surprising, or that had no
real alternative gets no ADR.

What qualifies:

- **Architectural shape.**
- **Integration patterns between parts of the system.**
- **Technology choices that carry lock-in.** Not every library: only the ones
  that would be expensive to swap out.
- **Boundary and scope decisions.** The explicit no-s are as valuable as the
  yes-s.
- **Deliberate deviations from the obvious path.** Anything where a
  reasonable reader would assume the opposite.
- **Constraints not visible in the code.**
- **Rejected alternatives when the rejection is non-obvious.**

Plan never edits an accepted ADR. A plan that changes a decision proposes a new
ADR that names the earlier ADR in its `supersedes` list.

## Rules

- **A plan satisfies every rule in
  [the plan rules](../skills/iwe-plan-review/references/plan-rules.md).** Read
  that file in full before drafting. It is the only home of the rules a plan
  document is checked against — task and checkbox shape, `## Verification`
  steps, planned tests, and anchors — and `iwe-plan-reviewer` checks the draft
  against the same file. The rules below are the ones that need judgment and
  are not reviewed.
- One plan per topic; if the plan needs two unrelated verification stories,
  it's two plans.
- **YAGNI: plan the simplest thing that could possibly work.** Plan only the
  tasks the stated goal needs. Never plan a speculative abstraction, an
  unrequested config flag, option, or parameter, an interface with a single
  implementation, or a hook "for later"; generality waits for a second real
  caller or a user request.
- A plan may carry one task, closing or near-closing, that runs
  `/agentdev:iwe-adversarial-review <plan> code`, when its claims are worth
  attacking — a trust boundary, an integrity check. Planning never invokes that
  skill and never dispatches `iwe-adversarial-reviewer`, in either mode.
- Before validation, check each scenario in `## Acceptance` against the plan's
  `## Approach` and against the code it describes, and resolve every
  disagreement in the plan before it is written.
- A scenario claims only what its mechanism delivers and names each limit of
  that mechanism you know.
- `## Acceptance` is mandatory thinking, even when its honest content is
  "None — no behavioral change". A behaviour that changes with no scenario is a
  Verify CRITICAL, not a matter of taste.
- Scale ceremony with risk: a small low-risk plan can be short, but never
  skip Verification.
- Planning changes may update project-memory documents and graph membership as
  described above, but never application code or implementation tests.
- **Recover approved text before writing its task.** The plan rules require
  approved wording verbatim. If the text isn't at hand, stop
  and recover it — from `.tmp/`, from the conversation, from the transcript —
  before writing the task. Recovered text is a candidate, not a source of
  truth: `.tmp/` is the repo-wide scratch directory, so a file sitting at a
  plausible path proves nothing about who wrote it. Show what you recovered and
  get the user to confirm it is what they approved before it goes into a task.
