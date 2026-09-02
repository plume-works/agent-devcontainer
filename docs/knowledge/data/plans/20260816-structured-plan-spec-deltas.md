---
type: plan
created: 2026-08-16
description: Add risk-scaled, plan-local spec deltas so behavior-changing IWE plans carry a reviewable pre-ship contract without importing OpenSpec change bundles or claiming deterministic application.
generated:
  by: codex
  at: 2026-08-16T01:27:59Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: docs/knowledge/data/spec/iwe-workflow-skills.md
- resource: docs/knowledge/STRUCTURE.md
stage: done
completed: 2026-08-16
---

# Embed structured spec deltas in IWE plans

## Context

The current Plan contract requires `## Spec changes`, but only requires it to
name each durable spec the work will create or change. That makes the plan
locate the affected contract without necessarily stating the intended
post-change behavior. The gap is most visible at the Verify → Ship boundary:
Verify currently expects each named durable spec to exist and already reflect
the change, while Ship is the workflow that is supposed to update those specs
after Verify passes. A new spec represented by a back-ticked future key is
therefore described as valid planning state by Plan and as a pre-ship CRITICAL
by Verify.

The earlier
[Strengthen the workflow skill contracts](20260815-strengthen-workflow-skill-contracts.md)
plan deliberately rejected OpenSpec delta machinery to preserve IWE's graph,
single-plan-document workflow, and agent-driven spec merge. The subsequent
exploration separated two ideas that decision had grouped together: OpenSpec's
change bundles and programmatic patch engine remain unnecessary, but a
risk-scaled behavioral delta inside the existing plan can make intent reviewable
before implementation and give Verify a coherent pre-ship contract.

This plan adopts only that representation. It does not make spec application
deterministic: Ship still performs an intelligent merge from a zero-CRITICAL
Verify report, and any disagreement among plan delta, implementation evidence,
and durable spec blocks shipping rather than being guessed through.

Assumption recorded from the preceding exploration: structured deltas are
conditional, not mandatory for every plan. No-behavior plans continue to say so
explicitly; simple low-risk behavior may use a concise normative outcome;
contract-heavy or risky behavior uses complete requirement blocks.

## Approach

Keep `## Spec changes` as the one IWE-native home for spec impact and give it
three risk-scaled forms:

1. **No behavioral change** — retain the explicit `None — no behavioral change`
   form.
2. **Simple, low-risk behavior** — link the affected durable spec and state the
   intended post-change outcome concisely with normative language.
3. **Contract-heavy or risky behavior** — link the affected spec and embed a
   fenced Markdown delta using `ADDED`, `MODIFIED`, and `REMOVED Requirements`.
   `ADDED` and `MODIFIED` carry complete post-change requirement blocks with
   their surviving scenarios; `REMOVED` identifies the requirement and why its
   behavior is intentionally retired.

The delta is the active plan's intended contract, not a second durable truth.
Plan creates or revises it; Implement must pause when implementation would
materially change it; Verify evaluates code against the effective contract
formed by the current durable spec plus the plan delta; Ship merges the verified
result into the durable spec and leaves the completed plan as history.

The fenced form preserves canonical Requirement/Scenario heading levels while
keeping the delta structurally inside the plan's existing `## Spec changes`
section. It also avoids adding a new document type, schema binding, directory,
or skill. Requirement-only renames are represented explicitly as removal plus
addition in this first version rather than adding a fourth operation whose
identity semantics would imply a parser.

Rejected alternatives:

- **Require a full delta for every plan.** This conflicts with IWE's existing
  progressive-rigor rule and adds ceremony to refactors and small internal
  changes.
- **Create separate delta-spec documents or change bundles.** That duplicates
  the plan lifecycle and weakens the graph's existing ownership boundaries.
- **Claim deterministic application from prompt wording.** Determinism would
  require a parser, conflict rules, a fixed application order, and executable
  postconditions. This plan adds none of those.
- **Derive the durable spec silently from implementation when the delta is
  stale.** That erases the reviewed contract. A material mismatch instead
  returns to Plan revision.

## Implementation Steps

### Task 1: Rebase the prompt contract after its active dependencies

**Files:** No file changes (analysis only)

