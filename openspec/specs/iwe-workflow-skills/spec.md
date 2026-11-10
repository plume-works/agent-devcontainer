# IWE workflow skills Specification

## Purpose

Defines reliable, phase-aware behavior for the IWE skills that guide work from
open-ended exploration through planning, implementation, verification, and
durable shipping state.

## Requirements

### Requirement: Explore remains an adaptive thinking mode

The Explore skill SHALL investigate the project graph and codebase without
editing application code, SHALL remain adaptive and patient as the problem takes
shape, and SHALL offer capture or a phase handoff without pressuring the user to
formalize unfinished thinking. Explore SHALL neither start Implement nor name it
as a next step. Explore SHALL propose a change only for a problem it can show
has occurred, SHALL list a case it can only imagine as not observed rather than
design for it, and SHALL weigh a risk its own proposal creates against that
proposal rather than open it as a new question. When the user approves specific
text, Explore SHALL persist it verbatim outside the conversation and reproduce
it verbatim in the handoff, and SHALL never paraphrase it. Once the problem has
open questions, Explore SHALL settle them with the user one at a time — one
topic per turn and one decision per question, in the user's names and design —
and SHALL record each answer verbatim as it is given.

#### Scenario: Exploration starts from an open-ended idea

- **WHEN** the user asks to explore an idea without committing to implementation
- **THEN** Explore follows relevant questions and tradeoffs, grounds claims in
  current project evidence, and ends with the current understanding and an
  optional next step

#### Scenario: Exploration starts from a GitHub issue

- **WHEN** the user invokes Explore with an issue URL, an `<owner>/<repo>#<n>`
  reference, or an issue number
- **THEN** Explore reads the issue and all of its comments into `./.tmp/` before
  investigating, verifies the issue's claims against the code and the graph
  rather than adopting them, never edits the issue, and carries the issue URL
  into any handoff to Plan

#### Scenario: Exploration starts during implementation

- **WHEN** the user invokes Explore because an active implementation task
  exposed a complication
- **THEN** Explore reads the active plan and task, investigates without editing
  code, and hands any resulting decision, scope change, or new work to Plan,
  without naming Implement

#### Scenario: The user approves specific wording

- **WHEN** the user agrees to specific text — wording for a document, a snippet,
  a message — that a later plan or edit will apply
- **THEN** Explore writes it verbatim to `.tmp/approved-wording-<slug>.md`
  before continuing, names that file in the handoff, and reproduces the text
  verbatim rather than describing it

#### Scenario: The exploration has open questions

- **WHEN** the problem being explored has more than one open question
- **THEN** Explore names one topic and stays on it until the user settles it,
  asks one decision at a time as numbered options with a recommendation, keeps
  the user's names and design unless changing them is the question asked,
  settles a question about system behavior with evidence before asking it,
  records each answer verbatim in `.tmp/approved-wording-<slug>.md` — marked
  approved only on an explicit yes — and opens the next topic only after the
  current one is settled

#### Scenario: Exploration proposes a change

- **WHEN** Explore is about to propose a change to the system
- **THEN** it first collects and counts the observed occurrences of the problem,
  proposes the smallest change that would have prevented them, lists any case it
  can only imagine under "not observed", and opens no thread or open question
  for a risk that exists only because of its own proposal

### Requirement: Plan creates or revises planning state without implementing

The Plan skill SHALL treat its invocation as authorization to write planning
state only, SHALL resolve material ambiguity before committing the plan, and
SHALL keep a created or revised plan coherent across context, approach, tasks,
spec impact, dependencies, verification, out-of-scope boundaries, and current
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

### Requirement: Plans declare their release impact

The plan schema SHALL require every active plan to carry a `release` frontmatter
value: `internal`, or a non-empty list of the `features/` and `bugs/` keys the
work adds, changes, or fixes. The Plan skill SHALL set that value when it files
a plan, SHALL declare `internal` only when no workspace user or template
consumer sees a difference, SHALL have Capture file a missing feature before it
files the plan, and SHALL set every bug the plan lists to `stage: planned`. Ship
SHALL take a plan's release entries only from that value, SHALL never create a
feature, SHALL write the `## Fix` of each bug it marks done, and SHALL return
each listed bug to `stage: pending` when it cancels the plan.

