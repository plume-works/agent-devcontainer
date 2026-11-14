---
type: plan
created: 2026-11-07
release:
- features/agentdev-iwe-workflow-skills
- features/autonomous-implement-loop
- features/verify-report-cache
- bugs/relayed-approval-unauthenticated
description: Remove the iwe-implement-all and iwe-ship-all coordinators, every coordinator, child-session, and relayed-approval rule from the agentdev catalog, and rename the Implement orchestrator to the Implement session, so Implement runs only in place and takes decisions only from its own user.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md
stage: done
completed: 2026-11-08
---

# Remove the IWE coordinators and relayed approvals

## Context

The maintainer decided to remove `/agentdev:iwe-implement-all` and
`/agentdev:iwe-ship-all` and every coordinator role rule and flow from the
catalog: any skill or agent that refers to coordinator or relay behavior, or any
IWE rule that coordinates sessions or relays an approval, is in scope.

Two mechanisms carry the coordinator role today:

- **In-process coordinators.** `iwe-implement-all` dispatches `iwe-implementer`
  once per plan and runs `## Running the loop` for each; `iwe-ship-all`
  dispatches `iwe-shipper` once per plan. `iwe-implementer`'s **Dispatched**
  mode exists only for `iwe-implement-all`.
- **Coordinator sessions.** `iwe-implementer`'s **In the user's session** mode
  takes "an approval of the user's that a coordinator's message relays", and
  owes a requesting session a status and the rollup. `pr-merge-stack` step 2
  lets a coordinator session hand the bottom pull request's merge to the child
  session that owns it.

The relay rule is [Implement takes a peer session's claim as the user's
approval](../bugs/relayed-approval-unauthenticated.md): nothing authenticates
the relayer, so a peer's claim can stand in for the user's consent to an
always-escalate deviation. Removing the rule fixes it.

The released behavior is in [IWE workflow skills in the agentdev
catalog](../../1.0.0/features/agentdev-iwe-workflow-skills.md), [Autonomous
Implement loop](../../2.0.0/features/autonomous-implement-loop.md), and [Verify
report cache](../../2.0.0/features/verify-report-cache.md).

## Approach

Delete both coordinator skills. `iwe-implementer` keeps one mode: it is followed
in place by the session that loaded `/agentdev:iwe-implement`, is never
dispatched, and takes every decision from that session's own user. A request
that arrives in another session's message is a plain request, with no duty to
report status or the rollup back to that session and no approval taken from it.
`pr-merge-stack` runs `pr-merge` itself.

In-session dispatch of leaf agents stays: the Implement session still dispatches
`iwe-verifier` and `iwe-revision-evaluator`, `/agentdev:iwe-ship` still
dispatches a fresh-context `iwe-shipper`, and every caller still re-posts a
Verify report verbatim. Only the name changes, so no rule reads as a coordinator
role: "Implement orchestrator" and "the orchestrator" become **the Implement
session**, and `durable-knowledge-auditor`, whose dispatcher can be any session,
says "your dispatcher" as the other leaf agents do.

Rejected:

- **Keep `iwe-implement-all` as the one legitimate relayer.** The maintainer
  removed the coordinators instead.
- **Remove in-session dispatch and relay too.** Verify, revision evaluation, and
  Ship would run in place, reversing [Explicit-only workflow
  agents](../../2.0.0/architecture/explicit-only-workflow-agents.md) and
  [Autonomous Implement
  loop](../../2.0.0/architecture/autonomous-implement-loop.md); the maintainer
  kept them.

## Implementation Steps

### Task 1: Delete the coordinator skills

**Files:** Delete: `.agents/plugins/agentdev/skills/iwe-implement-all/`,
`.agents/plugins/agentdev/skills/iwe-ship-all/`; Modify:
`.agents/plugins/agentdev/README.md`, `README.md`

- [x] Both skill directories are deleted, and the catalog README's
  `/agentdev:iwe-implement-all` and `/agentdev:iwe-ship-all` rows and the root
  README's `iwe-implement-all`/`iwe-ship-all` row are removed.
  - **Evidence:** commit 18547707; `test ! -e` on both skill directories passes
    and `grep -n "implement-all\|ship-all"` on both READMEs prints nothing at
    that commit.