- [x] **1. Re-read and re-anchor the workflow after both dependency plans
  ship.** Capture the then-current Plan, Implement, Verify, and Ship prompts;
  refresh every affected line reference below before editing; and confirm the
  checkbox-evidence and unchecked-task routing changes remain intact. Record a
  scenario-to-owner checklist so each new rule has exactly one primary owner and
  cross-skill handoffs do not duplicate it.
  - **Evidence:** both dependencies verified `stage: done` /
    `completed: 2026-08-16`; all four prompts re-read at that state; three moved
    anchors refreshed under `## Key references`
    (`plan/SKILL.md:99-102`→`111-114`, `implement/SKILL.md:20-45`→`20-50`,
    `verify/SKILL.md:20-40`→`23-43`), seven re-confirmed unchanged; the ten-row
    scenario-to-owner checklist and the intactness check for the evidence and
    unchecked-task-routing contracts are recorded under
    `## Verification results`. `iwe normalize` left the fenced `## Spec changes`
    delta byte-identical (`git diff` touches only the two edited sections);
    `iwe schema validate` and
    `uv run validate_agent_files --kind skills .claude/skills --ci` both exit 0.

### Task 2: Make Plan author risk-scaled spec contracts

**Files:** Modify: `.claude/skills/plan/SKILL.md`

- [x] **2. Define the three `## Spec changes` forms and their selection
  threshold.** Preserve the explicit no-behavior form; require a linked spec
  plus concise normative outcome for simple low-risk behavior; and require the
  fenced `ADDED` / `MODIFIED` / `REMOVED Requirements` form for changes whose
  compatibility, acceptance criteria, security/privacy/data-loss consequences,
  or scenario set make a prose summary ambiguous. Require complete post-change
  blocks under `ADDED` and `MODIFIED`, including every surviving scenario, and a
  reason under `REMOVED`. Keep future spec keys back-ticked until Ship creates
  them.
  - **Evidence:** `.claude/skills/plan/SKILL.md:107-143` adds
    `## The three forms of ## Spec changes` — form 1 keeps
    `None — no behavioral change`, form 2 requires a linked spec plus a concise
    normative outcome, form 3 requires the fenced delta and names the
    compatibility / acceptance-criteria / security-privacy-data-loss /
    scenario-set threshold; `ADDED` and `MODIFIED` are required to carry every
    surviving scenario, `REMOVED` a retirement reason, with `RENAMED` explicitly
    excluded and future spec keys kept back-ticked until Ship. `:62-64` routes
    the body contract to those forms and `:157-160` makes an under-scaled form a
    Verify CRITICAL.
    `uv run validate_agent_files --kind skills .claude/skills --ci` exits 0.
- [x] **3. Reconcile deltas during Plan revision.** Extend the existing
  bidirectional coherence pass so a decision affecting behavior updates the
  delta, tasks, verification, and out-of-scope boundaries together. State that
  the delta describes intended behavior while the durable spec remains current
  truth until Ship succeeds.
  - **Evidence:** `.claude/skills/plan/SKILL.md:76-86` extends the revise-mode
    reconciliation pass — a behavior-changing decision moves `## Spec changes`
    in the same pass, may escalate its form, and carries the dependent tasks,
    verification, and out-of-scope boundaries with it; it names the split it
    prevents (a delta edited alone or left on old intent) and states that the
    revision updates intent while the durable spec keeps describing released
    behavior until Ship succeeds. The same intent-versus-truth boundary opens
    the forms section at `:107-112`, so the two statements agree.
    `uv run validate_agent_files --kind skills .claude/skills --ci` exits 0.

### Task 3: Bind implementation and verification to the effective contract

**Files:** Modify: `.claude/skills/implement/SKILL.md`,
`.claude/skills/verify/SKILL.md`

- [x] **4. Make Implement preserve or escalate the delta.** Load the selected
  plan's chosen spec-impact form with the current durable specs. Tactical
  corrections may continue only when they preserve the recorded behavioral
  outcome; any change to a normative outcome, operation, requirement, or
  scenario is a material deviation requiring user direction and Plan revision
  before coding continues.
  - **Evidence:** `.claude/skills/implement/SKILL.md:20-28` loads the plan's
    chosen form — `None`, concise normative outcome, or fenced
    `ADDED`/`MODIFIED`/`REMOVED` delta — against the current durable spec, and
    states which of the two binds when they differ. `:49-55` limits tactical
    corrections to those leaving the recorded outcome exactly as written, and
    `:56-63` makes any change to a normative outcome, delta operation,
    requirement, or scenario material by definition, forbids editing the delta
    to match what was built, and routes it through Plan revise mode with user
    direction. `uv run validate_agent_files --kind skills .claude/skills --ci`
    exits 0.