#### Scenario: A plan introduces user-visible behavior with no feature

- **WHEN** Plan files a plan whose work changes what a workspace user or
  template consumer sees, and no feature describes it
- **THEN** Plan hands the feature to Capture, lists its key in `release`, and
  sets the feature to `stage: accepted`

#### Scenario: A plan lists a bug

- **WHEN** Plan files a plan whose `release` lists a bug at `stage: pending`
- **THEN** Plan sets the bug to `stage: planned`

#### Scenario: A plan changes nothing users see

- **WHEN** Ship ships a plan that declares `release: internal`
- **THEN** Ship marks the plan done and adds no release entry

#### Scenario: A plan declares features and bugs

- **WHEN** Ship ships a plan whose `release` lists feature and bug keys
- **THEN** Ship marks each feature implemented and each bug done, writes each
  bug's `## Fix` describing the shipped fix and linking the plan, and adds one
  unreleased inclusion link per listed document — a feature new in this version
  under Added, a feature released in an earlier version under Changed, a bug
  under Fixed

#### Scenario: A plan listing bugs is cancelled

- **WHEN** Ship cancels a plan whose `release` lists a bug at `stage: planned`
- **THEN** Ship sets the bug to `stage: pending` and writes no `## Fix`

#### Scenario: An active plan has no release declaration

- **WHEN** an active plan lacks `release`, or its value is neither `internal`
  nor a list of `features/` and `bugs/` keys
- **THEN** `iwe schema validate` fails and names the plan, and Ship returns a
  blocker report for Plan revise mode without a lifecycle transition

#### Scenario: A declared document does not exist

- **WHEN** a plan's `release` lists a key with no document behind it
- **THEN** Ship returns a blocker report for Plan revise mode without a
  lifecycle transition and creates no document

#### Scenario: A shipped plan predates the field

- **WHEN** a plan at `stage: done` or `stage: cancelled` has no `release`
- **THEN** `iwe schema validate` accepts it

### Requirement: Plans test behaviour and leave CI to the merge gate

Plan SHALL write no task or verification step whose only claim is that CI
passes, SHALL record behaviour observable only after merge as a task carrying a
`**Closed by:**` line, SHALL name a test as coverage only when it runs the
behaviour, and SHALL scope a verification search for leftover text to the files
the plan changes. Plan SHALL add no end-to-end test that drives an agent session
through the workflow skills against a live model; behaviour only such a session
can show SHALL be an observation task naming who closes it. Before validation,
Plan SHALL check each requirement it adds or modifies against the plan's
`## Approach` and the code that requirement describes. Every `## Verification`
command SHALL run in the checkout the `iwe-verifier` agent works in, inside the
Dev Container or container the agent already runs in, without starting a nested
Dev Container or CI. A requirement SHALL claim only what its mechanism delivers
and name each limit of that mechanism Plan knows.

#### Scenario: A plan's work needs CI

- **WHEN** Plan writes a plan whose change is checked by CI
- **THEN** the plan carries no "CI passes" task or verification step

#### Scenario: Behaviour is visible only after merge

- **WHEN** a requirement can be observed only once the change is on the default
  branch
- **THEN** Plan writes a task for it carrying a `**Closed by:**` line naming who
  or what closes it

#### Scenario: Behaviour only a live agent session shows

- **WHEN** a requirement can be observed only by driving an agent session
  through the workflow skills against a live model
- **THEN** Plan writes an observation task naming who closes it and adds no
  end-to-end test for it

#### Scenario: A requirement disagrees with the code

- **WHEN** a requirement Plan adds or modifies states a restriction the code it
  describes does not hold, or contradicts the plan's `## Approach`
- **THEN** Plan changes the requirement, the `## Approach`, or adds a task
  before validation, and the plan carries no disagreement

#### Scenario: A check needs a nested Dev Container

- **WHEN** proving the work needs a command that runs only after starting a
  nested Dev Container
- **THEN** `## Verification` does not list the command; the plan cites a CI job
  that runs it or adds a task carrying a `**Closed by:**` line

#### Scenario: A mechanism has a known limit

- **WHEN** Plan writes a requirement for a mechanism with a limit it knows of
- **THEN** the requirement names that limit

### Requirement: Implement starts work on its own branch

