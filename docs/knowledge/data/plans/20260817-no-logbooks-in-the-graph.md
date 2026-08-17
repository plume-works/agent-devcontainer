---
type: plan
created: 2026-08-17
description: Stop implementation sessions from growing plans into troubleshooting logbooks by scoping the one clause that invites narration, giving Implement a capture-and-route section, and stating the settled-versus-path rule once in the operating manual.
generated:
  by: claude-code/opus-5
  at: 2026-08-17T00:00:00Z
sources:
- .claude/skills/plan/SKILL.md
- .claude/skills/implement/SKILL.md
- .claude/skills/explore/SKILL.md
- docs/knowledge/AGENTS.md
- docs/knowledge/data/product.md
- docs/knowledge/data/spec/iwe-workflow-skills.md
- docs/knowledge/data/spec/plan-checkbox-evidence.md
---

# Keep working logbooks out of the knowledge graph

## Context

An implementation session grew
[AI responder workflows](20260816-ai-responder-workflows.md) from 299 to 558
lines, and almost none of the growth was plan content. It was narration of the
work in progress: six references to CI run IDs, an eleven-variable table, an
ablation matrix, a two-failed-runs story, phrases like "died one script later".
The maintainer caught it and the plan was cut back to 471 lines with its
evidence intact, but the same failure has occurred on other tasks, so the
wording — not that one session — is what needs to change.

The checkbox discipline held perfectly. All 27 ticks carried evidence lines,
one-to-one, and survived the cleanup untouched. Every rule
`.claude/skills/implement/SKILL.md:73-89` states is about checkboxes, evidence,
commits, and deviations; the damage landed entirely in `## Context`,
`## Approach`, and task rationale prose, which no rule in either skill governs.

One clause actively invites it. `.claude/skills/plan/SKILL.md:69-71` defines
`## Verification results` as "narrative evidence for the plan as a whole,
written as the work happens rather than reconstructed at the end", and
[Plan checkbox evidence](../spec/plan-checkbox-evidence.md) reinforces it with a
scenario covering results "or discovers something that changes what the plan
claims". Both are correct and deliberately scoped. But read mid-implementation
they land as a general licence to write narrative into the plan as things
happen, and because neither says *which section*, it bleeds into the ungoverned
ones.

The pressure behind it is structural rather than careless. Implementation
produces findings that are true and expensive — that `UV_PROJECT_ENVIRONMENT`
unset makes `uv sync` silently write `.venv` into the checkout under review took
a purpose-built ablation harness to find. The plan is the document already open,
so writing it there feels like preserving hard-won knowledge, and each addition
is individually defensible. The failure is only visible in aggregate, which is
exactly the shape per-edit rules cannot catch.

A routing rule already exists in [Product](../product.md) `## Authoring rules` —
spike findings go to `data/bugs/`, design decisions to `data/architecture/` —
and it is why the cleanup went smoothly once triggered: the minimal-contract
table moved to
[CI agent plugin availability](../architecture/ci-agent-plugin-availability.md)
and fit as though written for it. But `implement` never cites that rule, and
`explore` has a whole `## Capturing` section
(`.claude/skills/explore/SKILL.md:47`) that `implement` lacks. The skill that
generates the most findings has the least guidance on where they belong.

## Approach

Three coordinated edits, each aimed at a different half of the gap. All three
were drafted and approved as finished text before this plan existed, so Tasks
1-3 carry that wording verbatim in fenced blocks rather than describing it.
Approved wording is a deliverable, not an instruction to produce one: a
paraphrase silently drops the specifics — which document owns a finding before a
new one is created, the exact bug-document shape — and a future session applying
a description would write something reasonable and different.

**Scope the clause that leaks.** `## Verification results` keeps its purpose and
gains a boundary: it is the plan's only narrative section, it holds results of
the `## Verification` checks and findings that change what the plan claims, and
it is not a running account of attempts.

**Give Implement somewhere to put findings.** A `## Capturing` section mirroring
Explore's, inverting its handoff: Explore hands a plan-owned finding back to the
plan; Implement routes a plan-external finding out to `data/architecture/`,
`data/bugs/`, or `data/backlog/`, with material boundary changes still going
through the existing Step 6. It also states that `## Context` and `## Approach`
are the plan skill's to own and stay stable during implementation.

**State the prohibition once, where it binds everything.** In
`docs/knowledge/AGENTS.md` rather than in each skill, because the failure has
appeared outside `implement` and three copies would drift.

The prohibition is deliberately *not* "no troubleshooting content in the graph".
That would be false against the graph's own design — `data/bugs/` requires
Reproduction and Root cause, and `data/log.md` is chronological narrative by
construction — and a rule that reads as false gets discounted wholesale,
including the part that was right. The line drawn instead is **settled finding
versus the path taken to it**, with a falsifiable test: *would this sentence
still be true if the work had gone right the first time?* A constraint, a root
cause, or a rejected alternative passes. A sequence of failed attempts does not.

