---
type: spec
description: Behavioral contracts and handoffs for IWE's Explore, Capture, Plan, Implement, Verify, Ship, and adversarial review skills, and the graph conventions they write by.
sources:
- resource: .iwe/schemas/plan.yaml
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/plans/mvp.example.md
- resource: .agents/plugins/agentdev/bin/github_issue.py
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-capture/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-capture/agent-code/close-issue.py
- resource: .iwe/schemas/bug.yaml
- resource: .iwe/schemas/feature.yaml
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-explore/agent-code/fetch-issue.py
- resource: .agents/plugins/agentdev/skills/iwe-plan/agent-code/close-issue.py
- resource: .agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-new-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/bin/plan_predecessors.py
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-adversarial-reviewer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-adversarial-review/SKILL.md
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: .iwe/config.toml
- resource: .iwe/schemas/hub.yaml
- resource: .iwe/schemas/task.yaml
- resource: docs/knowledge/tests/test_hub_order.py
- resource: docs/knowledge/tests/test_rank_and_base_schemas.py
- resource: .github/workflows/validate-knowledge-base.yml
- resource: .agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-audit/SKILL.md
- resource: .iwe/schemas/okf.yaml
- resource: docs/knowledge/tests/test_banned_frontmatter_keys.py
- resource: py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md
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
verbatim in the task that applies it and SHALL never paraphrase it; when the
text is not at hand, Plan SHALL recover it from `.tmp/`, the conversation, or
the transcript and have the user confirm it before writing the task. Plan's
entry skill `/agentdev:iwe-plan` SHALL be explicit-only on Claude Code and
OpenCode.

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

#### Scenario: Approved text is not at hand

- **WHEN** a plan task would apply approved text that Plan cannot find in the
  conversation or in `.tmp/approved-wording-<slug>.md`
- **THEN** Plan stops before writing the task, recovers the text from `.tmp/`,
  the conversation, or the transcript, shows what it recovered, and writes the
  task only once the user confirms it is the text they approved

### Requirement: Plans express spec impact at risk-appropriate fidelity

The Plan skill SHALL record the intended spec impact in the plan's existing
`## Spec changes` section, SHALL scale detail with behavioral risk, and SHALL
keep that contract coherent when material decisions change. A structured delta
SHALL sit in a Markdown-tagged fence, so its Requirement and Scenario headings
stay out of the plan's own hierarchy. `ADDED` and `MODIFIED` SHALL carry the
complete post-change requirement with every surviving scenario, `REMOVED` SHALL
name the requirement and why its behavior is retired, and a rename SHALL be a
removal plus an addition, with no `RENAMED` operation. A spec the plan creates
SHALL stay a back-ticked key until Ship creates it. Plan SHALL keep each rule of
a durable spec in one requirement: before validation it SHALL read in full every
durable spec its normative outcome or structured delta touches.

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

#### Scenario: The chosen form is too weak for the change

- **WHEN** a plan records `None` or a normative outcome for a change that
  touches compatibility, acceptance criteria, security/privacy/data-loss
  behavior, or a requirement's scenario set
- **THEN** Verify reports a CRITICAL

#### Scenario: A MODIFIED block omits an unaffected scenario

- **WHEN** a MODIFIED requirement leaves out a scenario the change does not
  affect, and the plan does not name it as a deliberate removal
- **THEN** Verify reports a CRITICAL, because the merged spec would drop that
  scenario

#### Scenario: A plan introduces a spec

- **WHEN** a plan's `## Spec changes` names a spec that does not exist yet, in
  back-ticks, and supplies its planned contract
- **THEN** Verify accepts it and judges the implementation against that
  contract, and Ship creates the spec and replaces the key with a link

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
work closes. The Plan skill SHALL set that value when it files a plan, SHALL
declare `internal` when the work closes no feature and no bug, SHALL set every
feature the plan lists to `stage: accepted`, and SHALL set every bug the plan
lists to `stage: planned`. A plan revision that adds a bug to `release` SHALL
set it to `stage: planned`, and one that removes a bug SHALL return it to
`stage: pending`. Ship SHALL take the documents a plan closes only from that
value, SHALL never create a feature, SHALL write the `## Fix` of each bug it
marks done, and SHALL return each listed bug to `stage: pending` when it cancels
the plan.

#### Scenario: A plan implements a proposed feature

- **WHEN** Plan files a plan whose `release` lists a feature at
  `stage: proposed`
- **THEN** Plan sets the feature to `stage: accepted`

#### Scenario: A milestone aggregator plan is filed

- **WHEN** Plan files a milestone aggregator plan whose children are plans
- **THEN** the aggregator declares `release: internal`, and each child plan
  lists the features and bugs it closes

#### Scenario: A plan closes no document

- **WHEN** Ship ships a plan that declares `release: internal`
- **THEN** Ship marks the plan done and closes no feature or bug

#### Scenario: A plan declares features and bugs

- **WHEN** Ship ships a plan whose `release` lists feature and bug keys
- **THEN** Ship marks each feature implemented and each bug done, and writes
  each bug's `## Fix` describing the shipped fix and linking the plan

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

#### Scenario: Behaviour is visible only after merge

- **WHEN** a requirement can be observed only once the change is on the default
  branch
- **THEN** Plan writes a task for it carrying a `**Closed by:**` line naming who
  or what closes it

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
loop dispatches SHALL dispatch another; while a revision is drafted, the loop
may also dispatch the two agents `/agentdev:iwe-plan-review` names.

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
which `/agentdev:iwe-plan` follows in place. The Implement session SHALL follow
`iwe-planner` in its revise mode only, and SHALL revise a plan only by first
committing any pending edit to the plan file in a commit of its own, then
drafting the revision under the `iwe-planner` revise rules, including its
fresh-context audit and validation, changing only lines that answer the quoted
finding, leaving it uncommitted, and dispatching `iwe-revision-evaluator` with a
prompt carrying only the plan key and the finding the revision answers, quoted
as reported. It SHALL commit the revision only on the evaluator's `APPROVE`. On
`REJECT` or `ESCALATE` it SHALL restore the plan from `HEAD` and stop with a
report. The evaluator SHALL judge the uncommitted diff against the plan at
`HEAD`, SHALL edit, restore, and commit nothing, SHALL never approve a revision
that drops, narrows, defers, or accepts an exception to specified behavior,
changes `release`, or changes text the user approved, and SHALL reject a
revision with a hunk that answers no quoted finding or that adds or sharpens a
claim the code must newly meet.

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

#### Scenario: A plan edit is pending when a revision starts

- **WHEN** the plan file carries an uncommitted tactical correction, such as a
  refreshed anchor, and a finding takes the revision route
- **THEN** the Implement session commits that edit on its own before drafting,
  so the evaluator's diff holds only the revision and a restore from `HEAD`
  keeps the correction

### Requirement: Plans record intent, not the path taken to it