- [x] **5. Make Verify evaluate the effective pre-ship contract.** Replace the
  requirement that durable specs already reflect the unshipped change. For a
  structured delta, compare implementation evidence with the current durable
  spec plus the delta; for a concise low-risk entry, compare against its
  normative outcome; for `None`, confirm no observable behavior changed. Keep a
  missing durable spec valid only when the plan explicitly introduces it and
  supplies the required planned contract. Report a CRITICAL when the selected
  form is too weak for the risk, the implementation contradicts the delta, or
  the delta would silently discard an unaffected scenario.
  - **Evidence:** `.claude/skills/verify/SKILL.md:39-52` replaces the "spec
    exists and reflects the change" check with the effective contract (current
    durable spec plus the plan's recorded intent). A back-ticked not-yet-created
    spec is now valid when the plan introduces it and supplies its planned
    contract; the per-form checks cover fenced delta, concise normative outcome,
    and `None`; and the three named CRITICALs are an under-scaled form, an
    implementation contradicting recorded intent, and a delta silently dropping
    an unaffected scenario. Requirement-evidence search now runs over the
    effective contract rather than the durable spec alone.
    `uv run validate_agent_files --kind skills .claude/skills --ci` exits 0.

### Task 4: Make Ship consume deltas without pretending to compile them

**Files:** Modify: `.claude/skills/ship/SKILL.md`

- [x] **6. Use the plan-local delta as reviewed intent and Verify as the
  evidence gate.** During intelligent merge, preserve the existing read-before-
  write and restart-safe rules, apply only behavior supported by the
  zero-CRITICAL report, and stop for Plan revision when the delta and verified
  implementation disagree. Do not silently rewrite the delta from code or
  present the merge as programmatic/deterministic.
  - **Evidence:** `.claude/skills/ship/SKILL.md:42-50` names the recorded form
    as reviewed intent and the zero-CRITICAL report as the evidence it was
    built, merges only what both support, and forbids describing or performing
    the merge as a parser, fixed operation order, or mechanical conflict
    resolution. `:55-58` stops on intent/evidence disagreement with no lifecycle
    transition and no rewriting intent from code; `:127-130` repeats that as a
    rule. The existing read-before-write and restart-safe rules are untouched
    (`:51-53`, `:79`, `:131-133`, and the preamble at `:10-12`).
    `uv run validate_agent_files --kind skills .claude/skills --ci` exits 0.
- [x] **7. Verify the delta is fully represented before lifecycle changes.** In
  addition to re-reading every touched durable spec, compare the result with
  every operation and post-change requirement/scenario in the plan. Preserve
  unaffected content, reject a partial merge, and retain the existing
  graph-aware whole-spec retirement rules.
  - **Evidence:** `.claude/skills/ship/SKILL.md:66-78` adds a second pass over
    the recorded intent that must account for every `ADDED`/`MODIFIED`/
    `REMOVED` operation, post-change requirement, scenario, and concise
    normative outcome; states that a mostly-landed merge is a failed merge and
    an unfound operation is a mismatch to report; and requires confirming that
    content the delta never mentioned survived untouched. The graph-aware
    whole-spec retirement rule using `iwe delete` is retained unchanged at
    `:62-65`. `uv run validate_agent_files --kind skills .claude/skills --ci`
    exits 0.

### Task 5: Reconcile the operating documentation

**Files:** Modify: `docs/knowledge/AGENTS.md`, `docs/knowledge/STRUCTURE.md`,
`docs/knowledge/README.md`

- [x] **8. Document the risk-scaled plan-local contract.** Update the operating
  manual's planning and spec conventions, revise Structure's statement that
  delta headers are deliberately not adopted, and extend the OpenSpec
  acknowledgment only as needed. Keep the distinctions explicit: one plan
  document, no separate change bundle, durable specs update only during Ship,
  and no deterministic application engine.
  - **Evidence:** `docs/knowledge/AGENTS.md:115-125` adds the three forms to the
    conventions, names Plan as owner of the threshold, and states
    intent-versus-truth plus the four exclusions; `:40-42` routes plan creation
    to the risk-appropriate form. `docs/knowledge/STRUCTURE.md:73-82` adds "Spec
    impact scales with risk"; `:128-134` moves delta headers into *adopted* as a
    representation; `:147-153` replaces the old blanket rejection with a
    rejection of the *application engine* specifically (no parser, order,
    conflict rules, or postconditions) and explains why there is no `RENAMED`.
    `docs/knowledge/README.md:107-111` extends the OpenSpec acknowledgment to
    the notation while disclaiming change bundles and programmatic application.
    `iwe normalize` then `iwe schema validate` exit 0.

