---
type: plan
created: 2026-08-15
description: Adopt OpenSpec's behavioral prompt language into the five IWE workflow skills — authorization boundaries, materiality thresholds, evidence rules, mandatory pre-ship verification, and restart-safe spec merge — without importing OpenSpec's change-bundle machinery.
generated:
  by: claude-code/opus-5
  at: 2026-08-16T02:00:00Z
sources:
- .claude/skills/explore/SKILL.md
- .claude/skills/plan/SKILL.md
- .claude/skills/implement/SKILL.md
- .claude/skills/verify/SKILL.md
- .claude/skills/ship/SKILL.md
stage: done
completed: 2026-08-16
---

# Strengthen the workflow skill contracts

**This plan is a post-hoc reconstruction.** The work was executed through an
OpenSpec change bundle named `2026-08-16-strengthen-iwe-workflow-skills`, whose
proposal, design, and task artifacts lived under a directory `.gitignore` keeps
out of the repository. Its motivation, design decisions, and rejected
alternatives therefore existed only in one working tree and would have been lost
on the next clone. This plan was written from those three artifacts after the
fact; they are deliberately not linked, because nothing in the repository
resolves them. Every task box below carries the commit that landed it rather
than an unbacked tick — no box here asserts work that a named commit does not
show.

## Context

The IWE workflow is encoded in five short prompt contracts under
`.claude/skills/`, with `docs/knowledge/AGENTS.md` defining the surrounding
graph and OKF invariants. The lifecycle was coherent, but several high-value
behavioral guardrails were implicit or unevenly expressed across the skills:
planning boundaries, ambiguity handling, implementation deviations,
verification, and spec synchronization.

The sharpest instance was already recorded in project memory.
[Verification in the main loop](../features/verification-in-the-main-loop.md)
noted that `docs/knowledge/AGENTS.md` describes shipping as following a green
Verify result, while Ship treated Verify as the optional thorough form of a
looser confirmation step. Normal shipping could therefore proceed without
requirement tracing, scenario coverage, or coherence checks.

OpenSpec's explore → propose → apply → archive prompts encode much of this
judgment explicitly. The opportunity was to adopt the language that changes
agent behavior while rejecting the machinery — stores, artifact graphs, delta
specs, file-move archiving — that conflicts with IWE's graph and single-plan
model.

The implementation is prompt-only but cross-cutting: wording in one skill
changes ownership and handoffs in the others, so the edits had to be designed as
one behavioral state machine rather than isolated prose improvements.

## Approach

Eight decisions shaped the change. Each is recorded with the alternative it
displaced, because the alternatives were the substance of the design work.

**1. Adapt behavioral language, not workflow machinery.** Each skill gains only
the OpenSpec language that changes agent judgment: authorization boundaries,
material-ambiguity criteria, pause conditions, evidence rules, coherence checks,
post-write verification. IWE-native commands, document names, and ownership stay
authoritative. *Rejected:* wholesale prompt transplantation — the OpenSpec
skills repeatedly encode stores, artifact graphs, delta specs, and file-move
archiving that contradict IWE's model. Also rejected: merely renaming OpenSpec
terminology into IWE names, which would retain those structural assumptions
implicitly.

**2. Preserve the skill count; distribute ownership.** The useful behavior from
OpenSpec's Update and Sync skills folds into existing owners:

| Concern                                          | Owning IWE skill |
| ------------------------------------------------ | ---------------- |
| Open-ended and mid-implementation investigation  | Explore          |
| Create or revise planning state                  | Plan             |
| Record tactical deviations while executing       | Implement        |
| Prove graph claims against code                  | Verify           |
| Merge durable specs and transition shipped state | Ship             |

Plan gains create and revise modes rather than a separate plan-update skill;
Ship remains the only workflow that synchronizes durable specs. *Rejected:*
separate Update and Sync skills, which would create new entry points and weaken
existing ownership boundaries.

**3. One shared threshold for material decisions.** Plan and Implement use the
same classification: a decision is material when it affects scope, externally
observable behavior, compatibility, acceptance criteria, dependencies, or an
explicit out-of-scope boundary. Plan asks about material ambiguity but records
reasonable minor assumptions; Implement may repair intent-preserving details but
pauses before coding through a material deviation. *Rejected:* the two failure
extremes — interrogating the user about every detail, or silently changing the
contract to fit the implementation.