Plan documents SHALL record what is settled rather than the sequence of attempts
that settled it. `## Verification results` SHALL be a plan's only narrative
section. Implement SHALL route a finding that does not change the plan's intent
to its own document — `data/findings/`, `data/bugs/`, or `data/backlog/` —
rather than into the plan's `## Context` or `## Approach`, which state intent
and remain the Plan skill's to own. Every edit to a plan's intent sections SHALL
be reviewed through `/agentdev:iwe-plan-review` before the edit is validated:
audited for durable-knowledge residue by a reviewer holding no context beyond
the audit scope and the plan file, and checked by `iwe-ship-reviewer` in plan
mode for what Ship will need.

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

#### Scenario: A plan edit is checked for what Ship needs

- **WHEN** Plan creates or revises a plan and reaches validation
- **THEN** `iwe-ship-reviewer` in plan mode reports whether the plan gives Ship
  what it needs, and Plan resolves each finding before validating

### Requirement: Normal shipping requires a clean independent verification

The Ship skill SHALL run the report-only Verify workflow before normal shipping
state changes and SHALL refuse to ship while Verify reports any CRITICAL
finding. Verify SHALL remain independently invocable and SHALL not edit code or
project state. Verify's rulebook SHALL be defined once, as the catalog agent
`iwe-verifier`, and every Verify run SHALL start from a fresh context:
`/agentdev:iwe-verify` SHALL dispatch `iwe-verifier` with a prompt carrying only
the plan key or audit mode and the approvals quoted verbatim, whether the user's
session or `iwe-shipper` invokes it. Verify SHALL run a verification command
whose effects reach beyond the working tree only under a quoted approval that
names it, and otherwise SHALL stop before it and report the approval it needs.
`/agentdev:iwe-verify` SHALL be model-invocable on Claude Code and OpenCode.
Report-only is a rule of the `iwe-verifier` rulebook, not a tool boundary: the
agent holds the `Write` tool.

`/agentdev:iwe-verify` SHALL refuse to run on a dirty worktree, SHALL save each
report whose verdict is `Ready to ship`, `Blocked`, or `Audit` as the one saved
report for its plan or for audit mode under `.tmp/verify/`, keyed by the content
it judged and a digest of every file, as on disk, of the agentdev catalog the
skill runs from, and SHALL never save a `Needs decision` report. A plan's
content key SHALL cover the plan's body, without its frontmatter or
`## Ship review` and with each link resolved from the repository root, and the
committed content of every path the plan's links and code spans name; audit
mode's SHALL be the commit's tree. Only the skill's bundled `verify-cache.py`
SHALL write a saved report. It SHALL return the saved report, marked as saved
and without running any check or verification command, when that report's
content key and catalog digest are the current ones, unless the user's request
carries `--fresh`. The saved report SHALL record the request
`/agentdev:iwe-verify` was invoked with and the prompt `iwe-verifier` was
dispatched with, and neither SHALL be part of the key. A verification command
that leaves the worktree dirty SHALL be a CRITICAL finding.

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

#### Scenario: The user verifies a plan with an approval

- **WHEN** the user re-runs `/agentdev:iwe-verify <plan>` granting the approval
  the verifier reported, alongside other claims about the work
- **THEN** the dispatch prompt quotes the approval verbatim and leaves the other
  claims out, and `iwe-verifier` runs the approved command

#### Scenario: Ship dispatches Verify

- **WHEN** `iwe-shipper` reaches its Verify step and no saved report matches
- **THEN** it runs `/agentdev:iwe-verify`, which dispatches `iwe-verifier` with
  the plan key and the approvals the Shipper's prompt quotes, and only the
  report returns to the Shipper

#### Scenario: Ship reuses the Implement loop's report

- **WHEN** the Implement loop's Verify saved a report for the plan and
  `iwe-shipper` reaches its Verify step on a clean worktree whose plan body and
  named paths are unchanged, with the same active catalog
- **THEN** the skill returns the saved report, marked as saved, without running
  any check or verification command, and Ship proceeds on its verdict

#### Scenario: A commit leaves what Verify judged unchanged

- **WHEN** a commit since the save changes only files the plan does not name,
  the plan's frontmatter, or its location, as a squash merge or archiving does
- **THEN** the content key is unchanged and the saved report is returned

#### Scenario: No report is saved

- **WHEN** no saved report exists for the plan, as in a fresh container
- **THEN** Verify runs in full and saves its report

#### Scenario: What Verify judged or the catalog changed

- **WHEN** the content key or the active catalog digest differs from the saved
  report's
- **THEN** Verify runs in full and its report replaces the saved one

#### Scenario: The loaded catalog differs from the commit's

- **WHEN** the session runs an installed agentdev catalog whose files differ
  from the catalog the commit holds, and a report was saved for the same content
  under the commit's catalog
- **THEN** the digests differ and Verify runs in full

#### Scenario: The worktree is dirty

- **WHEN** `/agentdev:iwe-verify` is invoked with a tracked change or an
  untracked file Git does not ignore
- **THEN** it stops before any Verify step and reports the dirty worktree

#### Scenario: A report that needs a decision is not saved

- **WHEN** Verify reports `Needs decision` and the user re-runs it granting the
  approval
- **THEN** Verify runs again rather than returning the earlier report

#### Scenario: The user asks for a fresh run

- **WHEN** the user runs `/agentdev:iwe-verify <plan> --fresh` while a saved
  report matches
- **THEN** Verify runs in full and its report replaces the saved one

#### Scenario: The saved report records how Verify was invoked

- **WHEN** Verify saves a report
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

### Requirement: Adversarial review runs only when asked

The adversarial review SHALL be defined once, as the catalog agent
`iwe-adversarial-reviewer`, which `/agentdev:iwe-adversarial-review` dispatches
from a fresh context with a prompt carrying only the plan key, the target
(`plan` or `code`), and the user's approvals quoted verbatim. The agent SHALL
edit nothing and dispatch no agent, and every finding against code SHALL name
the plan claim it defeats, or none. On the `plan` target the agent SHALL look
for claims the design cannot keep, scenarios the plan misses, and limits a
promise does not state; on the `code` target, for inputs, states, orderings, or
actors under which the code does what the plan's claims rule out or fails to do
what they promise. The review SHALL run only on a person's request or a plan
task that runs it; Plan SHALL never invoke it, and SHALL add at most one such
task, closing or near-closing, targeting `code`. The skill SHALL be
model-invocable, so the Implement session can run that task. The Implement
session SHALL run it once per plan, after committing every earlier task. In the
Implement loop, a finding that defeats a plan claim SHALL take the code route,
and any other finding SHALL be filed through `/agentdev:iwe-capture`.

#### Scenario: A plan's claims are worth attacking

- **WHEN** Plan writes a plan whose claims guard a trust boundary or an
  integrity check
- **THEN** the plan may carry one closing or near-closing task that runs
  `/agentdev:iwe-adversarial-review <plan> code`, and no second one

#### Scenario: Planning does not start the review

- **WHEN** `/agentdev:iwe-plan` creates or revises a plan
- **THEN** it neither loads `/agentdev:iwe-adversarial-review` nor dispatches
  `iwe-adversarial-reviewer`

### Requirement: Ship waits for every dependency