### Task 2: `iwe-implementer` runs in one mode

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [x] `## How you run` describes one mode: the session that loaded
  `/agentdev:iwe-implement` follows the file in place, on the user's command or
  any request naming a plan, including one in another session's message; every
  decision comes from that session's own user, and an approval another session's
  message claims the user gave does not count. The **Dispatched** mode, the
  relay clause, and the requesting-session duties are gone.
  - **Evidence:** commit ee9c4ca7 rewrites `## How you run` as one paragraph;
    `grep -nE "relay|requesting session|^- \*\*Dispatched"` on the rulebook
    prints nothing at that commit.
- [x] Every branch on the dispatched mode is removed: step 1's "dispatched,
  report the candidates and stop", step 7's "Dispatched, both stop", the
  coordinator sentences in `## Running the loop` steps 3 and 4.4 and its
  preamble, the dispatched branch in `## The adversarial review task`, and the
  `## Rules` bullet "Dispatched, never wait for a reply". The description no
  longer names a dispatcher and says the agent is never dispatched.
  - **Evidence:** commit ee9c4ca7; `grep -nE "coordinator|implement-all"` on the
    rulebook prints nothing, the only remaining "dispatch" mentions are the
    never-dispatched statements and the loop's leaf agents, and
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 0 errors.
- [x] "orchestrator" becomes "the Implement session" throughout, including the
  `iwe-planner` mode name it cites (**From the Implement session**).
  - **Evidence:** commit ee9c4ca7; `grep -n orchestrator` on the rulebook prints
    nothing, and `## Running the loop` step 4.2 cites **From the Implement
    session**.

### Task 3: Rename the orchestrator in the other agents and skills

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`.agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md`,
`.agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md`,
`.agents/plugins/agentdev/agents/iwe-shipper.agent.md`,
`.agents/plugins/agentdev/skills/iwe-implement/SKILL.md`

- [x] `iwe-planner`'s description and mode **From the Implement orchestrator**
  become "the Implement session" and **From the Implement session**, naming only
  the session running `/agentdev:iwe-implement`; `iwe-revision-evaluator` says
  "the Implement session"; `durable-knowledge-auditor` says "your dispatcher".
  - **Evidence:** commit 631260ca; `grep -nE "coordinator|orchestrator"` on the
    three agent files prints nothing, and `validate_agent_files` reports 0
    errors.
- [x] `iwe-shipper`'s description names only `iwe-ship` and `iwe-plan` revise as
  dispatchers, and `iwe-implement`'s SKILL.md says the rulebook is never
  dispatched and calls this session the Implement session.
  - **Evidence:** commit 631260ca;
    `grep -nE "coordinator|ship-all|implement-all|orchestrator|In the user's session"`
    on `iwe-shipper.agent.md` and `iwe-implement/SKILL.md` prints nothing.

### Task 4: `pr-merge-stack` runs `pr-merge` itself

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md`

- [x] Step 2 runs `pr-merge` on the bottom pull request with no
  coordinator-session or child-session branch, and step 4 drops "— never by a
  child session —".
  - **Evidence:** commit 4bd10a3d; `grep -nE "coordinator|child session"` on
    `pr-merge-stack/SKILL.md` prints nothing, and `validate_agent_files` reports
    0 errors.

### Task 5: Graph documents stop describing coordinators

**Files:** Modify:
`docs/knowledge/data/archive/2.0.0/architecture/explicit-only-workflow-agents.md`,
`docs/knowledge/data/archive/2.0.0/architecture/autonomous-implement-loop.md`,
`docs/knowledge/data/archive/2.1.0/architecture/adversarial-review.md`,
`docs/knowledge/data/features/autonomous-implement-loop.md`,
`docs/knowledge/data/features/verify-report-cache.md`,
`docs/knowledge/data/backlog/observe-planned-adversarial-review.md`

- [x] The two architecture decisions name no coordinator, relayed approval, or
  dispatched `iwe-implementer`, and call the loop's runner the Implement
  session; the removal of the coordinators and the relay is recorded as a
  decision under `## Decision` with the rejected alternatives under
  `## Rejected alternatives`. `adversarial-review.md` says "the Implement
  session".
  - **Evidence:** commit 8c937584; in both architecture documents
    `grep -nE "coordinator|relay"` matches only the decision "No coordinator
    runs workflows across plans or sessions" and entries under
    `## Rejected alternatives`, `grep -n orchestrator` prints nothing in all
    three, and `iwe schema validate` passes.