**4. Plan revision is bidirectional reconciliation.** In revise mode, Plan reads
the complete active plan, applies the requested decision, and reconciles every
affected section in either direction — a task edit may force an Approach or
Verification edit just as an Approach edit may force new tasks or spec impact.
Affected anchors are re-verified. A revision stays in the same plan only while
topic, intended outcome, and verification story remain materially the same.
*Rejected:* replacing an active plan's intent in place, which destroys the
historical meaning of already-completed tasks and their evidence.

**5. Tactical corrections are separate from material deviations.** Implement may
update stale anchors or task decomposition and continue when intent is
preserved; it must pause when work would add scope or drop, narrow, defer, or
exempt specified behavior. A checkbox represents fully implemented specified
behavior with passing evidence — plan text, context, or an existing checkbox is
a claim, not proof.

**6. Verify becomes a mandatory dependency of normal Ship.** Ship first selects
cancellation or normal shipping:

``` text
                         ┌─ cancellation ─▶ cancel plan ─▶ validate/commit
select plan and mode ────┤
                         └─ normal ship ──▶ Verify ─▶ spec sync ─▶ transitions
                                                │
                                                └─ CRITICAL ─▶ stop unchanged
```

Normal Ship proceeds only on zero CRITICAL findings. Verify stays report-only
and independently invocable. Cancellation bypasses implementation verification,
spec synchronization, feature implementation, and release recording. *Rejected:*
duplicating Verify's completeness/correctness/coherence checks inside Ship,
because the two copies would drift. Also rejected: letting a user confirmation
override CRITICAL findings — a plan should remain active or be cancelled rather
than recorded as shipped while its durable claims are known false. This is the
change's breaking element.

**7. Ship is an ordered, restart-safe transaction over the graph.** After Verify
passes: inspect current graph state and the plan's complete `## Spec changes`;
read each existing spec and the verified evidence; merge changed behavior while
preserving unaffected requirements, scenarios, order, and valid explanation;
re-read every planned spec to confirm it matches shipped behavior; only then
update plan, feature or bug, release, and log state; then normalize, validate,
commit. Every step checks whether the intended result already exists, so a
restarted Ship does not duplicate hub links, release entries, or log bullets.
Whole-document spec retirement uses `iwe delete` so references are repaired.
*Rejected:* overwriting specs from plan prose, since plans can be stale and it
could erase unaffected scenarios. Also rejected: updating graph stages before
verifying spec synchronization, which creates a falsely completed plan.

**8. Validate prompt structure and behavioral coherence, not exact wording.**
Run the repository's skill validator over `.claude/skills`, then review the diff
against each new scenario; run `iwe normalize` and `iwe schema validate` for
project-memory edits. *Rejected:* a runtime test harness asserting exact
sentences, because equivalent prompt improvements should not fail on harmless
rewording.

### Risks accepted

- **Prompt growth dilutes important rules** → keep additions concise, remove
  redundant wording, place each rule only in its owning skill.
- **Materiality stays judgment-based** → one explicit criteria list shared by
  Plan and Implement, with concrete pause behavior.
- **Mandatory Verify makes Ship slower** → accepted, because Ship mutates
  durable project claims; Verify stays independently usable during
  implementation to surface problems earlier.
- **Restart safety is hard to express without executable transactions** →
  require inspection before every mutation and explicit duplicate avoidance.
- **Spec-merge language could import delta-spec assumptions** → refer only to
  current IWE specs, plan `## Spec changes`, and verified evidence.
- **Plan revision overlaps Implement deviations** → Plan owns user-requested
  planning-only revision; Implement owns discoveries made while executing.

## Implementation Steps

Executed in dependency order — Explore, Plan, Implement, Verify, then Ship — so
each skill's handoffs were settled before the next skill referenced them.

### Task 1: Establish the prompt contract baseline

**Files:** No file changes (analysis only)

- [x] **1.1 Capture the behavior and validation baseline** for the five target
  `SKILL.md` files, following the semantic-refactor audit workflow so preserved
  IWE/OKF behavior could be compared after editing. *Evidence:* pre-work
  analysis; no commit — the baseline is the parent of `0d4d37b`.
- [x] **1.2 Build a scenario-to-owner checklist** confirming each requirement
  belongs to exactly one primary skill, and identify the required cross-skill
  handoffs before changing prompt text. *Evidence:* the ownership table in
  `## Approach` decision 2.

### Task 2: Strengthen exploration and planning

**Files:** Modify: `.claude/skills/explore/SKILL.md`,
`.claude/skills/plan/SKILL.md`