Rejected: a read-only rule making `## Context` and `## Approach` untouchable by
Implement. It draws the sharpest line and would be mechanically checkable, but
genuine intent corrections do arrive mid-implementation, so the rule would be
violated for good reasons and then discounted generally. The material-deviation
route in Step 6 already handles those, and pointing at it is enough.

Also rejected for now: extending `docs/knowledge/tests/test_plan_checkboxes.py`
to catch this automatically. The gate reads shape, and "narration" has no
reliable shape — a line-count or prose-to-task ratio heuristic would fire on
legitimately long plans and miss a short dense logbook. Filed as backlog
instead, so the idea is not lost.

## Implementation Steps

The wording below was reviewed and approved before this plan was written. It is
reproduced verbatim rather than described, so a future session applies the
approved text instead of re-deriving something merely equivalent. Replace the
whole `## Verification results` bullet at `.claude/skills/plan/SKILL.md:69-71`
with the block in Task 1; insert Tasks 2 and 3 as new sections.

### Task 1: Scope `## Verification results` to its actual purpose

**Files:** Modify: `.claude/skills/plan/SKILL.md`

- [ ] Replace the `## Verification results` bullet with exactly this text,
  preserving its three-space list indentation in the surrounding section list

``` markdown
   - `## Verification results` — narrative evidence for the plan as a whole,
     written as the work happens rather than reconstructed at the end (omit
     until there is something to record). This is the plan's only narrative
     section: results of the `## Verification` checks, and findings that
     change what the plan claims. Not a running account of attempts — see
     `## Rules`.
```

The trailing pointer needs one resolution the approved draft left open: plan's
`## Rules` (`.claude/skills/plan/SKILL.md:145-164`) carries no narration rule
today, so `see ## Rules` currently dangles. Point it at
`docs/knowledge/AGENTS.md` `## Never write a working logbook into the graph`
instead — that is where Task 3 puts the rule, and it is the only change to the
approved wording in this plan.

### Task 2: Give Implement a capture-and-route section

**Files:** Modify: `.claude/skills/implement/SKILL.md`

- [ ] Insert this section verbatim between `## Steps` and `## Rules`
  (`.claude/skills/implement/SKILL.md:73`)

``` markdown
## Capturing what implementation turns up

Implementation produces findings the plan never anticipated, and they are often
the most expensive knowledge in the session. They do not belong in the plan.
Each has a home:

- A durable design fact — a constraint, a boundary, why the obvious approach
  fails → `data/architecture/<slug>.md`, linked from `data/architecture.md`.
  Add to the existing doc that owns the area before creating a new one.
- A defect in shipped behavior, not caused by this work →
  `data/bugs/<slug>.md` (Symptom / Reproduction / Root cause / Fix, with
  `path:line` anchors), linked from `data/bugs.md`.
- Work this plan should not absorb → `data/backlog/<slug>.md`, and say so in
  the handoff report rather than growing `## Out of scope` silently.
- A finding that changes a material boundary → stop and take it back through
  the plan skill (Step 6), which is the only route that may edit intent.

`## Context` and `## Approach` state intent and stay stable while you build.
The plan skill owns them; implement edits them only via Step 6's material
deviation route. Writing a finding into them, rather than routing it, is the
most common way a plan stops being executable — it grows to where a future
session cannot tell what was planned from what merely happened.

Reproducing a finding is normal work: a harness, a script, an ablation. The
harness is code and lives in the repository. Its *output* is not plan content.
```

### Task 3: State the settled-versus-path rule in the operating manual

**Files:** Modify: `docs/knowledge/AGENTS.md`

- [ ] Insert this section verbatim after `## Conventions`
  (`docs/knowledge/AGENTS.md:74`) and before `## iwe basics`

``` markdown
## Never write a working logbook into the graph

Knowledge documents record what is **settled**, not the path taken to settle it.
A blow-by-blow account of an in-flight investigation — attempt one failed,
attempt two failed differently, CI run IDs, per-attempt tables, "died one script
later" — belongs in the conversation and the commit history, never in `data/`.

The test: **would this sentence still be true if the work had gone right the
first time?** A constraint, a root cause, a rejected alternative: yes. The
sequence of failures that revealed it: no. Keep the first, drop the second.

This is not a ban on troubleshooting content. `data/bugs/` requires
Reproduction and Root cause; `data/architecture/` is where a hard-won
constraint belongs, with the alternatives that lost. Both record a *conclusion*,
written once, in its own document. `data/log.md` is retrospective by design —
one entry per shipped change, after the fact. What has no home anywhere is the
running account written *while* you are still finding out.

Plans are where this fails most often, because the plan is the document already
open. A plan that doubles in length during implementation has almost certainly
absorbed a logbook; the fix is to route each finding to its own document (see
the implement skill's `## Capturing`) and cut the narration.
```

### Task 4: Fix the stale operating-manual path

**Files:** Modify: `AGENTS.md`, `docs/knowledge/data/product.md`

- [ ] Correct `docs/knowledge/data/AGENTS.md` to `docs/knowledge/AGENTS.md` in
  `AGENTS.md:75` and `docs/knowledge/data/product.md:155` — the file has never
  existed at the referenced path, so the manual the new prohibition lives in is
  currently pointed at by two dead references

### Task 5: Record the deferred automation

**Files:** Create:
`docs/knowledge/data/backlog/detect-plan-narration-growth.md`; Modify:
`docs/knowledge/data/backlog.md`

- [ ] File a `stage: planned` backlog task for investigating whether plan
  narration growth can be detected mechanically, recording why the shape gate
  cannot do it today, and link it under the appropriate priority section

### Task 6: Update the workflow skills spec

**Files:** Modify: `docs/knowledge/data/spec/iwe-workflow-skills.md`

- [ ] Apply the `## Spec changes` delta below — one new requirement plus its
  scenarios — and confirm the existing Implement and Plan requirements still
  read true beside it

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — the durable contract for
these skills. This work adds a requirement that no existing one covers: today's
`Requirement: Implement never hides a material deviation` governs checkboxes and
deviations, and says nothing about what a session may write into a plan's prose.