The Ship skill SHALL, before Verify in normal shipping, read the stage of every
plan in the plan's `## Depends on` in the checkout's working tree, live or
archived, through `/agentdev:iwe-branch-name plan-state`, never on another
branch, and SHALL return a Ship blocker report naming each one that is not
`stage: done`, making no state change.

#### Scenario: Dependency shipped on the same branch

- **WHEN** a plan's dependency was shipped by an earlier commit on the branch
  Ship runs on, and is not yet `stage: done` on the default branch
- **THEN** Ship treats the dependency as shipped

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
behavior, SHALL preserve unaffected requirements, scenarios, and `## Rationale`
entries, SHALL complete and verify all required spec updates before marking work
done, and SHALL be safe to resume after a partial prior attempt.

#### Scenario: Existing behavior remains unaffected

- **WHEN** a shipped change modifies one requirement or scenario in an existing
  durable spec
- **THEN** Ship updates the changed behavior while preserving all unaffected
  requirements, scenarios, ordering, and `## Rationale` entries

#### Scenario: A decision is overturned

- **WHEN** a shipped plan replaces a decision a spec's `## Rationale` records
- **THEN** Ship rewrites that entry to state the new decision and lists the old
  one among its rejected alternatives

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
  duplicate `## Rationale` entries, archive moves, and release pages, and
  continues from the first incomplete operation

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
start the workflows. Every `iwe-*` catalog agent's description SHALL name the
skills that dispatch or follow it and SHALL state that it is never started on a
description match. The catalog SHALL carry no skill that implements or ships
more than one plan per request, and no rule that lets one session hand another
an approval or a step of a workflow. Ship SHALL always run as a dispatched
`iwe-shipper` whose prompt carries only the plan key, the operation, and the
user's approvals quoted verbatim, so its verification rests on the code and the
graph alone. `iwe-implementer` SHALL never be dispatched: Implement SHALL run in
the session that loaded its entry skill and SHALL take every decision from that
session's own user, and an approval that another session's message claims the
user gave SHALL not count as one. A dispatched `iwe-shipper` SHALL stop and
report at any point that needs a user decision it was not given. Nothing
authenticates who typed a message in the session's own conversation; this
requirement governs only approvals that another session's message claims.

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

### Requirement: Every ship is reviewed against Ship's obligations

`iwe-shipper` SHALL NOT commit a ship while a bug its plan's `release` lists has
no `## Fix`. After `iwe-shipper` ships a plan, `/agentdev:iwe-ship` and Plan
revise mode answering a Ship blocker report SHALL dispatch `iwe-ship-reviewer`
in ship mode with the plan key. When it reports gaps, they SHALL dispatch
`iwe-shipper` with the operation `fix` and the gaps quoted, which SHALL perform
only those operations without running Verify, and review again, for at most 3
fix rounds. `iwe-ship-reviewer` SHALL append the `## Ship review` checklist to
the plan only when every item is `confirmed` or `N/A`. The checklist SHALL be
fixed — no item added, dropped, reordered, or reworded — and its Verify,
plan-stage, and archive items SHALL never be `N/A`. A plan that already ends
with a `## Ship review` that holds SHALL keep it unchanged.

#### Scenario: a ship meets every obligation

- **WHEN** `iwe-ship-reviewer` finds every obligation met
- **THEN** the plan ends with a `## Ship review` whose every item is ticked
  `confirmed` or `N/A`.

#### Scenario: a ship leaves a gap

- **WHEN** `iwe-ship-reviewer` reports a listed bug with no `## Fix`
- **THEN** `iwe-shipper` runs `fix` for that gap alone, without Verify, and the
  plan is reviewed again.

#### Scenario: gaps outlast three rounds

- **WHEN** a gap remains after 3 fix rounds
- **THEN** Ship reports the gap and the plan has no `## Ship review`.

#### Scenario: an always-applicable item has nothing to confirm

- **WHEN** a shipped plan has no saved Verify report, is not `stage: done`, or
  is not archived
- **THEN** `iwe-ship-reviewer` reports that item as a gap rather than `N/A` and
  writes no `## Ship review`.

#### Scenario: a plan is reviewed before implementation

- **WHEN** `iwe-ship-reviewer` runs in plan mode
- **THEN** it reports whether the plan gives Ship what it needs and changes
  nothing.

### Requirement: The IWE workflow skills ship in the agentdev catalog

The IWE workflow skills SHALL ship from `.agents/plugins/agentdev/skills/iwe-*/`
and be invoked as `/agentdev:iwe-<name>`, with no copy under `.claude/skills/`.
A skill SHALL reach a sibling skill by its namespaced invocation and its own
bundled code as `agent-code/<file>`, never by a repository-relative path, and
`validate_agent_files` SHALL report every reference inside the plugin that
resolves outside the plugin root.

#### Scenario: A skill hands off to a sibling

- **WHEN** an IWE skill hands work to another IWE skill
- **THEN** it names the sibling as `/agentdev:iwe-<name>`, which resolves from
  the installed catalog in a consuming project

### Requirement: The durable-knowledge audit reads from a fresh context and changes nothing

The `Durable Knowledge Auditor` agent SHALL take only the file to audit and the
audit scope as inputs, SHALL hold no `Edit` or `Write` tool, SHALL invoke
`/agentdev:iwe-audit` as its only rulebook, and SHALL return that skill's report
verbatim. `/agentdev:iwe-audit` SHALL audit the graph's specs, findings, guides,
features, and `product.md`, code comments, and outside the graph `README.md`,
`AGENTS.md`, skill and agent definitions, and docstrings; it SHALL not audit
`data/bugs/`, `data/releases/`, `data/archive/`, or commit messages. In diff and
plan scope it SHALL report without editing. Its durable and not-durable
definitions SHALL match the wording of Best Practice 8 in the repository
`AGENTS.md`, so the skill states its criteria without a reference outside the
plugin.

#### Scenario: A plan draft is audited

- **WHEN** a caller dispatches the `Durable Knowledge Auditor` on a plan in plan
  scope
- **THEN** it returns the `/agentdev:iwe-audit` report table and the plan file
  is unchanged

#### Scenario: A commit message reads as a logbook

- **WHEN** `/agentdev:iwe-audit` runs over a change that includes commit
  messages
- **THEN** it leaves the commit messages out of the audit, since
  `/agentdev:git-commit` owns them

### Requirement: Plan review runs both reviewers from fresh contexts and changes nothing

`/agentdev:iwe-plan-review <plan>` SHALL dispatch the
`Durable Knowledge Auditor` and `iwe-ship-reviewer` in one message, forwarding
no conversation turns: the auditor's prompt SHALL carry only the plan file path
and the scope `plan`, and the reviewer's only the plan key and the mode `plan`.
It SHALL perform no review step itself, SHALL return both reports verbatim under
each agent's name, and SHALL edit no file and commit nothing; applying the
verdicts belongs to its caller. The skill SHALL be model-invocable, so the
`iwe-planner` rulebook can run it in every mode.

#### Scenario: Plan reaches its review step

