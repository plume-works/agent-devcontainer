---
type: spec
description: Behavioral contracts and handoffs for IWE's Explore, Plan, Implement, Verify, and Ship skills.
generated:
  by: codex
  at: 2026-08-16T00:40:24Z
sources:
- resource: .claude/skills/explore/SKILL.md
- resource: .claude/skills/plan/SKILL.md
- resource: .claude/skills/implement/SKILL.md
- resource: .claude/skills/verify/SKILL.md
- resource: .claude/skills/ship/SKILL.md
---

# IWE workflow skills

## Purpose

Defines reliable, phase-aware behavior for the IWE skills that guide work from
open-ended exploration through planning, implementation, verification, and
durable shipping state.

## Requirements

### Requirement: Explore remains an adaptive thinking mode

The Explore skill SHALL investigate the project graph and codebase without
editing application code, SHALL remain adaptive and patient as the problem takes
shape, and SHALL offer capture or a phase handoff without pressuring the user to
formalize unfinished thinking.

#### Scenario: Exploration starts from an open-ended idea

- **WHEN** the user asks to explore an idea without committing to implementation
- **THEN** Explore follows relevant questions and tradeoffs, grounds claims in
  current project evidence, and ends with the current understanding and an
  optional next step

#### Scenario: Exploration starts during implementation

- **WHEN** the user invokes Explore because an active implementation task
  exposed a complication
- **THEN** Explore reads the active plan and task, investigates without editing
  code, and hands any resulting decision, scope change, or new work back to the
  skill that owns plan execution

### Requirement: Plan creates or revises planning state without implementing

The Plan skill SHALL treat its invocation as authorization to write planning
state only, SHALL resolve material ambiguity before committing the plan, and
SHALL keep a created or revised plan coherent across context, approach, tasks,
spec impact, dependencies, verification, out-of-scope boundaries, and current
code anchors.

#### Scenario: A planning request also asks to build the change

- **WHEN** a request invokes Plan while also asking for implementation
- **THEN** Plan creates and validates the planning state, reports readiness, and
  stops before editing implementation code

#### Scenario: Ambiguity would alter observable behavior

- **WHEN** an unresolved choice would materially affect scope, externally
  observable behavior, compatibility, or acceptance criteria
- **THEN** Plan asks for direction before committing that choice

#### Scenario: Only a minor detail is unspecified

- **WHEN** an unspecified detail does not materially affect scope, behavior,
  compatibility, or acceptance criteria
- **THEN** Plan makes a reasonable assumption and records it in the plan

#### Scenario: An active plan is revised

- **WHEN** the user requests a specific revision to an existing active plan
- **THEN** Plan reconciles every affected section in either direction,
  re-verifies any affected code anchors, validates the graph, and reports
  implementation that may now be stale

#### Scenario: A revision changes the work's intent

- **WHEN** a proposed revision creates a different topic or materially different
  verification story
- **THEN** Plan recommends distinct work instead of silently replacing the
  existing plan's intent

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

### Requirement: Implement never hides a material deviation

The Implement skill SHALL distinguish intent-preserving task corrections from
material changes, SHALL pause before narrowing or extending specified behavior
without authority, and SHALL mark a task complete only when its full specified
behavior has passing evidence.

#### Scenario: A tactical correction preserves intent

- **WHEN** implementation reveals a stale anchor or task breakdown that can be
  corrected without changing scope, observable behavior, compatibility,
  acceptance criteria, or dependencies
- **THEN** Implement updates the plan, reports the correction, and may continue
  within the user's requested task boundary

#### Scenario: Completing a task requires a material change

- **WHEN** implementation would need to add scope or drop, narrow, defer, or
  accept an exception to specified behavior
- **THEN** Implement leaves the task unchecked, explains the material deviation,
  and waits for user direction before coding past it

#### Scenario: Work is partial or its evidence fails

- **WHEN** a task is only partially implemented, contains deferred behavior, or
  its required tests or checks do not pass
- **THEN** Implement leaves the task unchecked and reports the remaining work or
  failing evidence

### Requirement: Normal shipping requires a clean independent verification

The Ship skill SHALL run the report-only Verify workflow before normal shipping
state changes and SHALL refuse to ship while Verify reports any CRITICAL
finding. Verify SHALL remain independently invocable and SHALL not edit code or
project state.

#### Scenario: Verification reports no critical findings

- **WHEN** Ship invokes Verify for a completed plan and Verify returns zero
  CRITICAL findings
- **THEN** Ship may proceed to spec synchronization and later durable state
  transitions

#### Scenario: Verification reports a critical finding

- **WHEN** Ship invokes Verify and Verify reports one or more CRITICAL findings
- **THEN** Ship makes no shipping state transition and reports the blockers

#### Scenario: A plan is cancelled rather than shipped

- **WHEN** the user explicitly cancels an active plan
- **THEN** Ship records cancellation without requiring implementation
  verification or spec synchronization and performs no release or
  implemented-feature transition

#### Scenario: Verify is invoked outside Ship

- **WHEN** the user requests a mid-implementation check or a workspace audit
- **THEN** Verify produces its evidence-backed report and stops without invoking
  Ship or mutating the graph

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