### Task 6: Validate the complete workflow

**Files:** No file changes (validation only)

- [x] **9. Validate prompts and project memory.** Run
  `uv run validate_agent_files --kind skills .claude/skills --ci`, then
  `iwe normalize` and `iwe schema validate`; resolve every introduced error and
  inspect normalization to confirm fenced deltas remain byte-stable.
  - **Evidence:** all three commands exit 0 at `9cfee7a` (`validate_agent_files`
    0, `iwe normalize` 0, `iwe schema validate` 0), and no error or warning was
    introduced. Byte stability checked by copying the plan to
    `.tmp/delta-before.md`, re-running `iwe normalize`, and diffing: identical.
    The fenced delta specifically survives header-level normalization — 115
    lines, `## ADDED Requirements` and `## MODIFIED Requirements` still at H2
    inside the fence, three `### Requirement:` blocks and all 13
    `#### Scenario:` blocks intact. `git diff --exit-code` after normalize is
    clean, so the validate-knowledge-base.yml no-op gate passes.
- [x] **10. Perform scenario read-back.** Confirm the four skills agree on all
  three risk forms; Verify no longer requires an unshipped durable spec to
  contain future behavior; Ship stops on delta/evidence disagreement; Setup and
  Weekly remain unchanged; and no OpenSpec store, change directory, archive
  move, or separate delta document entered the IWE workflow.
  - **Evidence:** all five claims checked against the tree, not asserted. (a)
    All four skills carry all three forms — Plan `plan/SKILL.md:107-143`,
    Implement `:20-28`, Verify `:39-52`, Ship `:42-50`; the "normative outcome"
    wording was aligned in Plan `:116-119` during this read-back so the four
    share one vocabulary. (b) Verify's old "spec exists and reflects the change"
    / "not-yet-created spec still pending is a CRITICAL" text is absent (grep
    returns nothing), replaced by the effective-contract check. (c) Ship stops
    on disagreement at `ship/SKILL.md:54` and `:76`, with the rule at
    `:127-130`. (d)
    `git diff --quiet 4f0f3ad..HEAD -- .claude/skills/setup .claude/skills/weekly`
    reports no changes. (e) The branch touches nine files — the four skills,
    three knowledge docs, this plan, and `docs/knowledge/.markdownlint.yml`; the
    only file added is that lint config. No store, change directory, archive
    move, separate delta document, parser, or schema type appears, and
    `.iwe/config.toml` is untouched; the sole diff hit for "change bundle" is a
    disclaimer.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — add the risk-scaled
plan-local contract and revise Ship and model-preservation behavior as follows:

``` markdown
## ADDED Requirements

### Requirement: Plans express spec impact at risk-appropriate fidelity

The Plan skill SHALL record the intended spec impact in the plan's existing
`## Spec changes` section, SHALL scale detail with behavioral risk, and SHALL
keep that contract coherent when material decisions change.

#### Scenario: A plan has no behavioral change

- **WHEN** planned work changes no externally observable behavior
- **THEN** Plan records `None — no behavioral change` rather than inventing a
  spec delta

#### Scenario: A simple low-risk behavior changes

- **WHEN** one unambiguous low-risk behavior changes and a full scenario delta
  would add ceremony without resolving uncertainty
- **THEN** Plan links the affected durable spec and records a concise normative
  post-change outcome

#### Scenario: Contract-heavy or risky behavior changes

- **WHEN** a change affects compatibility, acceptance criteria,
  security/privacy/data-loss behavior, or a requirement's scenario set
- **THEN** Plan embeds complete ADDED, MODIFIED, or REMOVED requirement content
  for every affected durable spec

#### Scenario: Implementation would contradict the planned contract

- **WHEN** implementation requires a material change to a recorded normative
  outcome, delta operation, requirement, or scenario
- **THEN** Implement leaves the current task unchecked and waits for user
  direction and Plan revision before coding through the change

#### Scenario: Verify runs before durable spec synchronization

