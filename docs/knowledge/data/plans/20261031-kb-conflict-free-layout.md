---
type: plan
created: 2026-10-31
release:
- features/agentdev-iwe-workflow-skills
- features/consumer-iwe-seed
description: Keep work-item state only in frontmatter, order active work by a global rank field, flatten the hubs into alphabetical membership lists, write the log and release pages only at a release cut, and drop OKF conformance, in this workspace and the bootstrap scaffold.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T14:00:00Z
sources:
- resource: .iwe/config.toml
- resource: .iwe/schemas/hub.yaml
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-capture/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/assets
- resource: docs/knowledge/AGENTS.md
---

# Conflict-free knowledge layout

## Context

Catch-up merges on this repository's pull requests resolve conflicts in the
knowledge graph that are never disagreements about content. Every pull request
that files, ships, or logs work edits the same spots in the same shared files:
the top of today's group in `data/log.md`, the `## Active` and `## Done`
sections of `data/plans.md`, the backlog priority sections, and
`data/releases/unreleased.md`. Each conflict costs a catch-up merge, a full CI
run, agent tokens, and often a fresh AI review.

The decisions, their constraints, and the rejected alternatives are recorded in
[Conflict-free knowledge layout](../architecture/kb-conflict-free-layout.md).
This plan applies them.

The workflow skills and the scaffold they ship to template consumers change
together, so the [IWE workflow
skills](../features/agentdev-iwe-workflow-skills.md) and the [consumer IWE
seed](../features/consumer-iwe-seed.md) both gain the new layout.

## Approach

Each write gets a single owner. A work item's `stage`, `priority`, `completed`,
and new `rank` live only in its own document, so a stage change never edits a
shared file. Hubs keep one inclusion link per member, sorted by key without a
`YYYYMMDD-` prefix, with no `##` sections; a hub changes only when a member is
created, removed, or renamed. Ship writes neither the log nor a release page;
the release cut builds `releases/<X.Y.Z>.md` from the plans completed since the
previous release and adds one log group. OKF goes: no `data/index.md`, no
`okf-index` schema, no `status` field, and the log keeps its date-grouped shape
under a schema of its own. A base schema keeps requiring a non-empty `type`
everywhere, because every query now selects by `type`.

The rejected options — union or custom merge drivers, a merge queue, sorted
stage sections, a roadmap file, dependency-derived order, generated hubs — are
in the architecture document.

Settled defaults the tasks apply:

- `rank` is a positive integer; ranks step by 100 and an insertion takes the
  midpoint of its neighbours.
- An item without `rank` is not yet sequenced. The sequence is
  `iwe find --filter '{rank: {$exists: true}}' --sort rank:1`; unsequenced work
  is the separate `rank: {$exists: false}` query.
- Ship removes `rank` from a shipped or cancelled plan, a fixed bug, and a done
  task.
- Equal ranks are valid; ties break by key, and CI emits a warning naming them.
- Renumbering happens only in a reorder pull request.
- Dependencies stay in plan prose.

No codebase map exists when this plan starts, so every hub follows the same
rules.

## Implementation Steps

### Task 1: Schemas carry rank and drop OKF

**Files:** Modify: `.iwe/config.toml`, `.iwe/schemas/plan.yaml`,
`.iwe/schemas/bug.yaml`, `.iwe/schemas/task.yaml`, `.iwe/schemas/release.yaml`,
every other `.iwe/schemas/*.yaml` that declares `status`; Create:
`.iwe/schemas/base.yaml`, `.iwe/schemas/log.yaml`; Delete:
`.iwe/schemas/okf.yaml`, `.iwe/schemas/okf-index.yaml`,
`.iwe/schemas/okf-log.yaml`; Modify: `docs/knowledge/tests/`

- [x] `plan`, `bug`, and `task` schemas accept an optional integer `rank` of at
  least 1, and a test rejects a non-integer and a zero rank
  - **Evidence:** commit 36fa31c4;
    `uv run pytest docs/knowledge/tests/test_rank_and_base_schemas.py` passed
    (29 tests) — rank cases in `test_invalid_rank_is_rejected` and
    `test_positive_integer_rank_passes`
- [ ] No schema and no document under `data/` declares `status`
- [ ] `base.yaml` requires a non-empty `type` on every document under `data/`
  except `data/log`, and replaces the `okf` binding; a test rejects a document
  without `type`