- **WHEN** `iwe-planner` reaches its review step on a created or revised plan
- **THEN** both agents are dispatched in parallel with only those prompts, both
  reports return unchanged, and the plan file is unchanged until Plan applies
  them

### Requirement: Capture files complete inbox documents

The Capture skill SHALL be the only writer of new bug, proposed-feature, and
backlog-task documents, SHALL refuse a document missing any frontmatter field or
body section `SCHEMA.md` requires for its type, SHALL check the graph for a
likely duplicate before filing, SHALL file a feature at `stage: proposed` and
never promote it, SHALL file a bug at `stage: pending` — or at `stage: done`
with its `## Fix`, under `data/archive/next-release/bugs/`, when the same change
fixed it — and a task at `stage: pending`, and SHALL link every filed document
except a bug filed at `stage: done` from its hub and end with `iwe normalize`
and `iwe schema validate` passing. Capture SHALL file no bug whose Reproduction
or Root cause is a bare "unknown": a section not yet known states what is known,
the hypotheses eliminated and what eliminated each, and links the backlog task
whose spike settles it. No bug section SHALL state lifecycle, which `stage`
alone carries, and a bug's `severity` SHALL measure impact, not urgency, and set
nothing, `rank` included.

#### Scenario: A bug's root cause is not yet known

- **WHEN** Capture is invoked for a bug whose Root cause reads only "unknown"
- **THEN** Capture writes nothing and asks for what is known, the hypotheses
  eliminated, and the backlog task whose spike settles it

#### Scenario: A complete item is captured

- **WHEN** Capture is invoked for a bug, feature, or task whose required
  sections and fields are all supplied, and no likely duplicate exists
- **THEN** Capture writes the document at its lane's key with the `stage`
  `SCHEMA.md` derives for it, stamps `sources`, links it from its hub at its
  sorted position unless it is a bug filed at `stage: done`, and validates the
  graph

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

### Requirement: Agents reach the graph through the iwe CLI

Every IWE skill and agent in the catalog SHALL read and write the knowledge
graph through `iwe` commands run from the repository root, and SHALL not assume
`mcp__iwe__*` tools exist. The repository SHALL register no IWE MCP server, and
the `dev_tools` role SHALL install `iwe` and `iwes` from the IWE release tarball
and not `iwec`.

#### Scenario: The image installs IWE

- **WHEN** the `dev_tools` role installs the IWE release
- **THEN** `iwe` and `iwes` are installed and `iwec` is not

### Requirement: Work-item state and order live in each item's frontmatter

A plan's, bug's, or backlog task's `stage`, `priority`, `completed`, and `rank`
SHALL live only in its own frontmatter. Active plans, open bugs, and pending
tasks SHALL share one build order: an optional `rank` that the plan, bug, and
task schemas require to be a positive integer, lower first, read by
`iwe find --filter '{rank: {$exists: true}}' --sort rank:1`, with unsequenced
work a separate query on `rank: {$exists: false}`. Plan SHALL set a new plan's
`rank` to the midpoint of its neighbours' and edit no other document's `rank`;
whoever closes an item SHALL remove its `rank`. Equal ranks SHALL be valid, and
the knowledge-base workflow SHALL warn about them without failing. Every hub
`[schemas.hub]` binds SHALL be one flat list of inclusion links, with no `##`
sections, sorted by member key with any `YYYYMMDD-` prefix removed, and SHALL be
edited only when a member is created, archived, or renamed.

#### Scenario: A rank is not a positive integer

- **WHEN** a plan, bug, or task carries a `rank` of zero, a negative number, or
  a non-integer
- **THEN** `iwe schema validate` fails and names the document

#### Scenario: Two items share a rank

- **WHEN** two ranked items carry the same `rank`
- **THEN** the knowledge-base workflow emits a warning naming both keys and
  passes

#### Scenario: A hub link is out of order

- **WHEN** a hub lists a member whose key, without its date prefix, sorts before
  the member above it
- **THEN** `docs/knowledge/tests/test_hub_order.py` fails and names that link

#### Scenario: A hub gains a section

- **WHEN** a hub carries a `##` heading
- **THEN** `iwe schema validate` fails and names the hub

### Requirement: Workflow improvements preserve the IWE and OKF model

The strengthened skills SHALL continue to use IWE's single-plan-document
workflow, graph links, durable specs, existing stage conventions, `sources`
attribution, and schema validation. Risk-scaled spec deltas SHALL remain
embedded planning content without introducing OpenSpec change bundles, stores,
separate delta files, or a claimed programmatic delta application engine. The
graph SHALL remain a conformant OKF v0.2 bundle — `data/index.md` lists the
hubs, and the `okf` and `okf-index` schemas check every document — and SHALL
diverge from OKF only where OKF costs merges or upkeep. No document under
`data/` SHALL set OKF's optional `status`, because `stage` is the lifecycle
field, nor OKF's `generated` or `verified`, because source control records when
and by whom a document changed. The `banned-frontmatter-keys` pre-commit check
SHALL reject a document that sets any of them.

#### Scenario: Updated skills write project memory

- **WHEN** an updated skill creates or meaningfully changes an IWE document
- **THEN** it follows the existing OKF metadata, graph membership,
  normalization, validation, and commit requirements defined by the workspace

#### Scenario: A document sets a banned frontmatter key

- **WHEN** a document under `data/` carries `status`, `generated`, or `verified`
- **THEN** the `banned-frontmatter-keys` check fails and names the document and
  the key

#### Scenario: The index loses its OKF shape

- **WHEN** `data/index.md` departs from the shape its OKF schema defines
- **THEN** `iwe schema validate` fails and names the file

### Requirement: Each kind of knowledge has one home

The graph SHALL hold behaviour only in `data/spec/` requirements, the decision
in force and the alternatives it rejected only in the `## Rationale` section of
the spec that owns the behaviour, a finding only in `data/findings/`, and a
procedure only in `data/guides/`. The schemas SHALL reject a document of type
`architecture` outside `data/archive/`. A feature SHALL be a proposal: outside
`data/archive/` its `stage` is `proposed` or `accepted`, and the `ship-records`
check SHALL fail any other. Nothing checks mechanically that a `## Rationale`
states no behaviour; the Durable Knowledge Auditor and review judge it.

#### Scenario: An architecture note is written

- **WHEN** a document outside `data/archive/` carries `type: architecture`
- **THEN** `iwe schema validate` fails and names the document

#### Scenario: An implemented feature is left in place

- **WHEN** a feature under `data/features/` is at `stage: implemented`
- **THEN** the `ship-records` check fails and names the document

### Requirement: Closed work is distilled and archived by release

Whoever sets a plan, bug, or backlog task to `stage: done` or
`stage: cancelled`, or a feature to `stage: implemented` or `stage: cancelled`,
SHALL, in the same change, move it with `iwe rename` to
`data/archive/next-release/<type>/` and remove its hub link. Before Ship moves a
plan, it SHALL write the plan's decision in force and its rejected alternatives,
and each closed bug's lasting root cause, into the `## Rationale` of the spec
that owns the behaviour. The release cut SHALL move every document under
`data/archive/next-release/` to `data/archive/<X.Y.Z>/`, keeping the type
subfolders. The folder SHALL be the only record of a document's release: no
document SHALL carry `released`. Every archived document SHALL pass the schema
of its type. The `ship-records` check SHALL fail a closed document outside
`data/archive/` and an open one inside it.

