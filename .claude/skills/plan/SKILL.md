---
name: plan
description: Create or revise implementation planning state — discovery in the real codebase first, then a coherent plan with verified code anchors, spec impact, and dependencies. Never edits implementation code. Use when the user says "plan <feature>", "revise the plan", "write a plan for ...", or asks to turn a backlog task or accepted feature into work.
---

# Create or revise a plan

A plan is a promise a future session can execute without re-deriving context.
Discovery happens in the codebase before a word is written; every anchor is
verified, every touched spec is named. Invoking this skill authorizes planning
state changes only. Even when the same request also asks to build the change,
create or revise and validate the plan, report readiness, and stop before
editing implementation code.

## Steps

1. **Consult and select a mode.** Read `data/product.md` — especially `## Constraints` and
   `## Authoring rules`, which bind what you write. Check for related work:
   `iwe find --fuzzy <topic> -f keys`, the relevant `data/spec/` and
   `data/features/` docs, and whether an active plan already covers this
   (`iwe find --included-by data/plans -f keys`). Choose:
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
3. **Discover.** Read the code the plan will touch. Collect the entry points,
   the functions to modify, and their current line numbers — these become
   `## Key references`, and they must come from the current checkout, not
   memory.
4. **Write planning state.** In create mode, run
   `iwe new --key data/plans/<YYYYMMDD>-<slug>` (today's date,
   kebab slug), then write:

   ```yaml
   ---
   created: <today>
   ---
   ```

   Body sections, in order (omit a section only when it's genuinely empty):
   - `## Context` — why now, linking the feature/bug/backlog doc that
     motivates it
   - `## Approach` — the shape of the solution and the alternative you
     rejected, in a few sentences
   - `## Implementation Steps` — `### Task N: <name>` blocks, each with
     `**Files:** Create:/Modify: ...` and `- [ ]` checkboxes. Each checkbox
     carries an indented `- **Evidence:**` child once it is ticked, naming the
     commit, test run, or CI run that closed it; leave the checkbox bare while
     it is unticked. A task may describe an _action_; it may never paraphrase
     _approved content_. When a decision was made as specific text — wording for
     a document, a snippet, a message — reproduce that text verbatim in a fenced
     block under the task that applies it, and check
     `.tmp/approved-wording-<slug>.md` for it before writing the task from
     memory
   - `## Spec changes` — every `data/spec/` doc this work will create or
     change, written in whichever of the three forms below fits the risk;
     name not-yet-existing specs in back-ticks (never dangling links)
   - `## Depends on` — inline links to plans that must ship first (omit if
     none)
   - `## Verification` — how a session proves the work is done: commands,
     tests, manual checks
   - `## Verification results` — narrative evidence for the plan as a whole,
     written as the work happens rather than reconstructed at the end (omit
     until there is something to record). This is the plan's only narrative
     section: results of the `## Verification` checks, and findings that
     change what the plan claims. Not a running account of attempts — see
     `AGENTS.md` Best Practice 8.
   - `## Out of scope` — what this plan deliberately does not do
   - `## Key references` — `path:line — symbol` list under a line
     `Verified anchor points (line numbers as of <today>):`

   In revise mode, apply the requested decision and reconcile every affected
   section in either direction: Context, Approach, Implementation Steps, Spec
   changes, Depends on, Verification, Out of scope, and Key references. For
   example, a task edit may require an Approach or Verification edit, and an
   Approach edit may require new tasks or spec impact. When the decision
   changes behavior, `## Spec changes` moves with it in the same pass — the
   form may need to escalate, and the tasks, verification, and out-of-scope
   boundaries that depend on it are reconciled together. A delta edited alone,
   or left describing the old intent while the tasks around it change, is the
   split this pass exists to prevent. What you are updating is intent: the
   durable spec keeps describing current released behavior until Ship succeeds.
   Re-locate every affected code anchor in the current checkout and refresh its
   date. Identify checked tasks or existing implementation evidence made stale
   by the revision and report them; do not rewrite that implementation from
   this skill.

5. **File a created plan.** In create mode, add an inclusion link under
   `## Active` in `data/plans.md`. If the plan implements a proposed feature,
   set the feature doc to `stage: accepted`. If it grew from a backlog task,
   mark the task done and move its link. In revise mode, preserve the plan's
   existing graph membership and lifecycle unless the requested planning
   change explicitly requires another valid planning-state update.
6. **Check coherence.** Re-read the complete plan as a future implementer.
   Confirm its context, approach, tasks, spec impact, dependencies,
   verification, out-of-scope boundaries, and current code anchors agree with
   one another and with every recorded decision or assumption.
7. **Validate and stop.** Run `iwe normalize`, then `iwe schema validate` —
   both must pass. Report whether the plan was created or revised, any
   assumptions, collisions, and implementation that may now be stale. Stop
   before implementation code changes.

## The three forms of `## Spec changes`

This section is the plan's spec impact in one place: what the affected contract
is _intended_ to say once this work ships. It is not a second durable truth —
the spec documents keep describing current released behavior until Ship merges
the change. Choose the lightest form that leaves a reviewer no room to guess.

1. **No behavioral change** — `None — no behavioral change`. Refactors, tooling,
   and docs-only work stop here. Never invent requirements to fill the section.
2. **Simple, low-risk behavior** — link the affected spec and state a concise
   **normative outcome**: the intended post-change behavior in a sentence or
   two, written with SHALL. That phrase is what the other skills check against
   this form, so keep it recognizable as one. Use it when
   one unambiguous behavior changes and a scenario block would add ceremony
   without resolving anything.
3. **Contract-heavy or risky behavior** — link the affected spec and embed a
   fenced delta. Required when the change touches compatibility, acceptance
   criteria, security/privacy/data-loss behavior, or a requirement's scenario
   set: exactly the cases where a prose summary reads as agreement while hiding
   a disagreement.

The delta goes in a Markdown-tagged fence, so canonical Requirement/Scenario
headings survive inside the plan without turning it into a spec. `iwe normalize`
rewrites the opening fence as ` ``` markdown ` — that spacing is normalized
output, not damage, so leave it alone:

- `## ADDED Requirements` and `## MODIFIED Requirements` carry the **complete
  post-change** requirement — its SHALL statement and _every_ surviving
  scenario, not only the edited ones. A scenario left out of a MODIFIED block
  reads as one this plan deliberately dropped, and Verify treats it that way.
- `## REMOVED Requirements` names the requirement and why the behavior is
  intentionally retired.
- There is no `RENAMED` operation. A rename is an explicit removal plus an
  addition.

A spec that does not exist yet stays a back-ticked key here and in the delta;
Ship creates the document and replaces the key with a real link.

## Rules

- One plan per topic; if the plan needs two unrelated verification stories,
  it's two plans.
- One task is one outcome; if the task could ever be described as half-done,
  split it. A task whose evidence is external — a CI run, a deploy, a review, a
  published artifact — always stands alone, because the session writing the code
  cannot close it. The failure this prevents is a bundled task ticked for the
  half that was done locally, which then reads as a claim about the half that
  was not.
- Code anchors are verified against the current checkout and stamped with the
  date — never cite from memory.
- `## Spec changes` is mandatory thinking, even when its honest content is
  "none — no behavioral change". Picking the form is part of that thinking:
  a contract-heavy change written as a one-line summary is a Verify CRITICAL,
  not a matter of taste.
- Scale ceremony with risk: a small low-risk plan can be short, but never
  skip Verification.
- Planning changes may update project-memory documents and graph membership as
  described above, but never application code or implementation tests.
- **Approved text is copied, never described.** A plan that says what wording
  should accomplish, in place of the wording itself, has lost it: the session
  that applies the plan starts cold, writes something reasonable and different,
  and no one can see what was dropped. The test is whether a session with only
  this plan could reproduce the approved bytes. If the text isn't at hand, stop
  and recover it — from `.tmp/`, from the conversation, from the transcript —
  before writing the task.
