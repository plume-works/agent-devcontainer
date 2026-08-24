---
type: plan
created: 2026-08-17
description: Bind every file in the repository against working-logbook prose by promoting the durable-knowledge rule into the repository operating manual as Best Practice 8, scoping the plan clause that invites narration, giving Implement a capture-and-route section, reducing the graph manual to its genuine narrative exceptions, and widening the iwe-audit scope to match.
generated:
  by: claude-code/opus-5
  at: 2026-08-17T00:00:00Z
sources:
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/skills/iwe-audit/SKILL.md
- resource: .claude/skills/plan/SKILL.md
- resource: .claude/skills/implement/SKILL.md
- resource: .claude/skills/explore/SKILL.md
- resource: docs/knowledge/AGENTS.md
- resource: docs/knowledge/data/product.md
- resource: docs/knowledge/data/spec/iwe-workflow-skills.md
- resource: docs/knowledge/data/spec/plan-checkbox-evidence.md
---

# Never write a working logbook

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

The behavior is not specific to plans or to this repository's graph. The
maintainer reports the same residue in READMEs, code comments, skill files, and
agent definitions — it is characteristic of the current generation of LLMs, and
it lands in whatever text the model is writing. The rule therefore binds every
file, not one directory. `AGENTS.md` is the operating manual every agent reads,
so that is where it goes.

## Approach

Five coordinated edits. All the wording was drafted and approved as finished
text before it reached this plan, so the tasks carry it verbatim in fenced
blocks rather than describing it. Approved wording is a deliverable, not an
instruction to produce one: a paraphrase silently drops the specifics — which
document owns a finding before a new one is created, the exact bug-document
shape — and a future session applying a description would write something
reasonable and different. The fenced blocks in this plan are the approved text
itself, not a record of it: they are the only copy, and applying a task means
transcribing its block unchanged.

**State the rule where it binds every file.** Root `AGENTS.md`, as Best Practice
8 — the numbered list every agent reads, not a section scoped to the graph. The
rule covers documents, READMEs, code comments, skills, agent definitions,
docstrings, and issue and PR bodies.

**Extract the durable-knowledge definition into that rule.** The
`**Durable knowledge only.**` block currently sits under `## Project memory`,
which scopes it by its parent heading to `docs/knowledge/data/`. Its text is
shared vocabulary — `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:14-20`
carries the two bullets and the "rewritten from scratch" test verbatim — so it
moves word-for-word, changing only list indentation, and the two places that
pointed at its old location are repointed.

Two tests then coexist deliberately. *Rewritten from scratch* asks whether a
fact is durable; *gone right the first time* asks whether a sentence is a
logbook trace. A durable fact can still be phrased as narration, which is
exactly the residue being removed, so the second test is not a duplicate of the
first.

**Reduce the graph manual to what only the graph knows.**
`docs/knowledge/AGENTS.md` gains the narrative exceptions — `data/bugs/`,
`data/log.md`, and a plan's `## Verification results` — and points at Best
Practice 8 for the prohibition itself, so the rule is stated once and the
carve-outs live where they apply.

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

**Widen the auditor to match the rule.** `iwe-audit` audits graph documents and
code comments today. Its scope grows to the non-graph prose the rule now covers,
and names the surfaces it must not audit — including commit messages, which
`/agentdev:git-commit` owns.

Commit messages are out of scope entirely. That skill has its own rules and this
plan does not touch it.

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

Every fenced block below is approved text, reproduced verbatim rather than
described, so a future session applies the approved wording instead of
re-deriving something merely equivalent. These blocks are the approved text
itself — there is no other copy to consult. Transcribe each one unchanged, and
treat any difference between a block and what lands in the file as a defect in
the edit.

### Task 1: State the rule as Best Practice 8 in the repository manual

**Files:** Modify: `AGENTS.md`

- [x] Insert this item verbatim after item 7 (`AGENTS.md:21`) and before
  `### When in Doubt`, as a new numbered item 8. The second half is the
  `**Durable knowledge only.**` block extracted from `## Project memory`
  (`AGENTS.md:96-107`) — word-for-word, with only the three-space list indent
  and the resulting line wraps changed
  - **Evidence:** `AGENTS.md:23-46` now carries item 8; a scripted diff of the
    applied text against this task's fenced block reports an exact match, and a
    whitespace-normalized diff of the pre-edit `AGENTS.md:96-107` against the
    applied `**Durable knowledge only.**` half confirms it moved word-for-word.