#### Scenario: A plan ships

- **WHEN** Ship marks a plan done
- **THEN** the plan and each feature and bug it closed are under
  `data/archive/next-release/`, no hub links them, and every link to them
  resolves

#### Scenario: A plan made a decision

- **WHEN** Ship ships a plan whose `## Approach` records a decision and a
  rejected alternative for behaviour a spec owns
- **THEN** that spec's `## Rationale` states the decision and the rejected
  alternative before the plan is moved

#### Scenario: A release is cut

- **WHEN** Ship cuts release `X.Y.Z`
- **THEN** every document that was under `data/archive/next-release/` is under
  `data/archive/X.Y.Z/`

#### Scenario: A closed document is left in place

- **WHEN** a commit stages a plan, bug, or task at `stage: done` or
  `stage: cancelled` outside `data/archive/`
- **THEN** the `ship-records` check fails and names the document

#### Scenario: An archived document breaks its schema

- **WHEN** an archived plan carries a `stage` its schema does not allow
- **THEN** `iwe schema validate` fails and names the document

### Requirement: Release notes are written from the spec diff

The release cut SHALL write the release page from the difference in the
requirements and scenarios of `data/spec/` between the commit that added the
previous release page and the cut, ignoring `## Rationale`. The page SHALL say
in plain language what changed, grouped by theme, with a Removed section for
behaviour that went away, an Upgrade notes section when a change requires
action, and a Fixed section listing the titles of the bugs in the release's
folder. The page SHALL hold no Markdown link, and the `ship-records` check SHALL
fail one that does. The cut SHALL read the release's archived plans only to
settle what the diff leaves unclear, and SHALL report each change it could not
settle and leave it off the page. No skill SHALL edit a release page after its
cut; nothing checks that mechanically. The graph SHALL hold no `data/log.md`.

#### Scenario: A requirement changed between cuts

- **WHEN** a requirement's statement or a scenario differs between the previous
  cut and this one
- **THEN** the release page says what changed in it, not only that it changed

#### Scenario: A requirement left a spec

- **WHEN** a requirement present at the previous cut is absent at this one and
  an archived plan of the release retired the behaviour
- **THEN** the release page lists the behaviour under Removed

#### Scenario: The diff does not say why

- **WHEN** a requirement left a spec and no archived plan of the release says
  whether the behaviour was retired or moved
- **THEN** the cut reports the requirement and leaves it off the page

#### Scenario: Only rationale changed

- **WHEN** the only difference in a spec between the cuts is under
  `## Rationale`
- **THEN** the release page does not mention the spec

#### Scenario: A release page links a document

- **WHEN** a commit stages a release page holding a Markdown link
- **THEN** the `ship-records` check fails and names the line

## Rationale

### Workflow rulebooks live in catalog agents

The Plan, Implement, Verify, and Ship rulebooks are the catalog agents
`iwe-planner`, `iwe-implementer`, `iwe-verifier`, and `iwe-shipper`; the skills
that start them carry no rules of their own. A gated skill cannot carry a
rulebook another context needs: Claude Code refuses a gated skill to the Skill
tool in every context, subagents included, and withholds it from an agent's
`skills:` preload, so the rulebook has to sit where an ungated route reaches it.

Rejected:

- **Preload the gated skill into the agent.** Claude Code withholds a gated
  skill from an agent's `skills:` preload, so the agent starts without its
  rulebook.
- **Keep the rulebook in the gated skill and have a subagent read its file.**
  The read succeeds, but the Skill tool's refusal tells the model not to
  replicate the workflow by other means, so a model may rightly refuse, and one
  that complies has bypassed the gate.
- **Workers follow the rulebook file without loading the skill.** A worker that
  tried the gated skill first has seen that refusal, so the route depends on
  nobody ever mentioning the skill.
- **Keep the Verify rulebook in the skill behind a thin agent**, as the Durable
  Knowledge Auditor does with `iwe-audit`. The skill would be both the rulebook
  and the entry point that must dispatch, so a session loading it already holds
  the rules it would run inline.

### Ship is gated; Implement and Verify are model-invocable

Ship's entry skill is explicit-only, because a stray Ship run reaches the
remote. Plan's is explicit-only too. Implement's is model-invocable: it needs a
named active plan whose dependencies are done or in review and asks when the
plan is ambiguous, so a stray match has nothing to build, and Plan and Explore —
the sessions where a stray start could happen — never name it. Verify mutates
nothing and the Implement loop invokes it, so a gate would protect nothing and
block that loop. The adversarial review skill is model-invocable for the same
reason: the Implement loop runs its planned task. Capture's is model-invocable
so that Implement can file a deferred task or a defect mid-run without stopping
for the user.

Rejected:

- **Drop the gate and rely on descriptions, for Ship.** An ungated skill is
  listed to the model with its description on every harness, so a description
  match can start Ship from Explore — for example after a partial answer closes
  a plan's open question.
- **A self-checking skill or a harness hook as the gate.** A skill that checks
  who invoked it is a prompt-level check a model can argue past. A `PreToolUse`
  hook's input names the tool call, not the skill or request behind it, so it
  cannot tell a requested dispatch from a stray one without parsing the
  transcript, and it needs one implementation per harness.
- **A separate model-invocable Implement entry skill that runs only on a
  coordinator's request.** Its description is still listed to the model, and the
  coordinator check is the same prompt-level self-check.
- **Make `/agentdev:iwe-verify` or `/agentdev:iwe-adversarial-review`
  explicit-only.** Either would block the Implement loop and protect nothing,
  since both are report-only.

### Implement builds on a dependency in review; Ship does not ship ahead of it

Implementation may run ahead of an unshipped dependency that has an open pull
request, by stacking on that pull request; shipping may not run ahead of it.

Rejected:

- **Keep Implement's dependency gate.** It serializes every dependent plan
  behind its dependency's full implement, review, merge, and ship cycle.

### Ship and Verify run from a conversation-free prompt; Implement runs in place

Ship and Verify verdicts must rest on the code and the graph, never on what a
conversation asserted, so both always run as dispatched agents whose prompt
carries only the plan key, the operation or mode, and approvals quoted verbatim.
An approval they need comes back in the report and the user re-runs the skill.
Implement must ask the user about ambiguity and material deviations, so it runs
in the session that loaded it and is never dispatched; nothing authenticates a
sender, so an approval another session's message claims is not one. Every caller
of Verify, `iwe-shipper` included, goes through `/agentdev:iwe-verify`, so only
the report enters the Shipper's context ahead of its graph changes.

Rejected:

- **Have `iwe-shipper` follow the `iwe-verifier` rulebook in place.** It puts
  the whole Verify run in the Shipper's context ahead of its graph changes.
- **Have `/agentdev:iwe-ship` dispatch `iwe-verifier` before the Shipper.**
  Every other route that dispatches the Shipper, such as Plan answering a Ship
  blocker report, would need the same step.
