# Spec Delta

## MODIFIED Requirements

### Requirement: Plan creates or revises planning state without implementing

The Plan skill SHALL treat its invocation as authorization to write planning
state only, SHALL resolve material ambiguity before committing the plan, and
SHALL keep a created or revised plan coherent across context, approach, tasks,
dependencies, verification, out-of-scope boundaries, and current
code anchors. Plan SHALL neither start Implement nor name it as a next step.
When a decision was made as specific text, Plan SHALL reproduce that text
verbatim in the task that applies it and SHALL never paraphrase it.

#### Scenario: A plan grows from a GitHub issue

- **WHEN** Plan creates a plan for work that arrived as a GitHub issue
- **THEN** the plan links the issue URL in `## Context` and under `sources:`,
  and after the plan validates, Plan closes the issue with a comment naming the
  plan path, so the issue and the plan reference each other and the issue no
  longer competes with the plan as the open record of the work

#### Scenario: A planning request also asks to build the change

- **WHEN** a request invokes Plan while also asking for implementation
- **THEN** Plan creates and validates the planning state, reports readiness
  without naming Implement, and stops before editing implementation code,
  neither loading Implement nor dispatching `iwe-implementer`

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

### Requirement: Implement never hides a material deviation

The Implement skill SHALL distinguish intent-preserving task corrections from
material changes, SHALL never narrow or extend specified behavior without either
the user's direction or an evaluator-approved plan revision, SHALL leave to the
user every change that drops, narrows, defers, or accepts an exception to
specified behavior, changes `release`, or changes text the user approved, and
SHALL mark a task complete only when its full specified behavior has passing
evidence.

#### Scenario: A tactical correction preserves intent

- **WHEN** implementation reveals a stale anchor or task breakdown that can be
  corrected without changing scope, observable behavior, compatibility,
  acceptance criteria, or dependencies
- **THEN** Implement updates the plan, reports the correction, and may continue
  within the user's requested task boundary

#### Scenario: Completing a task requires extending the plan

- **WHEN** implementation would need an added task or a corrected
  verification step, keeping every specified behavior
- **THEN** Implement leaves the task unchecked and takes the plan through an
  evaluated revision before coding past it

#### Scenario: Completing a task requires narrowing what was agreed

- **WHEN** implementation would need to drop, narrow, defer, or accept an
  exception to specified behavior, change `release`, or change text the user
  approved
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
to its own document — `data/findings/`, `data/bugs/`, or `data/backlog/` —
rather than into the plan's `## Context` or `## Approach`, which state intent
and remain the Plan skill's to own. Every edit to a plan's intent sections SHALL
be audited for durable-knowledge residue by a reviewer holding no context beyond
the audit scope and the plan file, before the edit is validated.

#### Scenario: Implementation produces a durable finding

- **WHEN** implementation establishes a constraint, root cause, or rejected
  alternative that the plan did not anticipate
- **THEN** Implement records it in a finding, bug, or backlog item and reports
  the capture, leaving the plan's intent sections unchanged

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
project state. Verify's rulebook SHALL be defined once, as the catalog agent
`iwe-verifier`, and every Verify run SHALL start from a fresh context:
`/agentdev:iwe-verify` SHALL dispatch `iwe-verifier` with a prompt carrying only
the plan key or audit mode and the user's approvals quoted verbatim, and
`iwe-shipper` SHALL follow that rulebook in its own context without dispatching
an agent. Verify SHALL run a verification command whose effects reach beyond the
working tree only under a quoted approval that names it, and otherwise SHALL
stop before it and report the approval it needs.