- [ ] `log.yaml` carries the date-grouped body shape `okf-log.yaml` held, bound
  to `data/log`; the `okf-index` binding and schema are gone

### Task 2: Hubs are flat and sorted

**Files:** Modify: `.iwe/config.toml`, `.iwe/schemas/hub.yaml`; Create: a test
under `docs/knowledge/tests/`

- [ ] The hub schema binds every hub and rejects a `##` section in its body
- [ ] A test fails when a hub's inclusion links are not sorted by member key
  with any `YYYYMMDD-` prefix removed, and names the hub and the first
  out-of-order link

### Task 3: Migrate the graph

**Files:** Modify: `docs/knowledge/data/plans.md`, `bugs.md`, `backlog.md`,
`features.md`, `spec.md`, `architecture.md`, `concept.md`, `someday.md`; Delete:
`docs/knowledge/data/index.md`

- [ ] Every hub is one sorted list of inclusion links with no sections, and
  every member it linked before is still linked
- [ ] `data/index.md` is removed with `iwe delete`, the base schema binds every
  document under `data/` but the log, and `iwe stats` reports no broken link

### Task 4: Propose the initial sequence

**Files:** Modify: the active plans, open bugs, and planned backlog tasks

- [ ] Every active plan, open bug, and planned task named in the current hub
  order carries a `rank`: plans in their `## Active` order, open bugs at the
  positions the active plans' prose places them, and backlog tasks by priority
  and then their order within a priority section, stepping by 100

### Task 5: The maintainer approves the sequence

- [ ] The maintainer confirms the ranked list
  `iwe find --filter '{rank: {$exists: true}}' --sort rank:1` prints, or
  supplies corrections that are applied

### Task 6: Ship and the release cut follow the layout

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`,
`docs/knowledge/data/releases.md`, `.iwe/schemas/release.yaml`; Delete:
`docs/knowledge/data/releases/unreleased.md`

- [ ] Shipping sets `stage` and `completed`, removes `rank` from the plan and
  from each bug it fixes, sets each listed feature implemented, and writes no
  hub, release page, or log entry
- [ ] Cancelling sets `stage: cancelled` and removes `rank` without editing the
  hub
- [ ] Release mode builds `releases/<X.Y.Z>.md` from
  `iwe find --filter '{type: plan, stage: done, completed: {$gt: <previous release date>}}'`
  and each plan's `release` list — a feature absent from every earlier release
  page under Added, one present under Changed, a bug under Fixed — links it from
  `data/releases.md` in sorted position, and adds one dated group to
  `data/log.md`
- [ ] Resuming a partial ship or release cut never writes a second copy of a
  release link or log group
- [ ] The release page this procedure builds for the plans completed since 1.0.0
  lists the same features and bugs, under the same Added, Changed, and Fixed
  headings, as `data/releases/unreleased.md` does
- [ ] `data/releases/unreleased.md` is removed with `iwe delete`, and
  `data/releases.md` links only cut releases
- [ ] `release` accepts only `stage: released`

### Task 7: The other skills read and write frontmatter, not hub sections

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md`,
`.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`.agents/plugins/agentdev/agents/iwe-implementer.agent.md`,
`.agents/plugins/agentdev/agents/iwe-verifier.agent.md`,
`.agents/plugins/agentdev/skills/iwe-weekly/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-setup/SKILL.md`

- [ ] Capture and Plan add a new member's link at its sorted position in the
  hub, never under a section, and Plan sets an optional `rank` when the user
  names the plan's place in the sequence
- [ ] Capture's someday promotion and Setup's onboarding-task completion edit
  frontmatter only, and remove a hub link only when the member leaves the hub
- [ ] Implement, Verify, Weekly, and Plan list active work with the two rank
  queries and select members by `type`, with no `--included-by` on a work hub
  and no reference to a hub section
- [ ] Validation with
  `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes

### Task 8: The workspace manuals describe the layout

**Files:** Modify: `docs/knowledge/AGENTS.md`, `docs/knowledge/SCHEMA.md`,
`docs/knowledge/STRUCTURE.md`, `docs/knowledge/README.md`