- **Coordinator skills that implement or ship every plan in turn.** A
  coordinator needs a dispatched Implementer that stops at every decision and a
  route for relaying the user's answers to it, and a relayed approval is a claim
  nothing authenticates. A plan is implemented and shipped one request at a
  time.

### A saved Verify report is reused by content and catalog digest

A Verify run is costly and stochastic: run again on the same code, it can raise
new findings that were not there before. A saved report is therefore reused for
as long as what it judged is unchanged, keyed by the plan's body and the content
of every path the plan names, not by the commit. A commit outside that set, a
merge from the base branch, a squash merge, or the plan's archiving keeps the
verdict. The plan names what its claims rest on, so a change to code it never
names can leave a stale report; `--fresh` forces a new run. Audit mode judges
the whole workspace, so its key is the commit's tree. Verify refuses a dirty
worktree, so the committed content is what was judged. The catalog digest hashes
the files on disk, because an installed plugin is not a Git checkout and a
session can load a catalog that differs from the one the commit holds. The
lookup and save live in a script bundled with the skill, the one place every
caller reaches on every harness.

Each plan keeps one saved report, overwritten, because only the latest report is
ever looked up. The user's approvals are recorded in the report but are not part
of its key: an approval changes a verdict only by unblocking a command, and a
run blocked on a missing approval ends in `Needs decision`, which is never
saved. `verify-cache.py` writes a `.gitignore` holding `*` into `.tmp/verify/`,
so a save never dirties the worktree Verify refuses to run on, even in a
consuming repository that does not ignore `.tmp/`. A saved report is not reused
across a fresh container, and trust in `.tmp/verify/` rests on the rule that
only the skill's script writes it, not on any protection against a hand-written
file.

Rejected:

- **One saved report per commit.** Reading an older report is a different
  feature, incremental re-verify; the reuse check needs only the latest.
- **Look up the saved report in the `iwe-verifier` rulebook.** A hit would still
  cost a dispatch.
- **A handoff file the Implement side commits for the Shipper.** Committing it
  changes the commit it fingerprints, and committing project state contradicts
  report-only Verify.
- **Key the report by the commit.** Any commit, even one that touches nothing
  the plan names, forces a new run whose findings can differ on the same code,
  and a squash merge discards every saved verdict.
- **Key a plan's report by the commit's tree.** It survives a squash merge, but
  an unrelated change anywhere still forces a new run.

### The Verify report is shown verbatim and routed by finding ID

The report is the deliverable of a fresh context, so every caller shows it
verbatim: a summary is a paraphrase of that verdict, and a path under
`.tmp/verify/` is something the user cannot follow in chat. A Ship blocker
report routes a CRITICAL by its `C<n>` ID because an ID is short and stable
within one report, while a quoted first line is long and breaks when the
verifier rewords it. IDs are scoped to one report and restart at 1 in each run,
so nothing refers to a finding by ID across reports or Verify rounds.

Rejected:

- **A summary plus the saved report's path.** It paraphrases the verdict and
  points the user at a file they cannot open from the conversation.

### The Implement loop runs in the Implement session with leaf agents

The verify, fix, and revise loop is written once, in the `iwe-implementer`
rulebook, and runs in the Implement session; `iwe-verifier`,
`iwe-revision-evaluator`, and `iwe-adversarial-reviewer` dispatch nothing, so
the loop needs no nested dispatch. Issue closing is reachable only from Plan's
create mode, so its script stays bundled with `/agentdev:iwe-plan` while the
Implement session follows `iwe-planner` in revise mode only.

Rejected:

- **Run the loop inside a dispatched `iwe-implementer`.** It would need nested
  dispatch, and `iwe-implementer` is never dispatched.

### A plan revision is drafted, audited, evaluated, then committed

A fresh-context `iwe-revision-evaluator` judges the final, audited text of a
revision against the plan at `HEAD` and returns a fixed verdict, so the
Implement session can continue past a finding without the user only when every
specified behaviour survives.

Rejected:

- **Let `iwe-verifier` judge the revision.** Verify checks code against the
  plan; whether a new plan still serves the old one's outcome is a different
  question with its own rubric.
- **Reuse the Principal Engineer agent as the evaluator.** It is advisory and
  can dispatch agents; the gate needs a leaf that returns a fixed verdict.
- **Evaluate before the audit.** The audit may rewrite the text, so the
  evaluator would approve bytes that never land.

### The loop acts only on what the plan promised

Verify is a conformance check, so the Implement loop converges once the code
meets the plan's contract, and the run is bounded by recurrence, three rounds,
and one approved revision. CI belongs to `pr-merge`, which gates every merge on
it. Verify accepts a CI job as evidence without a run on the current head
because a task citing a CI run cannot close before the pull request exists, and
every fix commit would make the cited run stale. A verification search for
leftover text covers only the files the plan changes, because a repository-wide
search reads other plans' files and fails on text this plan did not change.
Ship, not Verify, refuses while a `**Closed by:**` task is unticked, so Verify's
saved report is the same for both callers.

Rejected:

- **Verify treats an observation as CRITICAL only when Ship calls it.** The
  saved report would differ by caller, and Ship reuses the loop's report.
- **Delta-scoped Verify rounds.** They treat the symptom; restricting findings
  to the plan's contract and leaving CI to the merge gate remove its causes, CI
  timing and unbounded probing.

### Adversarial review is its own agent, outside Verify

Looking for ways to defeat a design or its code asks a different question from
conformance, with its own rubric, and its findings have no fixed end. It lives
in the report-only leaf `iwe-adversarial-reviewer`, run from a fresh context
only when asked, and a `code` finding names the claim it defeats so the caller
can tell a broken promise from a weakness the plan never claimed to cover.

Rejected:

- **Extend the Durable Knowledge Auditor.** It would hold two unrelated rubrics:
  durable text and design attacks.
- **Run it inside every Verify round.** Findings outside the plan's contract
  would keep the loop from converging.

### Agents use the iwe CLI, not an IWE MCP server

Every IWE skill and agent drives the graph through `iwe` commands, so the MCP
tools duplicated an interface nothing used. A registered server also adds its
prompts (`explore`, `review`, `refactor`) to every client's slash-command menu;
they ignore this repository's schemas and conventions and collide with the
catalog's own IWE skill names. `iwes`, the LSP server behind the IWE editor
extension, is unaffected.

Rejected:

- **Keep the server behind a filter that strips its prompts.** That keeps the
  tools nobody calls, and the filter becomes a wrapper to maintain.
- **Disable it per user with `disabledMcpjsonServers`.** Every workspace and
  every template consumer would need to opt out separately, and the default
  would stay wrong.
- **Keep installing `iwec`.** With nothing registering it, the binary is dead
  weight in the image.

### A bug records its own fix; a task has no bug lifecycle

A bug keeps its own `## Fix` section because bugs reach `done` by two routes,
and many are fixed directly by a pull request no plan references; only the bug's
own section records those fixes. Backlog tasks do not get the bug lifecycle: a
task's job ends when a plan grows from it, so `planned` means only that a plan
owns a bug. `## Key references` is not required of a bug, because its anchors
rot with the code while frontmatter `sources` already names the paths the bug
derives from.

