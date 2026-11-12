---
type: plan
created: 2026-11-09
stage: done
completed: 2026-11-09
release:
- features/risk-scaled-spec-deltas
description: Make the planner read every spec its Spec changes touch in full, reference a rule's existing home instead of restating it, and drop a scenario a MODIFIED requirement leaves restating its requirement.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: docs/knowledge/data/spec/iwe-workflow-skills.md
---

# Stop the planner from adding spec redundancy

## Context

[Stop the planner from adding spec
redundancy](../backlog/planner-spec-redundancy-check.md) records the gap. A spec
is the second copy of the behaviour its code or rulebook carries; that
duplication is intended. Redundancy inside a spec is a different thing: one rule
restated across several requirements, or a scenario that only restates its own
requirement. Ship preserves every requirement and scenario a plan's
`## Spec changes` does not touch, so only the planner can keep redundancy out.
Its rulebook makes a `MODIFIED` requirement carry every surviving scenario, and
nothing in it checks whether a planned rule already lives in another requirement
of the same spec.

The change alters what [Risk-scaled spec
deltas](../../1.0.0/features/risk-scaled-spec-deltas.md) does for every
repository that installs the catalog. [Remove redundancy from the durable
specs](../backlog/deduplicate-spec-requirements.md) cleans up the redundancy
already in the specs, and depends on this plan so the cleaned specs stay clean.

## Approach

`iwe-planner.agent.md#the-three-forms-of--spec-changes` gains one rule for the
normative-outcome and fenced-delta forms. Before validation the planner reads
every durable spec the section touches in full, and a normative outcome or an
`ADDED` or `MODIFIED` requirement that would restate a rule another requirement
of that spec already holds names that requirement instead. The `MODIFIED` bullet
gains one exception to "every surviving scenario": a scenario that added a case
before this change and adds none after it is left out and named below the fence
as a deliberate removal. A scenario that already restated its requirement before
the change stays; the cleanup task owns it.

Rejected: having Verify or `iwe-revision-evaluator` flag a restated rule. The
planner writes the delta, so the check belongs where the delta is written, and a
Verify finding would arrive after the plan is already implemented.

## Implementation Steps

### Task 1: The planner keeps each spec rule in one requirement

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [x] `## The three forms of ## Spec changes` holds the rule that the planner
  reads every durable spec the section touches in full before validation, and
  that a normative outcome or an `ADDED` or `MODIFIED` requirement names an
  existing requirement of that spec instead of restating its rule.
  - **Evidence:** commit 76b68747 adds the paragraph "Each rule of a spec lives
    in one requirement" to
    `iwe-planner.agent.md#the-three-forms-of--spec-changes`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passed, 0 errors.
- [x] The `MODIFIED` bullet leaves out a scenario that added a case before the
  change and adds none after it, and requires naming it below the fence as a
  deliberate removal.
  - **Evidence:** commit 76b68747 adds "The one exception" to the `MODIFIED`
    bullet of `iwe-planner.agent.md#the-three-forms-of--spec-changes`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passed, 0 errors.

### Task 2: A revise with a redundant delta drops the redundancy

**Closed by:** the repository owner, after merge.

- [x] A scratch `/agentdev:iwe-plan` revise of an active plan, asked for a
  `## Spec changes` delta that restates a rule another requirement of the same
  spec holds and that leaves a scenario restating its requirement, produces a
  delta that references the existing requirement, leaves that scenario out, and
  names it below the fence. The revise is not committed.
  - **Evidence:** a headless `claude -p` run of the `/agentdev:iwe-plan` revise
    of `data/plans/20261109-one-observation-per-checkbox`, on a detached
    checkout of commit d8195541, asked for a SHALL sentence restating the
    evidence-line rule and one settling the scenario "A task's evidence is
    external". The uncommitted result names "A ticked task carries the evidence
    that closed it" instead of restating it, leaves that scenario out, and names
    it below the fence as "Removed scenario".

## Spec changes

[IWE workflow skills](../../../spec/iwe-workflow-skills.md) — Plan keeps each
rule of a touched spec in one requirement.

``` markdown
## MODIFIED Requirements

### Requirement: Plans express spec impact at risk-appropriate fidelity

The Plan skill SHALL record the intended spec impact in the plan's existing
`## Spec changes` section, SHALL scale detail with behavioral risk, and SHALL
keep that contract coherent when material decisions change. Plan SHALL keep each
rule of a durable spec in one requirement: before validation it SHALL read in
full every durable spec its normative outcome or structured delta touches.

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

#### Scenario: A planned rule already has a home

- **WHEN** a plan's normative outcome or an ADDED or MODIFIED requirement would
  state a rule another requirement of the same spec already holds
- **THEN** Plan names that requirement instead of restating the rule

#### Scenario: A modification makes a scenario redundant

- **WHEN** a MODIFIED requirement's post-change statement settles everything one
  of its scenarios says, and that scenario added a case before the change
- **THEN** Plan leaves the scenario out of the block and names it below the
  fence as a deliberate removal, while a scenario that already restated its
  requirement before the change stays
```

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- `iwe normalize` and `iwe schema validate` pass.
- `uv run scripts/check-anchors.py` passes.

## Out of scope

- Removing redundancy already in the specs: [Remove redundancy from the durable
  specs](../backlog/deduplicate-spec-requirements.md).
- Verify, Ship, or `iwe-revision-evaluator` checking for a restated rule.
- Statements of how the catalog is wired, which keep their copy in the spec.

## Key references

- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#the-three-forms-of--spec-changes`
  — the forms and the `MODIFIED` "every surviving scenario" rule this plan
  amends.
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps` › "Merge every
  planned durable spec" — Ship merges only what the plan states, so the planner
  is the only place the check can live.
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-plans-express-spec-impact-at-risk-appropriate-fidelity`
  — the requirement the delta modifies.