- [ ] The operating loop, conventions, and cheatsheet describe frontmatter as
  the only stage record, the rank sequence and its two queries, flat sorted
  hubs, and the release cut as the only writer of release pages and the log; no
  text describes dual representation, hub sections, OKF, `data/index.md`,
  `status`, or an unreleased accumulator
- [ ] `SCHEMA.md` documents `rank`, the base schema, the log schema, and the
  flat hub body

### Task 9: The bootstrap scaffold ships the layout

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/`
(support files, `.iwe/`, and the seed `docs/knowledge/data/` hubs, log,
releases, and onboarding tasks); Modify: `docs/knowledge/tests/test_iwe_seed.py`
only where it asserts the old layout

- [ ] The scaffold's support files and `.iwe/` match the publisher workspace's
- [ ] The seed has flat sorted hubs, no `data/index.md`, no unreleased page, and
  a release example at `stage: released`
- [ ] `uv run pytest docs/knowledge/tests/test_iwe_seed.py` passes

### Task 10: The e2e workflow harness checks the new ship contract

**Files:** Modify: `scripts/e2e/iwe-workflows/clone.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py`,
`scripts/tests/test_e2e_iwe_workflows_clone.py`

- [ ] The clone helper reports whether ship changed any hub, release page, or
  log, and the workflow tests assert that a ship changed none of them
- [ ] `uv run pytest scripts/tests/test_e2e_iwe_workflows_clone.py` passes

### Task 11: CI warns about equal ranks

**Files:** Modify: `.github/workflows/validate-knowledge-base.yml`

- [ ] A step prints a GitHub `::warning::` naming every pair of documents that
  share a `rank`, and never fails the job

### Task 12: The e2e workflow suite passes

- [ ] The Claude and OpenCode e2e workflow suites pass against this branch

### Task 13: CI passes on the pull request

- [ ] The knowledge-base, agent-files, and CI/CD checks pass on the pull request
  for this branch

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — contract-heavy:
shipping, capture, and the release cut change what they write, and the
release-impact and OKF requirements change their scenarios.

``` markdown
## ADDED Requirements

### Requirement: Active work carries one global rank sequence

Active plans, open bugs, and planned backlog tasks SHALL record their place in
the build order as an optional integer `rank` in their own frontmatter, lower
first, shared across the three types. The sequence SHALL be the result of
`iwe find --filter '{rank: {$exists: true}}' --sort rank:1`. Ship SHALL remove
`rank` from every document it marks done or cancelled. Equal ranks SHALL be
valid, and CI SHALL warn about them without failing.

#### Scenario: A plan is filed with a place in the sequence

- **WHEN** the user names where a new plan belongs in the build order
- **THEN** Plan sets its `rank` between its neighbours' ranks and edits no
  other document's `rank`

#### Scenario: Work ships

- **WHEN** Ship marks a plan done and the bugs its `release` lists fixed
- **THEN** none of them carries a `rank`, and the sequence query no longer
  lists them

#### Scenario: Two documents share a rank

- **WHEN** two documents carry the same `rank`
- **THEN** the knowledge-base CI check passes and emits a warning naming both

### Requirement: Hubs are flat alphabetical membership lists

Every hub SHALL be one list of inclusion links with no `##` sections, sorted by member key with any `YYYYMMDD-` prefix removed. A
skill SHALL edit a hub only when a member is created, removed, or renamed,
never to record a stage or priority change.

#### Scenario: A document is filed

- **WHEN** Capture or Plan files a new document
- **THEN** its link is inserted at its sorted position in its hub

#### Scenario: A hub is out of order or sectioned

- **WHEN** a hub's links are out of order or its body has a `##` section
- **THEN** the knowledge-base checks fail and name the hub

#### Scenario: A work item changes stage

- **WHEN** a plan, bug, task, or feature changes `stage`
- **THEN** its hub file is unchanged

### Requirement: A release cut is the only writer of release pages and the log

The release cut SHALL build `releases/<X.Y.Z>.md` from the plans whose
`completed` date falls after the previous release's date, taking entries only
from each plan's `release` list, SHALL link the page from `data/releases.md`,
and SHALL add one dated group to `data/log.md`. No other operation SHALL write
a release page or the log.

#### Scenario: A release is cut