The Implement skill SHALL, when the checkout is on `main` or `master`, create
the work branch through the git-new-branch skill, named by the iwe-branch-name
skill's next `impl` iteration for the plan, before executing the first task, and
SHALL continue on the current branch otherwise. The branch SHALL be cut from
`main` when no `## Depends on` plan is unshipped and the plan has no open
earlier iteration; otherwise it SHALL be cut with `--depends-on` for the top
open pull request of each such dependency and earlier iteration, leaving out any
that sits below another in the same chain.

#### Scenario: Implementation starts on main

- **WHEN** Implement begins plan `data/plans/<date>-<slug>` with `main` checked
  out and every dependency shipped
- **THEN** it creates branch `iwe/<slug>/iter-<N>-impl`, with `N` from
  iwe-branch-name, from `main` through git-new-branch before executing any task

#### Scenario: Implementation starts on a feature branch

- **WHEN** Implement begins with a branch other than `main` or `master` checked
  out
- **THEN** it executes the plan on that branch without creating another

#### Scenario: Dependency in review

- **WHEN** a `## Depends on` plan is not shipped and has an open pull request
- **THEN** the work branch is created with `--depends-on` for that pull request

#### Scenario: Dependencies in two chains

- **WHEN** two unshipped dependencies have open pull requests in different
  chains
- **THEN** the work branch is created with `--depends-on` for both

### Requirement: Implement stops on a dependency with nothing to build on

The Implement skill SHALL stop before creating a branch when a `## Depends on`
plan is not `stage: done` and has no open pull request, and SHALL name it.

#### Scenario: Unshipped dependency without a pull request

- **WHEN** a dependency is not shipped and none of its work branches has an open
  pull request
- **THEN** Implement stops and names the dependency

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

- **WHEN** implementation would need an added task or requirement, a heavier
  `## Spec changes` form, or a corrected verification step, keeping every
  specified behavior
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

### Requirement: Implement verifies its own work and acts on the report

When a plan's last task closes, the Implement session — the session that loaded
`/agentdev:iwe-implement` — SHALL run Verify through `/agentdev:iwe-verify` and
SHALL act on every CRITICAL finding, and on a WARNING only when its fix fits a
task the plan already has and adds no claim the code must newly meet. It SHALL
file every other WARNING through `/agentdev:iwe-capture`, report SUGGESTIONs
only, and SHALL not stop for an outstanding observation. A code or evidence
finding SHALL be fixed under the Implement rules and verified again, and a
finding about the plan's intent SHALL go through an evaluated revision. The
Implement session SHALL stop when a finding recurs after a fix attempt, after
three Verify rounds, or after one approved revision in the run. No agent the
loop dispatches SHALL dispatch another.

#### Scenario: Verify finds nothing to act on

- **WHEN** the plan's tasks are closed and Verify reports zero CRITICAL findings
  and no WARNING whose fix fits an existing task
- **THEN** the run ends with its rollup and the Verify verdict, and suggests
  `/agentdev:iwe-ship`

#### Scenario: Verify finds a code defect

- **WHEN** the Verify report carries a CRITICAL whose route is code or evidence
- **THEN** the Implement session fixes it under the Implement rules, closes it
  with evidence, and runs Verify again through `/agentdev:iwe-verify`

#### Scenario: A warning would add work

- **WHEN** Verify reports a WARNING whose fix needs a new task or a new claim
- **THEN** the Implement session files it through `/agentdev:iwe-capture`, names
  it in the report, and does not act on it in this run

#### Scenario: An observation is outstanding

- **WHEN** Verify lists an unticked `**Closed by:**` task under Outstanding
  observations and reports nothing else to act on
- **THEN** the run ends with its rollup naming the observation

#### Scenario: A finding recurs

- **WHEN** a finding the Implement session already tried to fix appears in the
  next Verify report
- **THEN** the run stops and reports the finding, the fix it attempted, and the
  Verify report

#### Scenario: Verify needs an approval

- **WHEN** Verify reports `Needs decision` for a command with effects beyond the
  working tree
- **THEN** the run stops and names the approval, which the user grants by
  re-running the skill

### Requirement: Implement revises its plan only after an independent evaluation