``` markdown
8. **Never write a working logbook — in any text you produce.** Documents,
   READMEs, code comments, skills, agent definitions, docstrings, issue and PR
   bodies: record what is **settled**, not the path taken to settle it. A
   blow-by-blow account of an in-flight investigation — attempt one failed,
   attempt two failed differently, CI run IDs, per-attempt tables, "died one
   script later" — belongs in the conversation, never in a file. The test:
   **would this still be true if the work had gone right the first time?** A
   constraint, a root cause, a rejected alternative: yes. The sequence of
   failures that revealed it: no. Keep the first, drop the second. Where
   narrative *is* the format, the rules that own that format say so; nothing
   here overrides them.

   **Durable knowledge only.** A document records what a reader needs to work
   here, not what one session happened to discover.

   - **Durable** — the decision and who made it, the constraint it creates, the
     invariant that must hold, the interface. Survives a reimplementation.
   - **Not durable** — how the decision was reached, what broke on the way, a
     tool's behavior on one day, the alternative that was almost written,
     whether something was hard to find. Dies with the code that provoked it.

   The test: _would this still be true if the code were rewritten from scratch?_
   If no, drop it. Record a decision as a decision — never as the obstacle that
   prompted it, which goes stale and reads as a workaround.
```

- **Evidence:** `AGENTS.md:23-46` now carries item 8; a scripted diff of the
  applied text against this task's fenced block reports an exact match, and a
  whitespace-normalized diff of the pre-edit `AGENTS.md:96-107` against the
  applied `**Durable knowledge only.**` half confirms it moved word-for-word.

### Task 2: Repoint what referenced the extracted block

**Files:** Modify: `AGENTS.md`

- [x] Delete `AGENTS.md:96-107` — the block Task 1 moved — and leave this single
  line in its place, so `## Project memory` still names the rule without
  restating it
  - **Evidence:** the twelve-line block is gone from `## Project memory`,
    replaced by the single approved pointer line at `AGENTS.md:120`;
    `grep -n "see Project memory" AGENTS.md` returns nothing, so no reference to
    the old location dangles.

``` markdown
**Durable knowledge only** — see Best Practice 8 for the definition and the test.
```

- [x] Replace the closing sentence of `### Comments` (`AGENTS.md:43-45`), whose
  "see Project memory" pointer no longer resolves to the definition
  - **Evidence:** `### Comments` now closes with the approved sentence pointing
    at Best Practice 8 (`AGENTS.md:67-69`), matching this task's fenced block
    word-for-word.

``` markdown
A pointer to where a decision is recorded usually earns its line; a paraphrase of
the mechanism never does. Only durable rationale is worth forwarding — see Best
Practice 8.
```

### Task 3: Reduce the graph manual to its narrative exceptions

**Files:** Modify: `docs/knowledge/AGENTS.md`

- [x] Insert this section verbatim after `## Conventions`
  (`docs/knowledge/AGENTS.md:74-144`) and before `## iwe basics`
  (`docs/knowledge/AGENTS.md:145`). It states the exceptions only; Best Practice
  8 states the prohibition
  - **Evidence:** `## Where narrative is the format` now sits between
    `## Conventions` and `## iwe basics` in `docs/knowledge/AGENTS.md`, matching
    this task's fenced block word-for-word; it names only the three carve-outs
    and points at Best Practice 8 for the prohibition.

``` markdown
## Where narrative is the format

Best Practice 8 in the repository `AGENTS.md` binds every file: record what is
settled, not the path taken to settle it. Three places in `data/` are the
exception, by design, and only these:

- `data/bugs/` requires Reproduction and Root cause.
- `data/log.md` is retrospective — one entry per shipped change, after the fact.
- A plan's `## Verification results` holds results of the `## Verification`
  checks and findings that change what the plan claims.

Each records a *conclusion*, written once, in its own document. What has no home
anywhere is the running account written *while* you are still finding out.