- **WHEN** the release cut runs for `<X.Y.Z>`
- **THEN** the page lists each feature absent from every earlier release under
  Added, each feature present in an earlier release under Changed, and each
  bug under Fixed, with one link per document

#### Scenario: A release cut resumes

- **WHEN** a prior release cut already wrote some of its results
- **THEN** the cut preserves them and writes no second release link or log
  group

### Requirement: Workflow improvements preserve the IWE model

The strengthened skills SHALL continue to use IWE's single-plan-document
workflow, graph links, durable specs, existing stage conventions, provenance
requirements, and schema validation. Risk-scaled spec deltas SHALL remain
embedded planning content without introducing OpenSpec change bundles, stores,
separate delta files, archive moves, or a claimed programmatic delta application
engine.

#### Scenario: Updated skills write project memory

- **WHEN** an updated skill creates or meaningfully changes an IWE document
- **THEN** it follows the existing metadata, graph membership, normalization,
  validation, and commit requirements defined by the workspace

## MODIFIED Requirements

### Requirement: Plans declare their release impact

The plan schema SHALL require every active plan to carry a `release` frontmatter
value: `internal`, or a non-empty list of the `features/` and `bugs/` keys the
work adds, changes, or fixes. The Plan skill SHALL set that value when it files
a plan, SHALL declare `internal` only when no workspace user or template
consumer sees a difference, and SHALL have Capture file a missing feature before
it files the plan. The release cut SHALL take a plan's release entries only
from that value, and Ship SHALL never create a feature.

#### Scenario: A plan introduces user-visible behavior with no feature

- **WHEN** Plan files a plan whose work changes what a workspace user or
  template consumer sees, and no feature describes it
- **THEN** Plan hands the feature to Capture, lists its key in `release`, and
  sets the feature to `stage: accepted`

#### Scenario: A plan changes nothing users see

- **WHEN** Ship ships a plan that declares `release: internal`
- **THEN** Ship marks the plan done, and the next release cut adds no entry for
  it

#### Scenario: A plan declares features and bugs

- **WHEN** Ship ships a plan whose `release` lists feature and bug keys
- **THEN** Ship marks each feature implemented and each bug done and writes no
  release page, and the next release cut adds one link per listed document —
  a feature new in that version under Added, a feature released in an earlier
  version under Changed, a bug under Fixed

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
- **THEN** Ship inspects current state, preserves completed valid work, and
  continues from the first incomplete operation

#### Scenario: A durable spec is retired

- **WHEN** the verified implementation and plan explicitly remove the final
  behavior represented by a durable spec
- **THEN** Ship uses IWE's graph-aware deletion operation, repairs references,
  and does not leave an empty or orphaned spec document

### Requirement: Capture files complete inbox documents

The Capture skill SHALL be the only writer of new bug, proposed-feature, and
backlog-task documents, SHALL refuse a document missing any frontmatter field or
body section `SCHEMA.md` requires for its type, SHALL check the graph for a
likely duplicate before filing, SHALL file a feature at `stage: proposed` and
never promote it, and SHALL link every filed document at its sorted position in
its hub and end with `iwe normalize` and `iwe schema validate` passing.

#### Scenario: A complete item is captured

- **WHEN** Capture is invoked for a bug, feature, or task whose required
  sections and fields are all supplied, and no likely duplicate exists
- **THEN** Capture writes the document at its lane's key with the `stage`
  `SCHEMA.md` assigns it, stamps `generated` and `sources`, links it at its
  sorted position in its hub, and validates the graph

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

## REMOVED Requirements

### Requirement: Workflow improvements preserve the IWE and OKF model

