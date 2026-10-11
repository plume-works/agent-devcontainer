---
type: spec
description: Behavioral contracts and handoffs for IWE's Explore, Capture, Plan, Map, Implement, Verify, and Ship skills.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-10T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-capture/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-capture/agent-code/close-issue.sh
- resource: .iwe/schemas/bug.yaml
- resource: .iwe/schemas/feature.yaml
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-explore/agent-code/fetch-issue.sh
- resource: .agents/plugins/agentdev/skills/iwe-plan/agent-code/close-issue.sh
- resource: .agents/plugins/agentdev/skills/iwe-map/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py
- resource: .agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.sh
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-new-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
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
formalize unfinished thinking. When the user approves specific text, Explore
SHALL persist it verbatim outside the conversation and reproduce it verbatim in
the handoff, and SHALL never paraphrase it.

#### Scenario: Exploration starts from an open-ended idea

- **WHEN** the user asks to explore an idea without committing to implementation
- **THEN** Explore follows relevant questions and tradeoffs, grounds claims in
  current project evidence, and ends with the current understanding and an
  optional next step

#### Scenario: Exploration starts from a GitHub issue

- **WHEN** the user invokes Explore with an issue URL, an `OWNER/REPO#N`
  reference, or an issue number
- **THEN** Explore reads the issue and all of its comments into `./.tmp/` before
  investigating, verifies the issue's claims against the code and the graph
  rather than adopting them, never edits the issue, and carries the issue URL
  into any handoff to Plan

#### Scenario: Exploration starts during implementation

- **WHEN** the user invokes Explore because an active implementation task
  exposed a complication
- **THEN** Explore reads the active plan and task, investigates without editing
  code, and hands any resulting decision, scope change, or new work back to the
  skill that owns plan execution

#### Scenario: The user approves specific wording

- **WHEN** the user agrees to specific text — wording for a document, a snippet,
  a message — that a later plan or edit will apply
- **THEN** Explore writes it verbatim to `.tmp/approved-wording-<slug>.md`
  before continuing, names that file in the handoff, and reproduces the text
  verbatim rather than describing it

### Requirement: Plan creates or revises planning state without implementing

The Plan skill SHALL treat its invocation as authorization to write planning
state only, SHALL resolve material ambiguity before committing the plan, and
SHALL keep a created or revised plan coherent across context, approach, tasks,
spec impact, dependencies, verification, out-of-scope boundaries, and current
code anchors. When a decision was made as specific text, Plan SHALL reproduce
that text verbatim in the task that applies it and SHALL never paraphrase it.

#### Scenario: A plan grows from a GitHub issue

- **WHEN** Plan creates a plan for work that arrived as a GitHub issue
- **THEN** the plan links the issue URL in `## Context` and under `sources:`,
  and after the plan validates, Plan closes the issue with a comment naming the
  plan path, so the issue and the plan reference each other and the issue no
  longer competes with the plan as the open record of the work

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

#### Scenario: A task applies text the user already approved

- **WHEN** a plan task would apply wording, a snippet, or a message that the
  user has already agreed to
- **THEN** Plan reproduces that text verbatim in a fenced block under the task,
  consulting `.tmp/approved-wording-<slug>.md` rather than writing it from
  memory, so a session holding only the plan can reproduce the approved bytes

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

### Requirement: Implement starts work on its own branch

The Implement skill SHALL, when the checkout is on `main` or `master`, create
the work branch through the git-new-branch skill, named from the plan key's
slug, before executing the first task, and SHALL continue on the current branch
otherwise.

#### Scenario: Implementation starts on main

- **WHEN** Implement begins plan `data/plans/<date>-<slug>` with `main` checked
  out
- **THEN** it creates branch `<slug>` through git-new-branch before executing
  any task

#### Scenario: Implementation starts on a feature branch

- **WHEN** Implement begins with a branch other than `main` or `master` checked
  out
- **THEN** it executes the plan on that branch without creating another

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

### Requirement: Plans record intent, not the path taken to it

Plan documents SHALL record what is settled rather than the sequence of attempts
that settled it. `## Verification results` SHALL be a plan's only narrative
section. Implement SHALL route a finding that does not change the plan's intent
to its own document — `data/architecture/`, `data/bugs/`, or `data/backlog/` —
rather than into the plan's `## Context` or `## Approach`, which state intent
and remain the Plan skill's to own. Every edit to a plan's intent sections SHALL
be audited for durable-knowledge residue by a reviewer holding no context beyond
the audit scope and the plan file, before the edit is validated.

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

#### Scenario: A plan edit is audited before validation

- **WHEN** Plan creates or revises a plan and reaches validation
- **THEN** a reviewer holding only the audit scope and the plan file audits its
  intent sections for durable-knowledge residue, its verdicts are applied, and
  the narrative-sanctioned `## Verification results` and `- **Evidence:**`
  children are left out of that audit

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

### Requirement: Ship and Implement start only from an explicit request or a named dispatcher