- [x] The two feature documents drop the `iwe-implement-all` and `iwe-ship-all`
  behavior and edge cases and their `sources:` entries for the deleted skills.
  - **Evidence:** commit 760cac77;
    `grep -nE "orchestrator|coordinator|implement-all|ship-all"` on both feature
    documents prints nothing.
- [x] `observe-planned-adversarial-review` drops the `iwe-implement-all` run
  from what it observes and says "the Implement session".
  - **Evidence:** commit 760cac77; the task observes one
    `/agentdev:iwe-implement` run on Claude Code and one on OpenCode, and
    `grep -nE "orchestrator|implement-all|coordinator"` on it prints nothing.

## Spec changes

IWE workflow skills — five requirements change; its `sources:` drop the two
deleted skills.

``` markdown
## MODIFIED Requirements

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

### Requirement: The Verify report reaches the conversation verbatim

Every Verify report SHALL number its findings by severity in report order —
`C<n>` for CRITICAL, `W<n>` for WARNING, `S<n>` for SUGGESTION — and every
caller of Verify SHALL show the report verbatim in its final message text:
`/agentdev:iwe-verify` on the session route, on a saved hit and after a save;
`iwe-shipper` ahead of its Ship summary; and the Implement session for the last
Verify round of a run. A path to the saved report, or the report appearing only
in a tool call or tool result, SHALL not count as showing it. A Ship blocker
report SHALL route each Verify CRITICAL by its ID without restating it, and
SHALL state in full, with `path:line` evidence, each blocker Ship found outside
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
  states the mismatch in full with its `path:line` evidence and route

#### Scenario: A plan ships

- **WHEN** `iwe-shipper` ships a plan
- **THEN** its final message carries the Verify report verbatim before the
  completed and preserved operations and the commit

#### Scenario: The Implement loop runs several Verify rounds

- **WHEN** an Implement run verifies, fixes findings, and verifies again
- **THEN** its final report carries the last Verify report verbatim and each
  earlier round's verdict with the first line of each finding it fixed

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
point that needs a user decision it was not given. Nothing authenticates who typed a message in the session's own conversation;
this requirement governs only approvals that another session's message claims.

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
```

## Verification

- `test ! -e .agents/plugins/agentdev/skills/iwe-implement-all && test ! -e .agents/plugins/agentdev/skills/iwe-ship-all`
- `grep -nE "coordinator|implement-all|ship-all|relay|requesting session|orchestrator|[Dd]ispatched mode|^- \*\*Dispatched" .agents/plugins/agentdev/agents/iwe-implementer.agent.md .agents/plugins/agentdev/agents/iwe-planner.agent.md .agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md .agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md .agents/plugins/agentdev/skills/iwe-implement/SKILL.md`
  prints nothing.
- `grep -nE "coordinator|implement-all|ship-all|child session" .agents/plugins/agentdev/agents/iwe-shipper.agent.md .agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md .agents/plugins/agentdev/README.md README.md docs/knowledge/data/archive/2.0.0/architecture/explicit-only-workflow-agents.md docs/knowledge/data/archive/2.0.0/architecture/autonomous-implement-loop.md docs/knowledge/data/archive/2.1.0/architecture/adversarial-review.md docs/knowledge/data/features/autonomous-implement-loop.md docs/knowledge/data/features/verify-report-cache.md docs/knowledge/data/backlog/observe-planned-adversarial-review.md`
  prints only lines inside a `## Approach` rejected-alternative or a decision
  recording the removal.