The Plan rulebook SHALL be defined once, as the catalog agent `iwe-planner`,
which `/agentdev:iwe-plan` follows in place. The Implement session SHALL revise
a plan only by drafting the revision under the `iwe-planner` revise rules,
including its fresh-context audit and validation, changing only lines that
answer the quoted finding, leaving it uncommitted, and dispatching
`iwe-revision-evaluator` with a prompt carrying only the plan key and the
finding the revision answers, quoted as reported. It SHALL commit the revision
only on the evaluator's `APPROVE`. On `REJECT` or `ESCALATE` it SHALL restore
the plan from `HEAD` and stop with a report. The evaluator SHALL judge the
uncommitted diff against the plan at `HEAD`, SHALL never approve a revision that
drops, narrows, defers, or accepts an exception to specified behavior, changes
`release`, or changes text the user approved, and SHALL reject a revision with a
hunk that answers no quoted finding or that adds or sharpens a claim the code
must newly meet.

#### Scenario: The evaluator approves an added task

- **WHEN** Verify reports a requirement with no implementation, the drafted
  revision adds a task that covers it, and the evaluator returns `APPROVE`
- **THEN** the revision commits, Implement executes the new task, and
  `iwe-verifier` runs again

#### Scenario: The evaluator escalates a narrowing

- **WHEN** a drafted revision would narrow specified behavior
- **THEN** the evaluator returns `ESCALATE`, the Implement session restores the
  plan from `HEAD`, and the run stops for the user's direction

#### Scenario: The evaluator rejects a restatement

- **WHEN** a drafted revision rewrites the plan's intent to describe the code
  without answering the quoted finding
- **THEN** the evaluator returns `REJECT`, the Implement session restores the
  plan from `HEAD`, and the run stops with the evaluator's reasons

#### Scenario: The evaluator rejects a stray hunk

- **WHEN** a drafted revision answers the quoted finding and also changes lines
  the finding does not concern
- **THEN** the evaluator returns `REJECT` naming the stray hunk

#### Scenario: The evaluator rejects a sharpened promise

- **WHEN** a drafted revision rewrites a requirement into a stricter claim the
  code must newly meet
- **THEN** the evaluator returns `REJECT`

#### Scenario: The evaluator sees no conversation

- **WHEN** the Implement session dispatches `iwe-revision-evaluator`
- **THEN** the prompt holds the plan key and the quoted finding and nothing else
  from the conversation

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

- **WHEN** Verify reports zero CRITICAL findings and the spec merge finds an
  intent-versus-implementation mismatch
- **THEN** the Shipper's final message carries the Verify report verbatim and
  states the mismatch in full with its anchored evidence and route

#### Scenario: A plan ships

- **WHEN** `iwe-shipper` ships a plan
- **THEN** its final message carries the Verify report verbatim before the
  completed and preserved operations and the commit

#### Scenario: The Implement loop runs several Verify rounds

- **WHEN** an Implement run verifies, fixes findings, and verifies again
- **THEN** its final report carries the last Verify report verbatim and each
  earlier round's verdict with the first line of each finding it fixed

### Requirement: Verify judges conformance to the plan

Verify SHALL report a CRITICAL or WARNING finding only against a requirement,
scenario, task, or verification step of the plan's effective contract, citing
it. It SHALL treat a scenario as uncovered only when a test that runs the
behaviour could cover it, and SHALL never count a check of file contents as
coverage. It SHALL accept a CI job as evidence for behaviour only CI exercises
when the job exercises that behaviour, without requiring a run on the current
head. It SHALL list an unticked task carrying a `**Closed by:**` line under
Outstanding observations rather than as a CRITICAL.

#### Scenario: A weakness the plan does not address

- **WHEN** Verify notices a way to defeat the code that no requirement,
  scenario, task, or verification step of the plan addresses
- **THEN** it reports no CRITICAL or WARNING for it

#### Scenario: A scenario has only a content test

- **WHEN** the only test for a scenario reads a repository file to check its
  text
- **THEN** Verify counts the scenario as uncovered only if a test that runs the
  behaviour could cover it, and never counts the content test as coverage

#### Scenario: A post-merge observation is unticked

- **WHEN** the plan's only unticked task carries a `**Closed by:**` line
- **THEN** Verify lists it under Outstanding observations and reports no
  CRITICAL for it