Plans are where this fails most often, because the plan is the document already
open. A plan that doubles in length during implementation has almost certainly
absorbed a logbook; the fix is to route each finding to its own document (see
the implement skill's `## Capturing`) and cut the narration.
```

### Task 4: Scope `## Verification results` to its actual purpose

**Files:** Modify: `.claude/skills/plan/SKILL.md`

- [x] Replace the `## Verification results` bullet with exactly this text,
  preserving its three-space list indentation in the surrounding section list
  - **Evidence:** `.claude/skills/plan/SKILL.md:69-74` now carries the scoped
    bullet, word-for-word against this task's fenced block except for the
    trailing pointer, which this task directs be resolved to `AGENTS.md` Best
    Practice 8 instead of the dangling `## Rules`.

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
today, so `see ## Rules` currently dangles. Point it at `AGENTS.md` Best
Practice 8 instead — that is where Task 1 puts the rule. This is the only change
to approved wording anywhere in this plan, and it resolves a pointer the draft
left open rather than altering a sentence.

### Task 5: Give Implement a capture-and-route section

**Files:** Modify: `.claude/skills/implement/SKILL.md`

- [x] Insert this section verbatim between `## Steps` and `## Rules`
  (`.claude/skills/implement/SKILL.md:73`)
  - **Evidence:** `## Capturing what implementation turns up` now sits between
    `## Steps` and `## Rules`, matching this task's fenced block word-for-word.
    Read end to end, the two sections do not overlap — `## Rules` governs
    checkboxes, evidence, commits, and deviations; `## Capturing` governs where
    findings go — and Step 6's material-deviation route is reachable, cited by
    name as the only route that may edit intent.

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

### Task 6: Widen the iwe-audit scope to the text the rule now covers

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md`

- [x] Replace `## Scope` and its two paragraphs
  (`.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:22-29`) with this text
  verbatim. Leave the skill's own `## Durable vs not` block (`:14-20`) untouched
  — it is the same shared vocabulary Task 1 moves, and the two copies must stay
  identical
  - **Evidence:** `## Scope` now matches this task's fenced block word-for-word,
    naming the non-graph surfaces and excluding commit messages;
    `## Durable vs not` was not edited. A scripted comparison confirms both
    durable/not-durable definitions and the rewritten-from-scratch test are
    word-for-word identical across the two copies — they differ only in the
    emphasis markers and the `Test:`/`The test:` label, as they did before this
    work.

``` markdown
## Scope

Audit any text that promises durable content: `data/spec/`,
`data/architecture/`, `data/features/`, `product.md`, code comments, and —
outside the graph — `README.md`, `AGENTS.md`, skill and agent definitions, and
docstrings.

Do not audit: `data/plans/`, `data/bugs/`, `data/releases/`, `data/log.md`, or
commit messages. Process detail is their job; commit messages are owned by
`/agentdev:git-commit`. Residue in a spec may belong in one of these — that is a
move, not a deletion.
```

### Task 7: Fix the stale operating-manual path

**Files:** Modify: `AGENTS.md`, `docs/knowledge/data/product.md`

- [ ] Correct `docs/knowledge/data/AGENTS.md` to `docs/knowledge/AGENTS.md` in
  `AGENTS.md:116` and `docs/knowledge/data/product.md:155` — the file has never
  existed at the referenced path, so the manual Task 3's exceptions live in is
  currently pointed at by two dead references

### Task 8: Record the deferred automation

**Files:** Create:
`docs/knowledge/data/backlog/detect-plan-narration-growth.md`; Modify:
`docs/knowledge/data/backlog.md`

- [ ] File a `stage: planned` backlog task for investigating whether plan
  narration growth can be detected mechanically, recording why the shape gate
  cannot do it today, and link it under the appropriate priority section

### Task 9: Update the workflow skills spec

**Files:** Modify: `docs/knowledge/data/spec/iwe-workflow-skills.md`

- [ ] Apply the `## Spec changes` delta below — one new requirement plus its
  scenarios — and confirm the existing Implement and Plan requirements still
  read true beside it

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — the durable contract for
these skills. This work adds a requirement that no existing one covers: today's
`Requirement: Implement never hides a material deviation` governs checkboxes and
deviations, and says nothing about what a session may write into a plan's prose.

The requirement below is scoped to the workflow skills, which is all this spec
governs. The general rule binding every file in the repository is an authoring
convention, not a workflow-skill contract: `AGENTS.md` is its only statement,
and `docs/knowledge/data/product.md` `## Authoring rules` already summarizes
that manual for graph readers. No new spec document is created for it.

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
- Confirm the extracted block survived the move word-for-word — normalize
  whitespace on the pre-edit text and the applied item 8 and diff them; only
  indentation and line-wrap positions may differ
- Confirm each applied edit matches this plan's corresponding fenced block
  word-for-word, allowing only the indentation each insertion point requires and
  the Markdown normalizations the repository's `prettier` hook enforces on
  commit (emphasis written `_x_` rather than `*x*`, and no blank line between a
  paragraph and the list that follows it). Every word must still match; the hook
  owns the syntax, this plan owns the wording
- Confirm the two copies of the durable-knowledge vocabulary still agree:
  `AGENTS.md` item 8 and
  `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:14-20`
- Confirm no pointer to the extracted block dangles:
  `grep -n "see Project memory" AGENTS.md` returns nothing
- Re-read the cleaned
  [AI responder workflows](20260816-ai-responder-workflows.md) against the new
  wording and confirm the rules would have caught what the maintainer caught by
  hand

## Out of scope

- Commit messages. `/agentdev:git-commit` owns that surface and this plan does
  not touch the skill; Task 6 names commit messages only to exclude them from
  the auditor's scope
- Auditing or rewriting existing prose for residue. This plan states the rule
  and widens the auditor; running the audit across the repository is separate
  work
- Rewriting plans already in the graph. `data/log.md` and closed plans are
  historical records; retroactively cutting narration from them would destroy
  evidence to satisfy a rule written afterwards
- Automating detection of narration growth — deferred to backlog in Task 8
- Moving the skills into the agentdev plugin. Tracked independently by
  [Move the IWE workflow skills into the agentdev plugin](20260816-move-iwe-skills-to-agentdev.md);
  the two plans touch the same files but not the same concerns, and whichever
  lands second re-locates its anchors
- Changing `data/log.md`'s chronological form, or `data/bugs/`'s Symptom /
  Reproduction / Root cause / Fix shape. Both are deliberate and the prohibition
  carves them out explicitly

## Key references

Verified anchor points (line numbers as of 2026-08-24):

- `AGENTS.md:21` — the end of item 7 in `## Best Practices for Agents`, after
  which Task 1 inserts item 8
- `AGENTS.md:43-45` — the `### Comments` closing sentence whose "see Project
  memory" pointer Task 2 repoints
- `AGENTS.md:96-107` — the `**Durable knowledge only.**` block Task 1 extracts
  and Task 2 replaces with a pointer
- `AGENTS.md:116` — the dead `docs/knowledge/data/AGENTS.md` reference Task 7
  fixes
- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:14-20` — the second copy
  of the durable-knowledge vocabulary, which stays untouched and must keep
  matching item 8
- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:22-29` — `## Scope`, the
  two paragraphs Task 6 replaces
- `docs/knowledge/AGENTS.md:74` — `## Conventions`, after which Task 3 inserts
- `docs/knowledge/AGENTS.md:145` — `## iwe basics`, the section Task 3's
  insertion precedes
- `.claude/skills/plan/SKILL.md:69-71` — the `## Verification results` bullet
  that Task 4 scopes
- `.claude/skills/implement/SKILL.md:73` — `## Rules`, the boundary Task 5's new
  section is inserted before
- `.claude/skills/implement/SKILL.md:44-56` — Step 6's tactical-correction and
  material-deviation split, which Task 5 cross-references rather than restates
- `.claude/skills/explore/SKILL.md:47` — `## Capturing`, the section Task 5
  mirrors
- `docs/knowledge/data/spec/iwe-workflow-skills.md:127` —
  `Requirement: Implement never hides a material deviation`, the neighbor the
  new requirement sits beside
- `docs/knowledge/data/spec/plan-checkbox-evidence.md:92-104` — the narrative
  evidence requirement whose scope Task 4 clarifies
- `docs/knowledge/tests/test_plan_checkboxes.py:26` — `PLANS_DIR`, the existing
  shape gate Task 8's backlog entry considers extending
- `docs/knowledge/data/product.md:155` — the second dead
  `docs/knowledge/data/AGENTS.md` reference Task 7 fixes