```
ADDED Requirement: Plans record intent, not the path taken to it

Plan documents SHALL record what is settled rather than the sequence of attempts
that settled it. `## Verification results` SHALL be a plan's only narrative
section. Implement SHALL route a finding that does not change the plan's intent
to its own document — `data/architecture/`, `data/bugs/`, or `data/backlog/` —
rather than into the plan's `## Context` or `## Approach`, which state intent and
remain the Plan skill's to own.

#### Scenario: Implementation produces a durable finding

- **WHEN** implementation establishes a constraint, root cause, or rejected
  alternative that the plan did not anticipate
- **THEN** Implement records it in the reference document that owns the area and
  reports the capture, leaving the plan's intent sections unchanged

#### Scenario: A session narrates its attempts into a plan

- **WHEN** a plan would gain a running account of an in-flight investigation —
  failed attempts, CI run identifiers, per-attempt tables
- **THEN** that content is excluded from the plan, because it would not be true
  had the work succeeded the first time

#### Scenario: A finding changes the plan's intent

- **WHEN** a finding alters scope, observable behavior, compatibility,
  acceptance criteria, dependencies, or an out-of-scope boundary
- **THEN** it goes back through the Plan skill's revise mode rather than being
  captured elsewhere or written into the plan directly
```

## Verification

- `uv run pytest docs/knowledge/tests/test_plan_checkboxes.py` — the plan-shape
  gate stays green, including `test_repository_plans_satisfy_the_checkbox_rules`
  over this plan itself
- `iwe normalize && iwe schema validate` — both clean, run from the repo root
- Read `.claude/skills/implement/SKILL.md` end to end as a future implementer:
  confirm `## Capturing` and `## Rules` do not contradict each other, and that
  Step 6's material-deviation route is reachable from the new section
- Confirm no remaining reference to `docs/knowledge/data/AGENTS.md`:
  `grep -rn "data/AGENTS.md" AGENTS.md docs/` returns nothing
- Re-read the cleaned
  [AI responder workflows](20260816-ai-responder-workflows.md) against the new
  wording and confirm the rules would have caught what the maintainer caught by
  hand

## Out of scope

- Rewriting plans already in the graph. `data/log.md` and closed plans are
  historical records; retroactively cutting narration from them would destroy
  evidence to satisfy a rule written afterwards
- Automating detection of narration growth — deferred to backlog in Task 5
- Moving the skills into the agentdev plugin. Tracked independently by
  [Move the IWE workflow skills into the agentdev plugin](20260816-move-iwe-skills-to-agentdev.md);
  the two plans touch the same files but not the same concerns, and whichever
  lands second re-locates its anchors
- Changing `data/log.md`'s chronological form, or `data/bugs/`'s Symptom /
  Reproduction / Root cause / Fix shape. Both are deliberate and the prohibition
  carves them out explicitly

## Key references

Verified anchor points (line numbers as of 2026-08-17):

- `.claude/skills/plan/SKILL.md:69-71` — the `## Verification results` bullet
  that Task 1 scopes
- `.claude/skills/implement/SKILL.md:73` — `## Rules`, the boundary Task 2's new
  section is inserted before
- `.claude/skills/implement/SKILL.md:44-56` — Step 6's tactical-correction and
  material-deviation split, which Task 2 cross-references rather than restates
- `.claude/skills/explore/SKILL.md:47` — `## Capturing`, the section Task 2
  mirrors
- `docs/knowledge/AGENTS.md:74` — `## Conventions`, after which Task 3 inserts
- `docs/knowledge/data/spec/iwe-workflow-skills.md:127` —
  `Requirement: Implement never hides a material deviation`, the neighbor the
  new requirement sits beside
- `docs/knowledge/data/spec/plan-checkbox-evidence.md:92-104` — the narrative
  evidence requirement whose scope Task 1 clarifies
- `docs/knowledge/tests/test_plan_checkboxes.py:26` — `PLANS_DIR`, the existing
  shape gate Task 5's backlog entry considers extending
- `AGENTS.md:75` and `docs/knowledge/data/product.md:155` — the two dead
  `docs/knowledge/data/AGENTS.md` references Task 4 fixes