#### Scenario: A CI job ran on an earlier commit

- **WHEN** a task cites a CI job that exercises behaviour only CI reaches, and
  the run cited is on an earlier commit than `HEAD`
- **THEN** Verify accepts the evidence

### Requirement: Adversarial review runs only when asked

The adversarial review SHALL be defined once, as the catalog agent
`iwe-adversarial-reviewer`, which `/agentdev:iwe-adversarial-review` dispatches
from a fresh context with a prompt carrying only the plan key, the target
(`plan` or `code`), and the user's approvals quoted verbatim. The agent SHALL
edit nothing and dispatch no agent, and every finding against code SHALL name
the plan claim it defeats, or none. The review SHALL run only on a person's
request or a plan task that runs it; Plan SHALL never invoke it. In the
Implement loop, a finding that defeats a plan claim SHALL take the code route,
and any other finding SHALL be filed through `/agentdev:iwe-capture`.

#### Scenario: A plan task runs the review

- **WHEN** Implement reaches a task that runs
  `/agentdev:iwe-adversarial-review <plan> code` and the report names a defeated
  plan claim
- **THEN** the Implement session fixes it under the Implement rules, and files
  every finding that names no plan claim

#### Scenario: A person reviews a plan

- **WHEN** the user runs `/agentdev:iwe-adversarial-review <plan> plan`
- **THEN** the agent reports the plan's weaknesses and changes nothing

#### Scenario: Planning does not start the review

- **WHEN** `/agentdev:iwe-plan` creates or revises a plan
- **THEN** it neither loads `/agentdev:iwe-adversarial-review` nor dispatches
  `iwe-adversarial-reviewer`

### Requirement: Ship waits for every dependency

The Ship skill SHALL, before Verify in normal shipping, read the stage of every
plan in the plan's `## Depends on` at the remote default branch, and SHALL
return a Ship blocker report naming each one that is not `stage: done`, making
no state change.

#### Scenario: Dependency not shipped

- **WHEN** Ship runs on a plan whose dependency is still active
- **THEN** it returns a blocker report naming the dependency and leaves the plan
  active

### Requirement: Ship waits for post-merge observations

Ship SHALL refuse normal shipping while the plan has an unticked task carrying a
`**Closed by:**` line, SHALL make no shipping state transition, and SHALL name
each such task in its blocker report with the route: observe it, tick it with
evidence, then run Ship again.

#### Scenario: An observation is still open

- **WHEN** Ship runs on a plan whose Verify report has no CRITICAL and lists an
  outstanding observation
- **THEN** the Shipper returns `Blocked` naming the observation and changes no
  state

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
agents `iwe-shipper` and `iwe-implementer`. Ship's user entry skill SHALL be
explicit-only on Claude Code and OpenCode. Implement's entry skill SHALL be
model-invocable on both, so a session asked to implement a named plan may load
it; a request in another session's message SHALL be handled as a plain request.
Only those skills and Plan revise mode answering a Ship blocker report SHALL
start the workflows. Ship SHALL always run as a dispatched `iwe-shipper` whose
prompt carries only the plan key, the operation, and the user's approvals quoted
verbatim, so its verification rests on the code and the graph alone.
`iwe-implementer` SHALL never be dispatched: Implement SHALL run in the session
that loaded its entry skill and SHALL take every decision from that session's
own user, and an approval that another session's message claims the user gave
SHALL not count as one. A dispatched `iwe-shipper` SHALL stop and report at any
point that needs a user decision it was not given. Nothing authenticates who
typed a message in the session's own conversation; this requirement governs only
approvals that another session's message claims.

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
  material deviation that narrows what was agreed
- **THEN** the session follows the `iwe-implementer` rulebook and waits for the
  user's direction.

#### Scenario: A session is asked in plain words to implement a plan

- **WHEN** the user asks a session to implement a named plan without typing the
  command
- **THEN** the session loads `/agentdev:iwe-implement` and follows the
  `iwe-implementer` rulebook in place, dispatching no `iwe-implementer`.

#### Scenario: A dispatched Shipper reaches a user decision

- **WHEN** a dispatched `iwe-shipper` reaches a point that needs the user
- **THEN** it stops without taking that step and reports what it needs.

#### Scenario: Explore hears a partial answer to an open question