`/agentdev:iwe-verify` SHALL refuse to run on a dirty worktree, SHALL save each
report whose verdict is `Ready to ship`, `Blocked`, or `Audit` as the one saved
report for its plan or for audit mode, keyed by the commit it ran on and the
digest of the active agentdev catalog, and SHALL never save a `Needs decision`
report. On both routes it SHALL return the saved report, marked as saved and
without running any check or verification command, when that report's commit is
`HEAD` and its catalog digest is the active catalog's, unless the user's request
carries `--fresh`. The saved report SHALL record the request
`/agentdev:iwe-verify` was invoked with and the prompt the `iwe-verifier`
rulebook ran under, whether dispatched or followed in place, and neither SHALL
be part of the key. A verification command that leaves the worktree dirty SHALL
be a CRITICAL finding.

#### Scenario: Verification reports no critical findings

- **WHEN** Ship invokes Verify for a completed plan and Verify returns zero
  CRITICAL findings
- **THEN** Ship may proceed to its durable state transitions

#### Scenario: Verification reports a critical finding

- **WHEN** Ship invokes Verify and Verify reports one or more CRITICAL findings
- **THEN** Ship makes no shipping state transition and reports the blockers

#### Scenario: A plan is cancelled rather than shipped

- **WHEN** the user explicitly cancels an active plan
- **THEN** Ship records cancellation without requiring implementation
  verification and performs no release or implemented-feature transition

#### Scenario: Verify is invoked outside Ship

- **WHEN** the user requests a mid-implementation check or a workspace audit
- **THEN** the skill dispatches `iwe-verifier`, which produces its
  evidence-backed report and stops without invoking Ship or mutating the graph

#### Scenario: The user verifies a plan without an approval

- **WHEN** the user runs `/agentdev:iwe-verify <plan>` and a `## Verification`
  command reaches beyond the working tree
- **THEN** the dispatch prompt carries the plan key and nothing else from the
  conversation, and `iwe-verifier` stops before that command and reports the
  approval it needs

#### Scenario: The user verifies a plan with an approval

- **WHEN** the user re-runs `/agentdev:iwe-verify <plan>` granting the approval
  the verifier reported, alongside other claims about the work
- **THEN** the dispatch prompt quotes the approval verbatim and leaves the other
  claims out, and `iwe-verifier` runs the approved command

#### Scenario: Ship runs Verify in place

- **WHEN** `iwe-shipper` reaches its Verify step
- **THEN** it follows the `iwe-verifier` rulebook in its own context and
  dispatches no agent

#### Scenario: Ship reuses the Implement loop's report

- **WHEN** the Implement loop's Verify saved a report for the plan and
  `iwe-shipper` reaches its Verify step on the same clean commit with the same
  active catalog
- **THEN** the skill returns the saved report, marked as saved from that commit,
  without running any check or verification command, and Ship proceeds on its
  verdict

#### Scenario: The commit or the catalog changed

- **WHEN** `HEAD` or the active catalog digest differs from the saved report's
- **THEN** Verify runs in full and its report replaces the saved one

#### Scenario: The worktree is dirty

- **WHEN** `/agentdev:iwe-verify` is invoked with a tracked change or an
  untracked file Git does not ignore
- **THEN** it stops before any Verify step and reports the dirty worktree

#### Scenario: A report that needs a decision is not saved

- **WHEN** Verify reports `Needs decision` and the user re-runs it granting the
  approval
- **THEN** Verify runs again rather than returning the earlier report

#### Scenario: The user asks for a fresh run

- **WHEN** the user runs `/agentdev:iwe-verify <plan> --fresh` on a commit with
  a saved report
- **THEN** Verify runs in full and its report replaces the saved one

#### Scenario: The saved report records how Verify was invoked

- **WHEN** Verify saves a report on either route
- **THEN** its frontmatter carries the request the skill was invoked with and
  the verifier prompt, verbatim, including every approval the prompt quotes

#### Scenario: A verification command dirties the worktree

- **WHEN** a `## Verification` command leaves a tracked change or an unignored
  file behind
- **THEN** Verify reports a CRITICAL naming the dirty paths

### Requirement: The Verify report reaches the conversation verbatim