- **WHEN** implementation is ready for pre-ship verification while the durable
  spec still describes current released behavior
- **THEN** Verify evaluates the implementation against the effective contract
  formed by the durable spec and the plan's risk-appropriate spec changes

## MODIFIED Requirements

### Requirement: Ship synchronizes durable specs by intelligent merge

The Ship skill SHALL treat a plan-local spec delta as reviewed intent, SHALL
derive durable updates only from intent that agrees with verified shipped
behavior, SHALL preserve unaffected requirements and scenarios, SHALL complete
and verify all required spec updates before marking work done, and SHALL be safe
to resume after a partial prior attempt.

#### Scenario: Existing behavior remains unaffected

- **WHEN** a shipped change modifies one requirement or scenario in an existing
  durable spec
- **THEN** Ship updates the changed behavior while preserving all unaffected
  requirements, scenarios, ordering, and still-accurate explanatory content

#### Scenario: A structured delta agrees with implementation

- **WHEN** Verify confirms that every planned delta operation and post-change
  scenario agrees with implementation evidence
- **THEN** Ship intelligently merges that behavior into the durable spec and
  verifies the complete resulting contract

#### Scenario: Plan intent and implementation disagree

- **WHEN** a normative outcome or structured delta disagrees with the verified
  implementation
- **THEN** Ship makes no lifecycle transition, does not rewrite intent from
  code, and reports that the plan requires revision

#### Scenario: A spec update cannot be validated

- **WHEN** any planned spec update is incomplete, disagrees with the verified
  implementation, or fails graph validation
- **THEN** Ship does not mark the plan or related feature or bug complete and
  reports the mismatch

#### Scenario: Shipping resumes after partial graph updates

- **WHEN** a prior Ship attempt already performed some valid state changes
- **THEN** Ship inspects current state, preserves completed valid work, avoids
  duplicate hub, release, and log entries, and continues from the first
  incomplete operation

#### Scenario: A durable spec is retired

- **WHEN** the verified implementation and plan explicitly remove the final
  behavior represented by a durable spec
- **THEN** Ship uses IWE's graph-aware deletion operation, repairs references,
  and does not leave an empty or orphaned spec document

### Requirement: Workflow improvements preserve the IWE and OKF model

The strengthened skills SHALL continue to use IWE's single-plan-document
workflow, graph links, durable specs, existing stage and status conventions,
provenance requirements, and schema validation. Risk-scaled spec deltas SHALL
remain embedded planning content without introducing OpenSpec change bundles,
stores, separate delta files, archive moves, or a claimed programmatic delta
application engine.

#### Scenario: Updated skills write project memory

- **WHEN** an updated skill creates or meaningfully changes an IWE document
- **THEN** it follows the existing OKF metadata, graph membership,
  normalization, validation, and commit requirements defined by the workspace

#### Scenario: Unaffected skills are exercised

- **WHEN** Setup or Weekly runs after this change
- **THEN** its existing behavior remains unchanged
```

## Depends on

[Make plan checkboxes carry their evidence](20260815-honest-plan-checkboxes.md)
— it changes Plan, Implement, Verify, and the operating manual, so this plan
must re-anchor and preserve its evidence contract rather than editing across it.

[Name the missing handoff routes in explore and verify](20260816-skill-handoff-routes.md)
— it changes Verify's unchecked-task routing and must land before this plan
rewrites the surrounding pre-ship contract.

## Verification

- `uv run validate_agent_files --kind skills .claude/skills --ci` passes with no
  introduced error or warning.
- `iwe normalize` followed by `iwe schema validate` exits 0, and a before/after
  comparison confirms fenced Markdown deltas are preserved.
- A no-behavior plan remains valid with an explicit `None` entry and is not
  forced to invent requirements.
- A simple low-risk behavior plan carries a linked spec and concise normative
  outcome without a full scenario block.
- A contract-heavy fixture plan carries complete `ADDED`, `MODIFIED`, and
  `REMOVED` blocks; Plan revision reconciles them with tasks and verification.
- Verify checks an unshipped implementation against the effective durable-spec
  plus plan-delta contract and does not require future behavior to have already
  been synced.
- Ship refuses a deliberately introduced delta/evidence mismatch, and a matching
  case merges without losing an unaffected requirement or scenario.
- Setup and Weekly remain unchanged; repository diff contains no new change
  bundle, separate delta file, store, archive move, parser, or schema type.

## Verification results

**Task 1 — rebase and scenario-to-owner checklist (2026-08-16).** Both
dependency plans carry `stage: done` / `completed: 2026-08-16`. The prompts were
re-read at that state; the checkbox-evidence contract is intact
(`.claude/skills/plan/SKILL.md:57-61` and `:68-70`,
`.claude/skills/implement/SKILL.md:30-39` and `:66-71`,
`.claude/skills/verify/SKILL.md:31-38`, `docs/knowledge/AGENTS.md:117-121`), and
Verify's unchecked-task routing with its three named routes is intact
(`.claude/skills/verify/SKILL.md:25-31`). Three anchors had moved and were
refreshed under `## Key references`; the other seven still resolve.