- **WHEN** during `/agentdev:iwe-explore` the user answers an open question in a
  way that leaves a plan apparently complete
- **THEN** Explore neither dispatches `iwe-shipper` nor loads a Ship or
  Implement skill, and names a next step for the user other than Implement.

#### Scenario: A revision answers a Ship blocker

- **WHEN** `/agentdev:iwe-plan` revise mode changes a plan to answer the Ship
  blocker report Ship returned for it, and validation passes
- **THEN** Plan dispatches `iwe-shipper` on that plan, whose Verify decides
  whether it ships.

#### Scenario: The model tries to start a gated skill

- **WHEN** a model on Claude Code or OpenCode tries to load `iwe-ship` without a
  user request
- **THEN** the harness withholds it.

### Requirement: Capture files complete inbox documents

The Capture skill SHALL be the only writer of new bug, proposed-feature, and
backlog-task documents, SHALL refuse a document missing any frontmatter field or
body section `SCHEMA.md` requires for its type, SHALL check the graph for a
likely duplicate before filing, SHALL file a feature at `stage: proposed` and
never promote it, SHALL file a bug at `stage: pending` — or at `stage: done`
with its `## Fix` when the same change fixed it — and a task at
`stage: pending`, and SHALL link every filed document from its hub and end with
`iwe normalize` and `iwe schema validate` passing.

#### Scenario: A complete item is captured

- **WHEN** Capture is invoked for a bug, feature, or task whose required
  sections and fields are all supplied, and no likely duplicate exists
- **THEN** Capture writes the document at its lane's key with the `stage`
  `SCHEMA.md` derives for it, stamps `sources`, links it from its hub at its
  sorted position, and validates the graph

#### Scenario: A bug fixed in the same change is captured

- **WHEN** Capture is invoked for a bug the same change already fixed, with a
  `## Fix` describing that fix
- **THEN** Capture files the bug at `stage: done`

#### Scenario: A required section is missing

- **WHEN** the supplied content lacks any section or field required for its
  type, including a bug's `severity`
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
— a bug's `Bug:` H1 and its Symptom, Reproduction, and Root cause sections,
followed by optional Potential solution and Fix sections; a feature's Purpose,
Behaviour, Edge cases, and Open questions sections — in that order, while
allowing additional sections. The bug schema SHALL require a `stage` of
`pending`, `planned`, `done`, or `cancelled` and a `severity` of `critical`,
`high`, `medium`, or `low`.

#### Scenario: A document is written without Capture

- **WHEN** a bug or feature document lacks a required section, has them out of
  order, or a bug's H1 lacks the `Bug:` prefix
- **THEN** `iwe schema validate` fails and names the document

#### Scenario: A bug lacks its stage or severity

- **WHEN** a bug document has no `stage` or no `severity`, or a value outside
  its enum
- **THEN** `iwe schema validate` fails and names the document

#### Scenario: A bug has no Fix

- **WHEN** a bug document has neither a Potential solution nor a Fix section
- **THEN** `iwe schema validate` accepts it

### Requirement: Workflow improvements preserve the IWE and OKF model

The strengthened skills SHALL continue to use IWE's single-plan-document
workflow, graph links, durable specs, existing stage conventions, `sources`
attribution, and schema validation. Risk-scaled spec deltas SHALL remain
embedded planning content without introducing OpenSpec change bundles, stores,
separate delta files, archive moves, or a claimed programmatic delta application
engine. The graph SHALL remain a conformant OKF v0.2 bundle — `data/index.md`
lists the hubs, `data/log.md` stays date-grouped, and the `okf`, `okf-index`,
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

### Requirement: Agents reach the graph through the iwe CLI

Every IWE skill and agent SHALL read and write the knowledge graph with the
`iwe` CLI run from the repository root. The repository SHALL register no IWE MCP
server, and the `dev_tools` role SHALL install `iwe` and `iwes` from the IWE
release tarball and SHALL NOT install `iwec`.

#### Scenario: A skill needs a graph operation

- **WHEN** a catalog skill queries or changes the graph
- **THEN** it runs an `iwe` command and assumes no `mcp__iwe__*` tool exists

#### Scenario: The image is provisioned

- **WHEN** the `dev_tools` role installs IWE
- **THEN** `iwe` and `iwes` are on `PATH` and `iwec` is not