The Ship and Implement workflows SHALL each be defined once, as the catalog
agents `iwe-shipper` and `iwe-implementer`. Their user entry skills and the
`iwe-ship-all` and `iwe-implement-all` coordinators SHALL be explicit-only on
Claude Code, Codex, and OpenCode. Only those skills, those coordinators, and
Plan revise mode answering a Ship blocker report SHALL start the workflows. Ship
SHALL always run as a dispatched `iwe-shipper` whose prompt carries only the
plan key, the operation, and the user's approvals quoted verbatim, so its
verification rests on the code and the graph alone. Implement started by the
user's own invocation SHALL run in the user's session. A dispatched workflow
SHALL stop and report at any point that needs a user decision it was not given.

#### Scenario: The user ships a plan directly

- **WHEN** the user runs `/agentdev:iwe-ship <plan>` with no approval
- **THEN** the skill dispatches `iwe-shipper` with the plan key and the ship
  operation and nothing else from the conversation, and the Shipper stops before
  a command with effects beyond the working tree and reports the approval it
  needs.

#### Scenario: The user ships a plan with an approval

- **WHEN** the user re-runs `/agentdev:iwe-ship <plan>` granting the approval
  the Shipper reported
- **THEN** the dispatch prompt quotes that approval verbatim, and the Shipper
  runs the approved command.

#### Scenario: The user implements a plan directly

- **WHEN** the user runs `/agentdev:iwe-implement <plan>` and a task needs a
  material deviation
- **THEN** the session follows the `iwe-implementer` rulebook and waits for the
  user's direction.

#### Scenario: A coordinator ships every implemented plan

- **WHEN** the user runs `/agentdev:iwe-ship-all`
- **THEN** it dispatches one `iwe-shipper` agent per implemented plan in
  dependency order and re-posts each one's Verify verdict and outcome.

#### Scenario: A dispatched workflow reaches a user decision

- **WHEN** a dispatched `iwe-shipper` or `iwe-implementer` reaches a point that
  needs the user
- **THEN** it stops without taking that step and reports what it needs.

#### Scenario: Explore hears a partial answer to an open question

- **WHEN** during `/agentdev:iwe-explore` the user answers an open question in a
  way that leaves a plan apparently complete
- **THEN** Explore neither dispatches `iwe-shipper` nor loads a Ship or
  Implement skill or coordinator, and names the next step for the user.

#### Scenario: A revision answers a Ship blocker

- **WHEN** `/agentdev:iwe-plan` revise mode changes a plan to answer the Ship
  blocker report Ship returned for it, and validation passes
- **THEN** Plan dispatches `iwe-shipper` on that plan, whose Verify decides
  whether it ships.

#### Scenario: The model tries to start a gated skill

- **WHEN** a model on Claude Code, Codex, or OpenCode tries to load `iwe-ship`,
  `iwe-implement`, or either coordinator without a user request
- **THEN** the harness withholds it.

### Requirement: Map derives the codebase lane from the code and refreshes it incrementally

The Map skill SHALL write `data/codebase/` only from reading the current
checkout, SHALL place each component doc at the canonical key that mirrors its
source path, SHALL stamp every doc with the `source` it describes, a
`source_digest` fingerprint of tracked source contents, and a `verified` record,
SHALL link children from their parent's `## Contains` so the hub tree renders
the code's containment, and SHALL re-read only the docs whose tracked source
contents differ from `source_digest` when refreshing.

#### Scenario: The map is written for the first time

- **WHEN** the user asks to map the codebase and `data/codebase.md` has no
  members
- **THEN** Map surveys entry points, external surfaces, and the build, run, and
  test commands first, proposes the containment tree before writing, writes one
  doc per confirmed component plus flow and api docs, fills `## Getting around`,
  and ends with `iwe normalize` and `iwe schema validate` passing

#### Scenario: Code moved after the map was written

- **WHEN** Map runs in refresh mode, or Verify's audit hands it stale map docs
- **THEN** Map re-reads only the components whose tracked source contents differ
  from `source_digest`, rewrites the affected sections, bumps `source_digest`,
  `verified`, and `stale_after`, and leaves fresh docs untouched

#### Scenario: A mapped component was moved or deleted

- **WHEN** a map doc's `source` no longer exists in the checkout
- **THEN** Map relocates the doc with `iwe rename` when the code moved, or
  removes it with `iwe delete` when the code is gone, and never moves or deletes
  the file by hand

#### Scenario: The code answers a question the map cannot

- **WHEN** reading a component reveals a design decision or its rationale
- **THEN** Map records what the code does in the map doc and reports the
  rationale as a candidate `data/architecture/` doc rather than writing it into
  the map

### Requirement: Map staleness reflects described content

The codebase-map staleness check SHALL classify a map document by whether the
content it describes changed, not by whether any byte under its `source`
changed. Content designated machine-managed SHALL be normalized to a fixed
placeholder before the source fingerprint is computed.

#### Scenario: An automerged pin bump leaves the document fresh

