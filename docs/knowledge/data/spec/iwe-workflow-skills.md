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
- resource: .agents/plugins/agentdev/agents/iwe-plan-reviewer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-plan-review/references/plan-rules.md
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

### Requirement: Agents reach the graph through the iwe CLI

Every IWE skill and agent in the catalog SHALL read and write the knowledge
graph through `iwe` commands run from the repository root, and SHALL not assume
`mcp__iwe__*` tools exist. The repository SHALL register no IWE MCP server, and
the `dev_tools` role SHALL install `iwe` and `iwes` from the IWE release tarball
and not `iwec`.

#### Scenario: The image installs IWE

- **WHEN** the `dev_tools` role installs the IWE release
- **THEN** `iwe` and `iwes` are installed and `iwec` is not

### Requirement: Workflow improvements preserve the IWE and OKF model

The strengthened skills SHALL continue to use IWE's single-plan-document
workflow, graph links, existing stage conventions, `sources` attribution, and
schema validation. Acceptance scenarios SHALL remain embedded planning content
without introducing OpenSpec change bundles, stores, or separate delta files.
The graph SHALL remain a conformant OKF v0.2 bundle — `data/index.md` lists the
hubs, and the `okf` and `okf-index` schemas check every document except the
archived architecture notes, which the `architecture` schema checks — and SHALL
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

### A saved Verify report is reused by commit and catalog digest

Verify refuses a dirty worktree, so a commit fully names what was judged; the
Implement loop's verdict is reused by the Shipper on the same commit instead of
repeating its test runs. The catalog digest hashes the files on disk, because an
installed plugin is not a Git checkout and a session can load a catalog that
differs from the one the commit holds. The lookup and save live in a script
bundled with the skill, the one place every caller reaches on every harness.

Each plan keeps one saved report, overwritten, because only the latest report is
ever looked up. The user's approvals are recorded in the report but are not part
of its key: an approval changes a verdict only by running a command a saved
report lists as `not run`, so a request that quotes an approval skips the
look-up instead. `verify-cache.py` writes a `.gitignore` holding `*` into
`.tmp/verify/`, so a save never dirties the worktree Verify refuses to run on,
even in a consuming repository that does not ignore `.tmp/`. A saved report is
not reused across a rebase, a squash merge, or a fresh container, and trust in
`.tmp/verify/` rests on the rule that only the skill's script writes it, not on
any protection against a hand-written file.

Rejected:

- **One saved report per commit.** Reading an older report is a different
  feature, incremental re-verify; the reuse check needs only the latest.
- **Look up the saved report in the `iwe-verifier` rulebook.** A hit would still
  cost a dispatch.
- **A handoff file the Implement side commits for the Shipper.** Committing it
  changes the commit it fingerprints, and committing project state contradicts
  report-only Verify.
- **Key the report by a tree hash or by blob hashes of the plan's files.**
  Verify and Ship run on one commit, so the commit is exact; hashes scoped to
  the plan's files miss changes outside that scope that a verification command
  can still depend on.

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

### Revision belongs to Plan

Plan's revise mode owns every change to an active plan, which keeps one owner
per kind of state: Explore investigates, Plan owns planning state, Implement
records tactical deviations, Verify proves, Ship records the result.

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

### The ASD-STE100 audit runs before the other plan reviewers

`/agentdev:iwe-plan-review` dispatches the `STE100 Auditor` alone and first. The
other reviewers read the draft only after it has no ASD-STE100 finding, so they
read the final text.

Rejected:

- **The `STE100 Auditor` as a fourth parallel plan reviewer.** The other
  reviewers would read text that the corrections then change.

### Each kind of knowledge has one home, and finished work is archived by release

The user set DRY and KISS as the principles of the graph's layout, so each kind
of knowledge has one home: findings and procedures in their own types, proposals
in features, work in flight in plans, bugs, and tasks. The `architecture` type
is retired, and a feature is a proposal that is archived with the plan that
implements it. Finished work is archived, never deleted, in one folder per
release plus `next-release`, each with one subfolder per type so every archived
document stays under its type's schema; the folder is the only record of a
document's release, so no `released` field repeats it.

Rejected:

- **Moving specs to OpenSpec.** OpenSpec keeps specs outside the graph and
  outside the plan and Ship flow; the user chose to fix the graph in place.
- **`data/architecture/` kept for decisions only.** No script can check that a
  note states no behaviour, and no workflow step maintains a note.
- **Minimal validation for archived documents.** The user chose full validation;
  a schema change is applied to that type's archived documents in the same
  change.
- **An implemented feature whose `## Behaviour` links spec requirements.** It
  keeps a second document per behaviour for a release page that no longer reads
  it.

### Release pages are written once, by the release cut

The release cut writes the release page in plain language, and the page is not
edited afterwards. The plan's `release` field names only the documents the plan
closes. `data/log.md` is removed, which OKF makes optional.

Rejected:

- **Release pages that link features.** A feature's text is written at proposal
  time, so a link to it names a change without saying what changed, and omits
  every change a plan declared `internal`.