### Requirement: Every graph write has one owner

A work item's `stage`, `priority`, `completed`, and `rank` SHALL live only in its
own frontmatter. Active plans, open bugs, and pending tasks SHALL share one
optional integer `rank`, lower first, and the build order SHALL be the query
`iwe find --filter '{rank: {$exists: true}}' --sort rank:1`. Ship SHALL remove
`rank`. Equal ranks SHALL be valid, break by key, and draw a CI warning that
does not fail the run. A hub SHALL be a flat list of inclusion links sorted by
member key without a `YYYYMMDD-` prefix, with no `##` sections, edited only when
a member is created, removed, or renamed. Release pages and `data/log.md` SHALL
be written only by a release cut.

#### Scenario: A plan ships

- **WHEN** Ship marks a plan done
- **THEN** the plan's own frontmatter changes, its `rank` is removed, and no hub,
  release page, or log entry is written

#### Scenario: Two work items share a rank

- **WHEN** the knowledge-base workflow runs on a graph where two items carry the
  same `rank`
- **THEN** it emits a warning naming both keys and the run does not fail

#### Scenario: A release is cut

- **WHEN** Ship runs `release <X.Y.Z>`
- **THEN** it builds `releases/<X.Y.Z>.md` from the done plans without
  `released`, sets `released` on each, and adds one dated group to
  `data/log.md`

## Rationale

### Ship and Implement are catalog agents behind an explicit request

The Ship and Implement rulebooks are the catalog agents `iwe-shipper` and
`iwe-implementer`; the skills that start them carry no rules of their own. A
stray Ship run reaches the remote, so `iwe-ship` keeps the
`disable-model-invocation` gate, which covers Claude Code directly and OpenCode
through the bridge's `deny`. `iwe-implement` stays model-invocable because it
needs a named active plan whose dependencies are done, so a stray match has
nothing to build. Ship always runs as a dispatched subagent, so its verification
rests on the code and the graph, never on what a conversation asserted.
Implement runs in the session that loaded it, so it can ask about an ambiguous
plan or a material deviation; an approval another session's message claims the
user gave is not one, because nothing authenticates the sender.

The gate rests on host behavior verified on Claude Code 2.1.280 and OpenCode
1.18.34, to recheck on a version bump: the Skill tool refuses a gated skill from
a subagent too; an agent's `skills:` preload withholds a gated skill; reading the
skill file is not gated, only discouraged by the refusal text; a `PreToolUse`
hook sees the tool call but not the skill or request behind it; and OpenCode's
`permission.skill.<name> = "deny"` hides a gated skill from the model while its
`agentdev:<name>` command still runs.

Rejected:

- **Drop Ship's gate and rely on descriptions.** An ungated skill is listed to
  the model on every harness, so a description match could start Ship from
  Explore.
- **Preload the gated skill into the agent.** Claude Code withholds it, so the
  agent starts without its rulebook.
- **Keep the rulebook in the gated skill and have the subagent read its file.**
  It is the route the refusal text forbids; a model may rightly refuse it, and
  one that complies has bypassed the gate.
- **A self-checking skill or a harness hook.** A self-check is prompt-level, and
  a hook cannot tell a requested dispatch from Explore's without parsing the
  transcript.
- **Coordinator skills that implement or ship every plan in turn.** A relayed
  approval is a claim nothing authenticates; the maintainer removed them.

### Every Verify run starts from a fresh context

Verify's rulebook is the catalog agent `iwe-verifier`, so its verdict rests on
the code and the graph. `/agentdev:iwe-verify` routes a session's request to a
dispatched `iwe-verifier` and has `iwe-shipper`, already a fresh context, follow
the rulebook in place so it stays a leaf. The saved report is keyed by commit
and by a digest of the catalog files on disk, because an installed plugin is not
a Git checkout and a session can load a catalog that differs from the one the
commit holds; Verify refuses a dirty worktree so the commit fully names what was
judged. `/agentdev:iwe-verify` stays model-invocable because it mutates nothing
and the Implement loop invokes it.

Rejected:

- **Give `iwe-shipper` the Agent tool and nest the dispatch.** OpenCode refuses
  nested dispatch at its default depth.