Replaced by "Workflow improvements preserve the IWE model": the graph no
longer follows OKF, so the requirement drops OKF metadata and the `status`
convention.
```

## Depends on

- [Remove the codebase map](20261031-remove-codebase-map.md) ships first: it
  deletes the `data/codebase` hub and the Map skill, so no hub is exempt from
  the flat-list rules and no skill writes map entries to the log.
- [Remove Codex support](20261031-remove-codex.md) ships first: it removes the
  Codex marketplace from agent-file validation and the Codex e2e harness, and
  edits the same catalog agents and skills this plan rewrites.

## Verification

- `iwe normalize` leaves the tree unchanged and `iwe schema validate` exits 0.
- `iwe stats` reports no broken link.
- `uv run pytest docs/knowledge/tests` passes, including the hub-order test and
  the seed tests.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- `uv run pytest scripts/tests/test_e2e_iwe_workflows_clone.py` passes.
- `iwe find --filter '{rank: {$exists: true}}' --sort rank:1 -f keys` prints the
  approved sequence.
- `grep -rnE '## Active|## Done|unreleased|okf|OKF|data/index' docs/knowledge/AGENTS.md docs/knowledge/SCHEMA.md .agents/plugins/agentdev/agents .agents/plugins/agentdev/skills/iwe-*/SKILL.md`
  finds no description of the old layout.
- A rehearsal merge of two branches that each file a plan and ship another
  merges without conflict in any hub.

## Out of scope

- The `generated` and `verified` provenance fields.
- Conflicts in Renovate-managed pin and workflow files.
- Recording dependencies between work items in frontmatter.
- Rewriting the history in `data/log.md` or the 1.0.0 release page.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `.iwe/config.toml:93` — hub schema binding over every directory hub
- `.iwe/config.toml:113` — OKF bindings `okf`, `okf-index`, `okf-log`
- `.iwe/schemas/hub.yaml:1` — hub schema, frontmatter only
- `.iwe/schemas/plan.yaml:12` — plan `stage`
- `.iwe/schemas/task.yaml:14` — task `priority`
- `.iwe/schemas/release.yaml:15` — release `stage` enum with `unreleased`
- `.iwe/schemas/okf-log.yaml:1` — date-grouped log body schema
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:54` — Ship reads the hub
  section, unreleased page, and today's log group
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:65` — cancellation moves
  the hub link to `## Cancelled`
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:123` — graph
  transitions: hub move, unreleased link, log bullet
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:150` — release cut
  renames the unreleased page
- `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md:69` — hub link under a
  priority section
- `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md:96` — someday promotion
  moves the hub link
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md:39` — active plans by
  `--included-by data/plans`
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md:128` — plan filed under
  `## Active`
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:32` — plan choice
  from `## Active`
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md:46` — plan choice from
  `## Active`
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md:118` — audit checks
  done plans under `## Active`
- `.agents/plugins/agentdev/skills/iwe-weekly/SKILL.md:15` — shipped plans by
  `--included-by data/plans`
- `.agents/plugins/agentdev/skills/iwe-weekly/SKILL.md:18` — in-flight plans
  from `## Active`
- `.agents/plugins/agentdev/skills/iwe-weekly/SKILL.md:22` — backlog head from
  `## High`
- `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md:50` — onboarding tasks
  moved to `## Done`
- `docs/knowledge/AGENTS.md:35` — the Record step's hub and log transitions
- `docs/knowledge/AGENTS.md:83` — inclusion-link, `data/index.md`, dual
  representation, and OKF conventions
- `docs/knowledge/AGENTS.md:202` — cheatsheet `--included-by` queries
- `docs/knowledge/SCHEMA.md:42` — `stage` versus OKF `status`
- `docs/knowledge/SCHEMA.md:60` — reserved files `data/index.md` and
  `data/log.md`
- `docs/knowledge/SCHEMA.md:188` — hubs and their sections
- `docs/knowledge/STRUCTURE.md:37` — hub membership is a link
- `docs/knowledge/tests/test_iwe_seed.py:110` — scaffold support files must
  match the publisher workspace
- `docs/knowledge/tests/test_iwe_seed.py:178` — onboarding tasks are present and
  open
- `scripts/e2e/iwe-workflows/clone.py:34` — `UNRELEASED` accumulator path
- `scripts/e2e/iwe-workflows/clone.py:325` — `unreleased_diff`
- `.github/workflows/validate-knowledge-base.yml:93` — schema validation and
  normalization steps
- `docs/knowledge/data/spec/iwe-workflow-skills.md:185` — Requirement: Plans
  declare their release impact
- `docs/knowledge/data/spec/iwe-workflow-skills.md:537` — Requirement: Ship
  synchronizes durable specs by intelligent merge
- `docs/knowledge/data/spec/iwe-workflow-skills.md:834` — Requirement: Capture
  files complete inbox documents
- `docs/knowledge/data/spec/iwe-workflow-skills.md:893` — Requirement: Workflow
  improvements preserve the IWE and OKF model