- `uv run validate_agent_files` on every changed `SKILL.md` and `.agent.md`.
- `bun test ./.agents/plugins/agentdev/tests/opencode`
- `iwe normalize && iwe schema validate`

## Out of scope

- In-session dispatch of leaf agents and verbatim re-posting of their reports,
  including `/agentdev:iwe-ship` dispatching `iwe-shipper`.
- "Orchestrator" in `pr-review` and the self-improve documents, which name other
  concepts.
- The rejected alternative "a coordinator pausing its sessions" in
  `architecture/manual-stacked-prs.md`.
- Shipped plans, `log.md`, and finding documents that mention the coordinators
  as history.
- Cancelling `20261102-model-invocable-ship`, which the maintainer runs through
  `/agentdev:iwe-ship <plan> cancel`.

## Key references

- `.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md` — the
  implement-all coordinator
- `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md` — the ship-all
  coordinator
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md › "description: Execute an active IWE plan task by task —"`
  — description naming the coordinator
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#how-you-run › "follows this file in place —"`
  — `## How you run`, both modes and the relay clause
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#steps › "merges that intent. Both bind the code, and where they"`
  — step 1 dispatched branch
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#steps › "continuous run — with the verification results. With every"`
  — step 7 "Dispatched, both stop"
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#running-the-loop › "meet. File every other WARNING through the"`
  — `## Running the loop`, preamble at 141-145, coordinator at 161 and 179
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#capturing-what-implementation-turns-up › "A durable design fact — a constraint, a boundary, why the"`
  — `## The adversarial review task`, dispatched branch at 201-203
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#rules › "release recording stay with the"`
  — rule "Dispatched, never wait for a reply"
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md › "description: Create or revise an IWE plan — discovery in the"`
  — description naming the Implement orchestrator
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#how-you-run › "From the Implement session"`
  — mode **From the Implement orchestrator**
- `.agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md › "description: Judge one uncommitted IWE plan revision against"`
  — "the Implement orchestrator" in description and twice in the body
- `.agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md#durable-knowledge-auditor › "message goes to your dispatcher, not a human. Never wait for"`
  — "the orchestrator", twice
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md › "description: Ship, cancel, or cut a release for an IWE plan"`
  — description naming the ship-all coordinator
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md#implement-a-plan › "as a subagent: the rulebook is never dispatched."`
  — "only `/agentdev:iwe-implement-all` does that", orchestrator at 17
- `.agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md#the-loop › "pr-merge itself."`
  — coordinator session branch of step 2; "never by a child session" at 50
- `.agents/plugins/agentdev/README.md#knowledge-graph-workflow-iwe › "iteration branch. |"`
  — implement-all row; ship-all at 181
- `README.md#iwe-project-memory › "| Keep durable documents free of session residue. |"`
  — coordinators row
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-implement-verifies-its-own-work-and-acts-on-the-report`
  — Implement loop requirement; 450 revision; 662 Verify verbatim; 751
  adversarial review; 846 start requirement
- `docs/knowledge/data/archive/2.0.0/architecture/explicit-only-workflow-agents.md#decision › "The Ship and Implement workflows are each defined once, as"`
  — `## Decision` callers and relay
- `docs/knowledge/data/archive/2.0.0/architecture/autonomous-implement-loop.md#decision › "Implement session is the session that loaded"`
  — `## Decision` orchestrator and coordinator
- `docs/knowledge/data/features/autonomous-implement-loop.md#behaviour › "is the session that loaded"`
  — orchestrator behaviour; implement-all edge case at 76
- `docs/knowledge/data/features/verify-report-cache.md#behaviour › "— so a Ship blocker report routes a Verify CRITICAL by"`
  — ship-all caller
- `docs/knowledge/data/backlog/observe-planned-adversarial-review.md#observe-a-planned-adversarial-review-task-through-the-implement-loop › "run on Claude Code and one on OpenCode. Done when each"`
  — implement-all run to observe