- **Keep the rulebook in the skill behind a thin agent.** A session loading the
  skill would already hold the rules it should dispatch.
- **Look up the saved report in the `iwe-verifier` rulebook.** A hit would still
  cost a dispatch.
- **A handoff file committed for the Shipper.** Committing it changes the commit
  it fingerprints.
- **Key the report by tree or blob hashes of the plan's files.** Verify and Ship
  run on one commit, and file-scoped hashes miss changes a verification command
  can still depend on.

### The Implement session runs the loop, and every agent is a leaf

`iwe-implementer`, `iwe-verifier`, and `iwe-revision-evaluator` never dispatch,
so the loop runs on Claude Code and OpenCode without OpenCode's experimental
depth setting. The loop is written once, in the `iwe-implementer` rulebook. The
Plan rulebook is the `iwe-planner` agent, which the Implement session follows in
revise mode only, because `/agentdev:iwe-plan` is explicit-only. A revision is
evaluated after the Durable Knowledge Auditor, because the audit may rewrite the
text. The loop acts only on what the plan promised, which is what lets it
converge; post-merge behavior is a `**Closed by:**` task that Ship, not Verify,
refuses on, so Verify's saved report is the same for both callers.

Rejected:

- **Let `iwe-verifier` judge the revision.** Whether a new plan still serves the
  old one's outcome is a different question with its own rubric.
- **Reuse `Principal Engineer` as the evaluator.** It is advisory and can
  dispatch; the gate needs a leaf with a fixed verdict.
- **Evaluate before the audit.** The evaluator would approve bytes that never
  land.
- **Delta-scoped Verify rounds.** They treat the symptom; bounding the run and
  leaving CI to `pr-merge` remove the causes.
- **Run the loop inside a dispatched `iwe-implementer`.** It would need nested
  dispatch, and `iwe-implementer` is never dispatched.

### Adversarial review is its own agent, outside Verify

The maintainer decided that looking for ways to defeat a design asks a different
question from conformance, with findings that have no fixed end, so it lives in
`iwe-adversarial-reviewer`, outside Verify. The skill is model-invocable so the
Implement loop can run a planned review task.

Rejected:

- **Extend the Durable Knowledge Auditor.** It would hold two unrelated rubrics.
- **Run it inside every Verify round.** Findings outside the plan's contract
  would keep the loop from converging.
- **Make the skill explicit-only.** The Implement loop could not run a planned
  review task.

### IWE through the CLI, not MCP

The project owner decided that agents use the `iwe` CLI only. Every catalog
skill already drove the graph through it, and a registered server adds generic
prompts (`explore`, `review`, `refactor`) to every client's slash-command menu
that ignore this repository's schemas and collide with the catalog's own IWE
skills. `iwes`, the LSP server behind the editor extension, is unaffected.

Rejected:

- **Keep the server behind a filter that strips its prompts.** It keeps tools
  nobody calls, and the filter is a wrapper to maintain.
- **Disable it per user with `disabledMcpjsonServers`.** Every workspace and
  consumer would opt out separately, and the default would stay wrong.
- **Keep installing `iwec`.** Nothing registers it.

### The layout gives every write one owner

Parallel pull requests each write project state into the graph, and a conflict
costs a catch-up merge, a full CI run, and often a fresh AI review. GitHub
decides mergeability without `.gitattributes` merge drivers, and Git merges two
insertions cleanly only when an unchanged line separates them, so conflict
reduction has to come from the layout. `data/index.md` lists hubs and changes
only when a hub is added, so the graph stays an OKF bundle; it diverges only on
`status`, which duplicated `stage`.

Rejected:

- **`merge=union` on the log and hubs, or a custom merge driver.** GitHub ignores
  both, and union merges resurrect moved or deleted links.
- **A merge queue.** `main` does not require up-to-date branches, so no
  catch-up merge is caused by staleness.
- **Stage sections in hubs, sorted alphabetically.** Short sections keep
  conflicting, and every ship moves a link between sections.
- **A separate roadmap file.** Parallel ships edit adjacent lines at its head.
- **Dependencies (`after: [keys]`) as the order.** A partial order leaves
  independent work unordered.
- **Hubs generated from frontmatter.** It drops the browsable list and the
  editor tree, and adds a generator to maintain.
