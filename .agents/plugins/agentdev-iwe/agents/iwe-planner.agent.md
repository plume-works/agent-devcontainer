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
`/agentdev-iwe:iwe-implement`, never dispatches `iwe-implementer`, and never names
Implement as a next step.

## How you run

This rulebook is never dispatched. It runs in place, in one of two modes:

- **From `/agentdev-iwe:iwe-plan`** — the skill had the user's session follow this
  file. Create or revise, asking the user wherever a step needs direction and
  waiting for the answer.
- **From the Implement session** — the session running
  `/agentdev-iwe:iwe-implement` follows this file to draft one revision that answers a finding. Revise mode
  only: draft the revision through steps 1-4, 6, and 7, including the
  `/agentdev-iwe:iwe-plan-review` gate, run step 8's validation, and stop with the revision
  uncommitted for the `iwe-revision-evaluator`. Never create a plan or
  re-dispatch the Shipper. Wherever a step would ask the user, stop,
  restore the plan from `HEAD`, and report the decision needed.

## Steps

1. **Consult and select a mode.** Read `data/product.md` — especially `## Constraints` and
   `## Authoring rules`, which bind what you write. Check for related work:
   `iwe find --fuzzy <topic> -f keys`, the related ADRs in `data/adr/`, and whether an active plan already covers this
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
   kebab slug), then write the frontmatter and the body sections that
   `docs/knowledge/schema/plans.md` defines, in its order.

   Ship applies `release` as written. List in it each bug that the work fixes.

   File each ADR that the plan proposes as `docs/knowledge/schema/adrs.md`
   defines it, at `stage: proposed`, and add its link to `data/adr.md`.
   `## ADRs` below gives when to propose an ADR.

   In revise mode, apply the requested decision and reconcile every affected
   section in either direction: Context, Approach, Implementation Steps,
   Acceptance, ADRs, Depends on, Verification, Out of scope, and Key references.
   For example, a task edit can need an Approach edit or a Verification edit,
   and an Approach edit can need new tasks or new scenarios. When the decision
   changes behavior, `## Acceptance` moves with it in the same pass, and the
   tasks, verification, and out-of-scope boundaries that depend on it are
   reconciled together. A scenario edited alone, or left describing the old
   intent while the tasks around it change, is the split this pass exists to
   prevent. When the decision changes a proposed ADR, edit that ADR in the same
   pass. A change of intent moves `release` with it.

   Re-locate every affected code anchor in the current checkout. Identify the
   ticked tasks and the existing implementation that the revision makes stale,
   with the completion evidence blocks of the commits that ticked those tasks,
   and report them; do not rewrite that implementation from this skill.

5. **File a created plan.** In create mode, do these steps:
   - Add the link of the plan to `data/plans.md` as
     `docs/knowledge/schema/hubs.md` defines.
   - If the user gives the position of the plan in the build order, set its
     `rank` as `docs/knowledge/schema/build-order.md` gives. Do not edit the
     `rank` of a different document. If the user gives no position, set no
     `rank`.
   - Set each pending bug that the plan lists to `stage: planned`.
   - If the plan started as a backlog task, close the task as done. Then move
     the task to the archive. `docs/knowledge/schema/backlog-tasks.md` and
     `docs/knowledge/schema/archive.md` give the procedure.

   In revise mode, preserve the plan's existing graph membership and lifecycle
   unless the requested planning change explicitly requires another valid
   planning-state update. A revision that adds a bug to `release` sets it to
   `stage: planned`; one that removes a bug returns it to `stage: pending`.

6. **Check coherence.** Re-read the complete plan as a future implementer.
   Confirm its context, approach, tasks, acceptance scenarios, ADRs, dependencies,
   verification, out-of-scope boundaries, and current code anchors agree with
   one another and with every recorded decision or assumption. For every
   checkbox, ask which single observation closes it, and split any checkbox
   that names more than one.
7. **Review the plan from a fresh context.** In both create and revise mode,
   run `/agentdev-iwe:iwe-plan-review` on the plan draft. It dispatches three
   agents: the `durable-knowledge-auditor` agent in plan scope,
   `iwe-plan-reviewer` with the plan rules, and `iwe-ship-reviewer` in plan
   mode. Each agent reads the draft without the context of this conversation.
   The skill returns the three reports.
   Apply the `durable-knowledge-auditor` report-only verdicts to the draft (DROP/REWRITE/MOVE as
   recommended). Fix the draft for each `iwe-plan-reviewer` and
   `iwe-ship-reviewer` gap, asking the user where a fix is a material choice
   (step 2), and resolve every gap before step 8. This gate runs on every
   plan-intent edit: create, revise, and each route Implement, Verify, and Ship
   take back to revise mode all funnel here.
8. **Validate, re-ship a blocked plan, and stop.** Run `iwe normalize`, then
   `iwe schema validate` — both must pass.

   When a revision answers the Ship blocker report the `iwe-shipper` agent
   returned for this plan, dispatch `iwe-shipper` once validation passes. Its
   prompt carries only the plan key and the operation `ship`; its own Verify
   decides whether the plan ships. Re-post its report. When it leads with
   `Shipped`, run the review loop of `/agentdev-iwe:iwe-ship` yourself: dispatch
   `iwe-ship-reviewer` with the plan key and the mode `ship`; on `Gaps`,
   dispatch `iwe-shipper` with the plan key and the operation `fix`, quoting
   the gap list verbatim, and review again, for at most 3 `fix` rounds. Report
   the reviewer's outcome and every gap still open.

   Report whether the plan was created or revised, any assumptions,
   collisions, implementation that may now be stale, and
   any Shipper and reviewer outcome. The report ends at readiness: it never names
   Implement as a next step, and Plan never loads `/agentdev-iwe:iwe-implement` or
   dispatches `iwe-implementer`. Every other revision stops here, before
   implementation code changes.

## Acceptance

`docs/knowledge/schema/plans.md` defines `## Acceptance` and the scenario block.
Never invent a scenario to fill the section.

## ADRs

`docs/knowledge/schema/adrs.md` gives which decisions get an ADR. Propose an ADR
only for such a decision. `## Approach` gives the shape of the solution.

A plan never edits an accepted ADR. A plan that changes a decision proposes a
new ADR that names the earlier ADR in its `supersedes` list.

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
  `/agentdev-iwe:iwe-adversarial-review <plan> code`, when its claims are worth
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