Each new rule gets exactly one primary owner; the other skills reference it
rather than restating it:

- **Three `## Spec changes` forms and their selection threshold** → Plan (task
  2). Other skills refer to "the plan's chosen spec-impact form" and never
  restate the threshold.
- **No behavioral change means an explicit `None` entry** → Plan (task 2).
  Verify only confirms no observable behavior changed (task 5).
- **Delta coherence during revision** → Plan (task 3). Implement routes material
  changes back to Plan revision (task 4) rather than reconciling them itself.
- **A material contradiction pauses coding** → Implement (task 4). No other
  skill owns the pause.
- **Effective contract = current durable spec + plan delta** → Verify (task 5).
  Ship consumes Verify's verdict and does not re-derive it (task 6).
- **A missing durable spec is valid before Ship** → Verify (task 5). Ship still
  owns creating that spec at merge time (existing step 4).
- **Delta/evidence disagreement blocks the merge** → Ship (task 6). Verify
  reports the contradiction as a CRITICAL; only Ship refuses the transition.
- **Full delta representation checked before lifecycle flips** → Ship (task 7).
- **Durable specs mutate only during Ship** → Ship (existing rule). Plan,
  Implement, and Verify never write durable specs.
- **The OpenSpec boundary and its rationale** → `docs/knowledge/STRUCTURE.md`
  (task 8). `AGENTS.md` and `README.md` summarize it; the skill prompts do not
  carry the rationale.

## Out of scope

- A programmatic delta parser, fixed application order, conflict engine, or
  deterministic merge claim.
- Separate per-change directories, stores, delta-spec documents, archive moves,
  or new IWE skills.
- Mandatory full deltas for refactors, tooling/docs-only work, or every low-risk
  behavior change.
- A `RENAMED Requirements` operation; requirement-only renames use explicit
  removal plus addition until executable identity semantics are justified.
- Synchronizing durable specs before Ship or weakening the zero-CRITICAL Verify
  gate.
- Editing or deleting the untracked `.agents/skills/` runtime copies currently
  present in this working tree. While this plan was active the tracked workspace
  source was `.claude/skills/`; that boundary held only for this plan's
  lifetime, and
  [Move the IWE workflow skills into the agentdev plugin](20260816-move-iwe-skills-to-agentdev.md)
  superseded it by relocating the seven skills to
  `.agents/plugins/agentdev/skills/iwe-*/`.

## Key references

Verified anchor points (line numbers as of 2026-08-16, refreshed by Task 1 after
both dependency plans shipped):

- `.claude/skills/plan/SKILL.md:52-67` — plan body contract, including the
  current name-only `## Spec changes` rule
- `.claude/skills/plan/SKILL.md:111-114` — mandatory spec-impact thinking and
  progressive-rigor rules
- `.claude/skills/implement/SKILL.md:20-50` — spec loading and tactical versus
  material deviation handling
- `.claude/skills/verify/SKILL.md:23-43` — the current pre-ship checks,
  including the requirement that durable specs already reflect the change
- `.claude/skills/ship/SKILL.md:42-60` — intelligent merge and post-merge
  verification before lifecycle transitions
- `docs/knowledge/AGENTS.md:40-53` — plan creation and spec-at-ship operating
  loop
- `docs/knowledge/AGENTS.md:109-113` — durable-spec format and progressive rigor
- `docs/knowledge/STRUCTURE.md:67-70` — current name-only spec-sync design
- `docs/knowledge/STRUCTURE.md:102-130` — OpenSpec influences and the explicit
  rejection of delta headers
- `docs/knowledge/data/spec/iwe-workflow-skills.md:148-199` — intelligent Ship
  merge and the current prohibition on delta-spec machinery