- [x] **2.1 Update Explore** with adaptive and patient inquiry, concise
  exploratory actions, and mid-implementation handling, preserving its no-code
  boundary, IWE grounding, capture destinations, and closing summary.
  *Evidence:* `0d4d37b` — `explore/SKILL.md` +26/-8; added
  `## During implementation` (`explore/SKILL.md:39`).
- [x] **2.2 Update Plan** with the planning-only authorization boundary, shared
  material-ambiguity criteria, minor-assumption recording, existing-plan
  collision handling, and a final whole-plan coherence check. *Evidence:*
  `0d4d37b` — `plan/SKILL.md` +64/-9; materiality at `plan/SKILL.md:32-37`,
  coherence pass at `plan/SKILL.md:84-87`.
- [x] **2.3 Add create and revise modes to Plan** so a requested active-plan
  revision is reconciled bidirectionally, affected anchors are re-verified,
  materially different intent becomes distinct work, and no implementation code
  is edited. *Evidence:* `0d4d37b` — mode selection at `plan/SKILL.md:17-30`.

### Task 3: Strengthen implementation and verification handoffs

**Files:** Modify: `.claude/skills/implement/SKILL.md`,
`.claude/skills/verify/SKILL.md`

- [x] **3.1 Update Implement** to distinguish tactical corrections from material
  deviations, pause before silently expanding or narrowing specified behavior,
  and keep the one-task-at-a-time default. *Evidence:* `61cce13` —
  `implement/SKILL.md` +37/-14; deviation classification at
  `implement/SKILL.md:35-45`.
- [x] **3.2 Tighten Implement's checkbox and status-report contract** so
  partial, deferred, or failing work stays unchecked and completion reports
  identify actual code, tests, and checks as evidence. *Evidence:* `61cce13` —
  the rule at `implement/SKILL.md:56-60`.
- [x] **3.3 Update Verify** only as needed to make its report-only,
  independently invocable behavior and zero-CRITICAL Ship handoff explicit,
  without duplicating Ship's state transitions. *Evidence:* `61cce13` —
  `verify/SKILL.md` +13/-4; handoff at `verify/SKILL.md:70-71`.

### Task 4: Make shipping verified and restart-safe

**Files:** Modify: `.claude/skills/ship/SKILL.md`

- [x] **4.1 Restructure Ship** to select cancellation versus normal shipping
  first, make normal shipping invoke Verify and stop on every CRITICAL, and keep
  cancellation free of implementation verification, spec synchronization, and
  release transitions. *Evidence:* `fcdd45a` — `ship/SKILL.md` +98/-47; step 1
  at `ship/SKILL.md:16`, cancellation at `ship/SKILL.md:29`, "there is no
  CRITICAL override" at `ship/SKILL.md:35-41`.
- [x] **4.2 Rewrite Ship's spec-sync as an intelligent merge** from verified
  behavior: preserve unaffected requirements and scenarios, handle explicit
  retirement through `iwe delete`, re-read every planned spec, and refuse
  durable completion on any mismatch or validation failure. *Evidence:*
  `fcdd45a` — `ship/SKILL.md:42-60`.
- [x] **4.3 Make every Ship mutation inspect current state first** and avoid
  duplicate plan-hub, feature/bug, unreleased, and log entries, so an
  interrupted invocation can resume safely. *Evidence:* `fcdd45a` —
  `ship/SKILL.md:61-78`.

### Task 5: Reconcile durable project memory

**Files:** Modify:
`docs/knowledge/data/features/verification-in-the-main-loop.md`,
`docs/knowledge/README.md`

- [x] **5.1 Update the verification feature doc** to record the resolved
  decisions — Ship-only mandatory verification, no CRITICAL override, and the
  cancellation exemption — keeping its OKF metadata and lifecycle fields
  consistent. *Evidence:* `a35c802` — feature doc +73/-41, `stage: implemented`.
- [x] **5.2 Review `docs/knowledge/AGENTS.md`, `README.md`, and `STRUCTURE.md`**
  against the revised contracts, editing only statements made inaccurate by the
  change. *Evidence:* `a35c802` — `docs/knowledge/README.md` +15/-11 only.
  `AGENTS.md` and `STRUCTURE.md` were reviewed and left unchanged; their last
  touch remains `d4bcf7d` and `391d9b8` respectively.

### Task 6: Validate the complete workflow

**Files:** No file changes (validation only)

- [x] **6.1 Run the skill validator** and resolve every validation error
  introduced by the prompt edits. *Evidence:*
  `uv run validate_agent_files --kind skills .claude/skills --ci` clean at the
  time of `fcdd45a`.