Every Verify report SHALL number its findings by severity in report order —
`C<n>` for CRITICAL, `W<n>` for WARNING, `S<n>` for SUGGESTION — and every
caller of Verify SHALL show the report verbatim in its final message text:
`/agentdev:iwe-verify` on the session route, on a saved hit and after a save;
`iwe-shipper` ahead of its Ship summary; and the Implement session for the last
Verify round of a run. A path to the saved report, or the report appearing only
in a tool call or tool result, SHALL not count as showing it. A Ship blocker
report SHALL route each Verify CRITICAL by its ID without restating it, and
SHALL state in full, with anchored evidence, each blocker Ship found outside
Verify.

#### Scenario: A session verifies a plan

- **WHEN** the user runs `/agentdev:iwe-verify <plan>` and the verifier returns
  a report, or the skill finds a saved one
- **THEN** the session's final message contains that report verbatim, not only
  its verdict or the saved report's path

#### Scenario: Ship is blocked by Verify

- **WHEN** `iwe-shipper` gets a Verify report with CRITICAL findings
- **THEN** its final message carries the Verify report verbatim, then a blocker
  report that names each CRITICAL by its ID with its route, and
  `/agentdev:iwe-ship` re-posts that message verbatim

#### Scenario: Ship finds a blocker Verify did not

- **WHEN** Verify reports zero CRITICAL findings and a later Ship step finds a
  blocker
- **THEN** the Shipper's final message carries the Verify report verbatim and
  states the blocker in full with its anchored evidence and route

#### Scenario: A plan ships

- **WHEN** `iwe-shipper` ships a plan
- **THEN** its final message carries the Verify report verbatim before the
  completed and preserved operations and the commit

#### Scenario: The Implement loop runs several Verify rounds

- **WHEN** an Implement run verifies, fixes findings, and verifies again
- **THEN** its final report carries the last Verify report verbatim and each
  earlier round's verdict with the first line of each finding it fixed

### Requirement: Workflow improvements preserve the IWE and OKF model

The strengthened skills SHALL continue to use IWE's single-plan-document
workflow, graph links, existing stage conventions, `sources` attribution, and
schema validation. The graph SHALL remain a conformant OKF v0.2 bundle —
`data/index.md` lists the hubs, `data/log.md` stays date-grouped, and the `okf`, `okf-index`,
and `okf-log` schemas check every document — and SHALL diverge from OKF only
where OKF costs merges or upkeep. No document under `data/` SHALL set OKF's
optional `status`, because `stage` is the lifecycle field, nor OKF's `generated`
or `verified`, because source control records when and by whom a document
changed. The `banned-frontmatter-keys` pre-commit check SHALL reject a document
that sets any of them.

#### Scenario: Updated skills write project memory

- **WHEN** an updated skill creates or meaningfully changes an IWE document
- **THEN** it follows the existing OKF metadata, graph membership,
  normalization, validation, and commit requirements defined by the workspace

#### Scenario: A document sets a banned frontmatter key

- **WHEN** a document under `data/` carries `status`, `generated`, or `verified`
- **THEN** the `banned-frontmatter-keys` check fails and names the document and
  the key

#### Scenario: A reserved file loses its OKF shape

- **WHEN** `data/index.md` or `data/log.md` departs from the shape its OKF
  schema defines
- **THEN** `iwe schema validate` fails and names the file

## REMOVED Requirements

### Requirement: Plans express spec impact at risk-appropriate fidelity

**Reason**: Specs live in `openspec/specs/` and change only through an OpenSpec
change, so an IWE plan no longer records spec impact.

**Migration**: Plan a behavior change as an OpenSpec change and link it from the
IWE plan, per `project-knowledge` › "Behavior changes go through an OpenSpec
change".

### Requirement: Ship synchronizes durable specs by intelligent merge

**Reason**: `openspec archive` merges a change's delta into its spec, so Ship no
longer touches specs.

**Migration**: Archive the OpenSpec change that specifies the work; its archive
also updates the spec's `## Rationale`, per `project-knowledge` › "Archiving a
change keeps rationale current".