Rejected:

- **Drop `## Fix` and send the reader to the fixing plan through
  `iwe find --references`.** A bug fixed without a plan is left with no record
  of its fix.

### Work-item state, order, and hubs are laid out to avoid merge conflicts

Parallel pull requests each write project state, and a spot every pull request
edits turns parallel work into conflicts, each costing a catch-up merge, a full
CI run, and often a fresh AI review. So a state change edits only the item's own
file, the build order is a `rank` query rather than a file, and hubs are flat
lists sorted by key, where two pull requests conflict only when their new
members sort next to each other. GitHub decides mergeability without
`.gitattributes` merge drivers, and Git merges two insertions cleanly only when
an unchanged line separates them, so conflict reduction has to come from the
layout, not from merge tooling. Hubs stay as browsable lists and as the tree the
IWE editor views show; queries select documents by `type` and frontmatter, not
by hub membership.

Rejected:

- **`merge=union` on hubs.** GitHub ignores it, so it saves only a local
  resolution; it also keeps a moved link in both places, resurrects a deleted
  link, and can duplicate a heading both sides add.
- **A custom merge driver.** The same GitHub limitation, and every clone would
  need the driver registered in its Git configuration.
- **A merge queue.** `main` does not require branches to be up to date, so no
  catch-up merge is caused by staleness; a queue cannot enqueue a conflicting
  pull request and adds a CI run per queued pull request.
- **Stage sections in hubs, sorted alphabetically.** Short sections and priority
  buckets keep conflicting, and every ship still moves a link between sections.
- **A roadmap file listing the sequence.** Work ships from the head of the
  sequence, so parallel ships always edit adjacent lines.
- **Dependencies (`after: [keys]`) as the order.** A dependency set is a partial
  order and leaves independent work unordered.
- **Hubs generated from frontmatter, not committed.** It drops the browsable
  list and the editor tree and adds a generator to maintain.

### Explore interviews one decision at a time by default

Settling open questions one topic and one decision at a time is Explore's
default behaviour, so every exploration gets it without the user asking.

Rejected:

- **A separate interview skill or an opt-in mode.** A second entry point would
  leave the default unchanged.

### Approved wording is carried in `.tmp/` and inlined in the plan

Approved text is the deliverable, and conversation is not storage, so Explore
writes it to `.tmp/approved-wording-<slug>.md` at approval time and Plan copies
it into a fenced block under the task that applies it. `.tmp/` is the scratch
directory `AGENTS.md` mandates and is gitignored; once a plan absorbs the text,
the plan is its durable copy. The obligation is split: Explore writes and Plan
inlines, because approved wording also reaches Plan without Explore. No CI gate
can see `.tmp/`, so the verbatim check is one a session runs.

Rejected:

- **A `data/drafts/` hub.** The hub set is closed, a drafts hub would be the
  only one whose members are temporary and would need a deletion lifecycle, and
  a second copy would drift from the plan.
- **Carrying approved text across the plan-to-implement and implement-to-ship
  handoffs.** Those sessions start from the written plan alone, so the plan is
  already the only channel.

### Plan deltas adopt the notation, not an application engine

A behavior-changing plan carries a reviewable contract before implementation,
scaled to risk: a delta only where a prose outcome could hide a disagreement.
The delta is intent inside the one plan document; the durable spec describes
released behavior until Ship merges it by judgment, accounting for every
operation. Determinism is not claimed.

Rejected:

- **A delta in every plan.** It taxes refactors and docs-only work with ceremony
  that resolves nothing.
- **A separate change bundle, store, or delta file.** A second lifecycle would
  duplicate the plan's own.
- **A parser that applies deltas.** Operation order, conflict rules, and
  postconditions would be machinery for a merge Ship performs by reading.
- **Reconciling a stale delta from the implementation.** It erases the reviewed
  contract; a material mismatch returns to Plan revision.

### A plan's release impact is a frontmatter field chosen when it is written

The maintainer decided that a plan's release impact is chosen and reviewed when
the plan is written. It lives in the `release` frontmatter field because the
plan schema can require a frontmatter field only while a plan is active.

Rejected:

- **A `## Release` body section.** The schema cannot require a body section only
  on active plans, so enforcement would fall to the skills.
- **Verify cross-checking `release: internal` against a non-empty
  `## Spec changes`.** A plan can change specified behaviour without closing a
  feature or a bug.
- **A `RENAMED` operation.** A fourth operation carries identity semantics that
  only a parser would act on; a removal plus an addition says the same thing.

### A CRITICAL blocks Ship with no override

Normal Ship runs Verify itself, so verification is not a step a user can forget,
and a CRITICAL refuses the ship mechanically. A plan with a CRITICAL stays
active for fixes, is revised to drop the offending work through Plan's revise
mode, or is cancelled; a known-false durable claim is never shipped.
Cancellation is exempt from Verify because it records abandonment, not behavior.
The gate only blocks defects Verify has a rule for; a defect outside its rules
passes it.

Rejected:

- **A user override of a CRITICAL.** It would ship a durable claim known to be
  false.
- **Cancelling the plan over one undone task.** Out of scale; a revision that
  drops the task is the proportionate route.
- **Ship running its own copy of Verify's checks.** Two copies of one rulebook
  drift.
- **Softening the no-override rule so a task the user declined can ship.** A
  revision that drops the task through Plan's revise mode, which asks the user
  because dropping a task is a material scope change, keeps the gate whole.

### The durable-knowledge audit is an isolated leaf

Session residue survives because the writer reads its draft through the session
that produced it, so the audit runs in an agent that never saw the work and
cannot edit what it reads, and the rule lives in one rulebook, `iwe-audit`.
Every plan-intent edit funnels through Plan, so one gate there covers create,
revise, and every route back to revise.

Rejected:

- **A self-audit step inside Plan's own context.** It re-reads the polluted
  context.
- **Each caller inlining the rule into a spawned subagent.** The rule drifts at
  every call site.
- **Making `## Context` and `## Approach` read-only to Implement.** Genuine
  intent corrections arrive mid-implementation; the material-deviation route
  handles them.
- **Detecting narration mechanically in the plan-shape gate.** Narration has no
  shape: a length or prose-ratio heuristic fires on long plans and misses a
  short dense logbook.

### Issue closing has one implementation in `bin/`

Plan and Capture both close a GitHub issue, so the closing logic lives once in
the shared `bin/github_issue.py`, and each skill's `close-issue.py` only names
its own command and arguments.

Rejected:

- **Capture calling Plan's close script.** It couples one skill to another's
  `--plan` contract.
- **A copy of the closing logic per skill.** Two copies of one algorithm drift.

### The no-logbook rule lives in the root AGENTS.md with two tests

Best Practice 8 in the repository `AGENTS.md` states the rule because logbook
residue appears in every kind of text an agent writes, not only in the graph;
`docs/knowledge/AGENTS.md` keeps only the places where narrative is the format.
Its two tests ask different questions: "rewritten from scratch" asks whether a
fact is durable, "gone right the first time" asks whether a sentence is a
logbook trace, and a durable fact can still be phrased as narration.