- **WHEN** a dependency-update commit changes only a pinned value designated
  machine-managed under a map document's `source`
- **THEN** the staleness check reports that document as `FRESH`

#### Scenario: A structural change around a masked value is still staleness

- **WHEN** a commit changes the structure holding a masked value — the identity
  of the pinned artifact, the set of pinned entries, or the presence of the pin
- **THEN** the staleness check reports the document as `STALE`

#### Scenario: Changing the mask set invalidates the documents it reaches

- **WHEN** the mask designations change
- **THEN** the staleness check reports as `STALE` every document with a source
  file the changed designation matches, and reports the remaining documents
  unchanged

#### Scenario: An unreadable designation breaks only its own subtree

- **WHEN** a mask designation cannot be read or a pattern cannot be compiled
- **THEN** the check reports every document whose sources reach that designation
  as broken, naming it, rather than computing a fingerprint from unmasked
  content
- **AND** documents whose sources do not reach it keep their normal verdicts

### Requirement: An agent push carries a fresh codebase map

The branch push helper shared by the pull request skills SHALL run the
codebase-map staleness check against the branch head, including a head the
upstream already holds, SHALL refuse to push when the check reports a stale map,
and SHALL push without the check only when the repository has no IWE map or the
caller passes an explicit override. The AI pull request review SHALL NOT report
codebase-map staleness when the repository's CI runs the staleness check, which
then owns it.

#### Scenario: A push would carry a stale map

- **WHEN** a pull request skill pushes a branch whose map docs the staleness
  check reports stale
- **THEN** the push helper pushes nothing and reports `MAP_STALE`, and the skill
  runs the Map refresh, commits it, and pushes again

#### Scenario: The repository has no map

- **WHEN** the repository root has no `.iwe/config.toml`, or the check reports
  no map docs
- **THEN** the push helper pushes without gating

#### Scenario: The user pushes a stale map on purpose

- **WHEN** the user explicitly asks to push while the map is stale
- **THEN** the skill passes the override, the helper pushes and reports the
  check as overridden, and CI still reports the stale map

#### Scenario: A stale head reached the remote outside the helper

- **WHEN** the branch head is already on its upstream, pushed by a path that
  does not run the check, and its map docs are stale
- **THEN** the push helper reports `MAP_STALE`, and the skill refreshes the map,
  commits it, and pushes again

#### Scenario: A review sees a stale map

- **WHEN** an AI review runs on a pull request whose map docs are stale, in a
  repository whose CI runs the staleness check
- **THEN** the review raises no finding about map staleness

### Requirement: Capture files complete inbox documents

The Capture skill SHALL be the only writer of new bug, proposed-feature, and
backlog-task documents, SHALL refuse a document missing any frontmatter field or
body section `SCHEMA.md` requires for its type, SHALL check the graph for a
likely duplicate before filing, SHALL file a feature at `stage: proposed` and
never promote it, and SHALL link every filed document from its hub and end with
`iwe normalize` and `iwe schema validate` passing.

#### Scenario: A complete item is captured

- **WHEN** Capture is invoked for a bug, feature, or task whose required
  sections and fields are all supplied, and no likely duplicate exists
- **THEN** Capture writes the document at its lane's key with the `stage` and
  `status` `SCHEMA.md` derives for it, stamps `generated` and `sources`, links
  it from its hub — a task under its priority section — and validates the graph

#### Scenario: A required section is missing

- **WHEN** the supplied content lacks any section or field required for its type
- **THEN** Capture writes nothing and lists every missing section and field

#### Scenario: A likely duplicate exists

- **WHEN** a fuzzy or lexical search finds an existing document that matches the
  item
- **THEN** Capture writes nothing and shows the match

#### Scenario: A someday idea is promoted

- **WHEN** Capture is invoked for a task with `--from someday/<slug>`
- **THEN** Capture files the backlog task from the idea and moves the idea's
  link out of `data/someday.md`

#### Scenario: The item grew from a GitHub issue

- **WHEN** the exploration behind the item started from a GitHub issue
- **THEN** Capture records the issue under `sources:`, and after validation
  closes it with a comment naming the captured document

#### Scenario: Explore or Implement finds an inbox item

- **WHEN** Explore settles a defect, feature, or task, or Implement finds a
  defect or work its plan should not absorb
- **THEN** it hands the item to Capture rather than writing the document itself

### Requirement: Bug and feature documents keep the SCHEMA.md shape

The bug and feature schemas SHALL require the body shape `SCHEMA.md` prescribes
— a bug's `Bug:` H1 and its Symptom, Reproduction, Root cause, Fix, and Key
references sections; a feature's Purpose, Behaviour, Edge cases, and Open
questions sections — in that order, while allowing additional sections.

#### Scenario: A document is written without Capture

- **WHEN** a bug or feature document lacks a required section, has them out of
  order, or a bug's H1 lacks the `Bug:` prefix
- **THEN** `iwe schema validate` fails and names the document

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