- [x] **6.2 Run `iwe normalize` and `iwe schema validate`**, inspect
  normalization changes, and resolve every graph or OKF validation error.
  *Evidence:* clean at `a35c802`; re-confirmed exit 0 on 2026-08-16.
- [x] **6.3 Compare the final diff against every scenario**, confirming Setup
  and Weekly remain unchanged and no OpenSpec artifact, store, archive-move, or
  delta-spec terminology entered the IWE skills. *Evidence:* neither
  `setup/SKILL.md` nor `weekly/SKILL.md` appears in `0d4d37b`, `61cce13`,
  `fcdd45a`, or `a35c802`.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — **created**. Six
requirements covering Explore's adaptive thinking mode, Plan's write-planning-
state-only boundary and materiality threshold, Implement's material-deviation
rule, Ship's mandatory clean verification, Ship's intelligent spec merge, and
the preservation of the IWE/OKF model.

The spec landed in `b0bc56a` ahead of this reconstruction, imported from the
change bundle's capability spec. That delta was a pure `## ADDED Requirements`
block — no MODIFIED or REMOVED sections — so the delta and the durable spec are
the same document modulo line wrapping and the heading.

## Verification

- `uv run validate_agent_files --kind skills .claude/skills --ci` — clean.
- `iwe normalize` then `iwe schema validate` — exit 0, re-confirmed on
  2026-08-16 both before and after this plan was filed.
- The five edited skills each carry the rules assigned to them by the ownership
  table, and no rule appears in two skills.
- `.claude/skills/setup/SKILL.md` and `.claude/skills/weekly/SKILL.md` are
  untouched by every commit in this plan.
- No OpenSpec vocabulary — "change bundle", "delta spec", "store", "archive
  move" — appears in any `.claude/skills/*/SKILL.md`.

## Out of scope

Recorded as explicit non-goals during design:

- **Reproducing OpenSpec's change directories, artifact schemas, stores, or
  delta specifications in IWE.** The graph, not a bundle directory, stays the
  system of record.
- **New IWE skills for updating plans or syncing specs.** Plan's revise mode and
  Ship's spec merge absorb those concerns.
- **Changing OKF schemas, document types, stage/status vocabularies, graph
  membership rules, or the timing of durable spec updates.**
- **Changing Setup or Weekly behavior.**
- **Turning OpenSpec's prose examples into embedded tutorials** inside the IWE
  skills.

Discovered after this work and owned elsewhere:

- **The two remaining handoff routes** — Explore's missing defect destination
  and Verify's third unchecked-box route — owned by
  [Name the missing handoff routes in explore and verify](20260816-skill-handoff-routes.md).
- **The ticked-box asymmetry**, where Verify takes a `- [x]` on faith, owned by
  [Make plan checkboxes carry their evidence](20260815-honest-plan-checkboxes.md).

## Key references

Verified anchor points (line numbers as of 2026-08-16):

- `.claude/skills/explore/SKILL.md:39` — `## During implementation`, added by
  task 2.1
- `.claude/skills/explore/SKILL.md:47` — `## Capturing` and its destinations
- `.claude/skills/plan/SKILL.md:17-30` — step 1, create/revise mode selection
  and collision handling (task 2.3)
- `.claude/skills/plan/SKILL.md:32-37` — step 2, the shared materiality
  threshold (task 2.2)
- `.claude/skills/plan/SKILL.md:84-87` — step 6, the whole-plan coherence pass
- `.claude/skills/implement/SKILL.md:35-45` — step 6, deviation classification
  (task 3.1)
- `.claude/skills/implement/SKILL.md:56-60` — the never-tick rule (task 3.2)
- `.claude/skills/verify/SKILL.md:66-71` — `## Rules`, "Report, never fix" and
  the zero-CRITICAL Ship handoff (task 3.3)
- `.claude/skills/ship/SKILL.md:16-28` — step 1, operation selection and state
  inspection (task 4.1)
- `.claude/skills/ship/SKILL.md:29-34` — step 2, cancellation without shipping
- `.claude/skills/ship/SKILL.md:35-41` — step 3, "there is no CRITICAL override"
  (task 4.1)
- `.claude/skills/ship/SKILL.md:42-60` — steps 4-5, the spec merge and its
  pre-lifecycle verification (task 4.2)
- `.claude/skills/ship/SKILL.md:61-78` — step 6, idempotent graph transitions
  (task 4.3)