Rejected:

- **The rule under the graph manual only.** Code comments, skills, and pull
  request bodies would fall outside it.

### Revision and spec synchronization belong to Plan and Ship

Plan's revise mode owns every change to an active plan and Ship is the only
workflow that writes durable specs, which keeps one owner per kind of state:
Explore investigates, Plan owns planning state, Implement records tactical
deviations, Verify proves, Ship merges specs.

Rejected:

- **Separate Update and Sync skills.** They add entry points and split the
  ownership each existing skill holds.

### A revision keeps its plan only while the plan's intent holds

A revision stays in the same plan only while topic, intended outcome, and
verification story remain materially the same. A plan's completed tasks and
their evidence mean what they mean against that intent; replacing it in place
leaves them claiming something nobody checked.

Rejected:

- **Revising any active plan in place, whatever the change.** It silently
  rewrites the meaning of work already ticked.

### Ship merges specs from verified evidence before it moves any state

Ship derives each durable spec update from the plan's `## Spec changes` and
Verify's implementation evidence, validates the merged specs, and only then
moves plan, feature, bug, and release state, so a plan is never recorded as done
while a spec it touched still describes the old behaviour.

Rejected:

- **Overwriting a spec from plan prose.** A plan can be stale, and a whole-spec
  overwrite erases scenarios the change never touched.
- **Moving stages before the spec merge is verified.** A failed merge then
  leaves a plan marked done that is not.

### A spec contradiction found outside a plan becomes a bug

A spec-versus-code contradiction found with no plan in flight is handed to
Capture as a bug, because Ship acts only on a selected plan's `## Spec changes`
and has nothing to merge without one.

Rejected:

- **Handing the contradiction to Ship.** No plan carries the intent Ship would
  merge.

### The IWE workflow skills carry an iwe prefix in the agentdev catalog

The maintainer placed the IWE workflow skills in the `agentdev` catalog, so one
catalog is versioned and installed, accepting that `agentdev` ships a workflow
that assumes an IWE graph. The `iwe-` prefix stays although `agentdev:` already
namespaces, because `plan`, `ship`, and `verify` alone would read as peers of
the `pr-*` skills in the same directory.

Rejected:

- **A separate `iwe` plugin.** A second catalog to version and install.
- **Keeping the skills under `.claude/skills/`.** Every template consumer would
  inherit them outside the supported install path.

### Explore's evidence gate opens its stance

The gate sits at the top of Explore's stance, so it applies before any proposal
is formed.

Rejected:

- **Extending the `Evidence before argument` interview rule.** That rule runs
  only once open questions exist, which is after an over-scoped proposal has
  been written.

### Workflow skills get no live-model end-to-end test

An end-to-end test of the workflow skills is not kept unrun: an unrun test rots
and still reads as coverage. The ban names the agentdev workflow skills only;
the self-improve plugin's `smoke`, `pty`, and `auto_memory` live-session tests
are kept by the maintainer's decision.

Rejected:

- **No live-model test anywhere in the repository.** It would remove the
  self-improve live-session tests the maintainer kept.

### Only the planner keeps a rule from being restated in a spec

Ship preserves every requirement and scenario a plan's `## Spec changes` does
not touch, so a restated rule can only be kept out where the delta is written. A
spec stating the behaviour its code or rulebook also carries is intended and is
not that redundancy: a statement of how the catalog is wired keeps its copy in
the spec.

Rejected:

- **Verify or `iwe-revision-evaluator` flags a restated rule.** The check
  belongs where the delta is written, and a Verify finding arrives after
  implementation.

### The Ship review loop belongs to the Ship skill

`/agentdev:iwe-ship` runs the review-and-fix loop, and so does Plan revise mode
answering a Ship blocker report, because `/agentdev:iwe-ship` is explicit-only.
`iwe-ship-reviewer` commits its own `## Ship review`, because it is that
section's only writer.

Rejected:

- **`iwe-shipper` dispatches `iwe-ship-reviewer` as its last step.** Rejected by
  the repository owner.

### OKF's `generated` and `verified` are banned; `sources` stays

`generated.at` changed on every edit, so two branches touching one document
collided in its frontmatter even when their content did not; that merge cost,
with review noise and upkeep, is why `generated` and `verified` are not set.
`okf.yaml` accepts undeclared fields, so dropping a field's declaration does not
keep it out of a document; the ban has to be a check, and one check covers
`status`, `generated`, and `verified`. `sources` stays: it records what a
document derives from and does not change on every edit.

Rejected:

- **A second near-copy test per banned key.** One check covers all three.

### A plan draft is reviewed by two existing agents through one skill

`/agentdev:iwe-plan-review` fans out to the `Durable Knowledge Auditor` and to
`iwe-ship-reviewer` in plan mode, so each rubric lives in exactly one agent and
every Plan mode reaches both through a single step.

Rejected:

- **Widening the `Durable Knowledge Auditor`'s rubric to Ship's obligations.**
  `iwe-ship-reviewer` exists for its ship mode anyway, and one rubric held by
  two agents would drift.

### Each kind of knowledge has one home, and finished work is archived by release

The user set DRY and KISS as the principles of the graph's layout, so each kind
of knowledge has one home: behaviour in spec requirements, the decision in force
and what it rejected in the same spec's `## Rationale`, findings and procedures
in their own types, proposals in features, work in flight in plans, bugs, and
tasks. The `architecture` type is retired, and a feature is a proposal that is
archived with the plan that implements it. Finished work is archived, never
deleted, in one folder per release plus `next-release`, each with one subfolder
per type so every archived document stays under its type's schema; the folder is
the only record of a document's release, so no `released` field repeats it. Ship
writes a plan's lasting decision into the owning spec's `## Rationale` before it
archives the plan, because the operating loop's Consult step reads specs, not
closed plans.

Rejected:

- **Moving specs to OpenSpec.** OpenSpec keeps specs outside the graph and
  outside the plan and Ship flow; the user chose to fix the graph in place.
- **`data/architecture/` kept for decisions only.** No script can check that a
  note states no behaviour, and no workflow step maintains a note.
- **Rationale only in the plan that made the decision.** The Consult step reads
  specs, not closed plans, so rationale needs a home that step reads.
- **Minimal validation for archived documents.** The user chose full validation;
  a schema change is applied to that type's archived documents in the same
  change.
- **An implemented feature whose `## Behaviour` links spec requirements.** It
  keeps a second document per behaviour for a release page that no longer reads
  it.

### Release notes are written from the spec diff

The release cut writes the release page in plain language from the difference in
the specs' requirements and scenarios since the previous cut, because the specs
are the one maintained statement of behaviour, and the page is not edited
afterwards. The plan's `release` field names only the documents the plan closes.
`data/log.md` is removed, which OKF makes optional.

Rejected:

- **Release pages that link features.** A feature's text is written at proposal
  time, so a link to it names a change without saying what changed, and omits
  every change a plan declared `internal`.
