---
type: plan
created: 2026-11-08
release:
- features/agentdev-iwe-workflow-skills
description: Make plans ephemeral implementation documents that the release cut deletes once they are on the default branch, and track planned work only as ready stories (backlog tasks with acceptance criteria) and bugs, with decisions in architecture docs and the iteration goal in milestone.md.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md
- resource: scripts/check-ship-records.py
- resource: .agents/plugins/agentdev/skills/iwe-capture/SKILL.md
- resource: .iwe/schemas/task.yaml
- resource: .iwe/schemas/plan.yaml
- resource: .iwe/schemas/bug.yaml
- resource: docs/knowledge/SCHEMA.md
---

# Plans as ephemeral implementation documents; stories as the planned work

## Context

The maintainer wants project memory kept at the level XP/Agile tracks: product
goals, decisions, architecture for the current iteration, and acceptance
criteria for stories. Planned work lives only in stories (backlog tasks) and
bugs; a plan is an ephemeral implementation document. A story must be complete
enough that `/agentdev:iwe-plan` has no open question about *what* to build.

Today the graph does the opposite. Plans are the permanent record — 106 done and
1 cancelled plan stay in `data/plans/` and other documents link into them — and
the release cut reads their `release:` lists. Backlog tasks have no shape beyond
an H1 and a body: the 16 pending tasks use about a dozen layouts and none
carries acceptance criteria, so the planner's step 2 has to ask about scope,
behaviour, and boundaries a story should already settle.

Every decision below is the maintainer's.

The work changes [agentdev IWE workflow
skills](../features/agentdev-iwe-workflow-skills.md) for every workspace user
and template consumer.

## Approach

**Model.**

```
product.md ## Goals ──► milestone.md (current iteration goal)
                               │ committed work = ranked stories + bugs
features/<capability> ◄── advances ── backlog/<story>  (filed means ready)
architecture/ ◄── ## Decisions ──────┘   │
                                         ▼ /agentdev:iwe-plan
                              plans/<date>-<slug>   delivers: backlog/<story> | bugs/<bug>
                                         │ acceptance scenarios → ## Spec changes
                                         ▼ Ship
           spec/ merged · story/bug done · advanced features implemented · plan kept
                                         ▼ release cut
           done stories (advances) + done bugs without `released` → releases/X.Y.Z
           shipped plans already on the default branch → deleted
```

- **Feature vs story.** A feature stays the durable, capability-level document.
  A story is one increment: a `data/backlog/` task whose frontmatter `advances:`
  is `internal` or a list of `features/<slug>` keys.
- **The story card**, enforced by `task.yaml` the way `bug.yaml` enforces a
  bug's shape, and by Capture: `## Story`, `## Acceptance criteria` (spec
  format: `#### Scenario:` with WHEN/THEN), `## Decisions`, `## Out of scope`,
  then the optional `## Depends on` and `## Plan`. A story with no behaviour
  change states an observable check as its scenario. Filed means ready: unformed
  work stays in `data/someday/`; a spike is a story whose acceptance criterion
  is a decision recorded in `data/architecture/`.
- **Lifecycle.** Stories and bugs go `pending → in-progress → done` (`cancelled`
  stays). Plan creates a plan only from one ready story or bug, records it in
  the plan's `delivers:`, sets the item `in-progress`, and adds an inclusion
  link to the plan under the item's `## Plan`. Ship marks the item done and each
  advanced feature `implemented`, and leaves the plan in place. The release cut
  `iwe delete`s each shipped plan — which removes the plan's inclusion links,
  including the one under `## Plan` — and removes the emptied `## Plan` heading.
  Cancelling deletes the plan the same way at once and returns the item to
  `pending`.
- **A shipped plan reaches main before it is deleted.** The default branch is
  squash-merged, so a plan created or finished and deleted on one branch never
  reaches main's history. Ship may run on the implementation branch and deletes
  nothing; the release cut deletes a plan only when its delivered item is done
  and its file is byte-identical at the remote default branch, and leaves any
  other plan for a later cut.
- **The Ship review lives on the delivered item.** `iwe-ship-reviewer` appends
  `## Ship review` to the story or bug the plan `delivers`, which survives the
  plan, and the `ship-records` pre-commit hook gates it there.
- **Release cut** reads done stories and done bugs without `released`: each
  story's `advances` features (internal contributes nothing) under Added or
  Changed, each bug under Fixed, and stamps `released` on them.
- **Build order.** `rank` lives on stories and bugs only; plans carry none.
- **Iteration.** `milestone.md` becomes the iteration tracker: a goal and the
  product goal it serves, no membership list. `product.md` gains `## Goals`.
- **Specs stay.** The plan lifts the story's acceptance scenarios into its
  `## Spec changes`; Ship merges them as today.

**Switch.** Every active plan ships under the old rules first, then one last
old-rules release cut stamps every done plan. Only then does this plan's
implementation migrate the graph: done and cancelled plans are deleted with
every inbound link repointed to a GitHub permalink at the last commit that holds
them; every backlog task moves to `data/someday/`; bugs at `planned` become
`in-progress`; done bugs get the last cut's version as `released`.

**Assumptions** (minor details no decision covered):

- Cancelled backlog tasks move to `data/someday/` with the pending and done
  ones, so `data/backlog/` holds only cards.
- A bug's `## Fix` no longer links the plan — a release cut deletes the plan;
  the fix description stands alone.
- The plan names its item in frontmatter `delivers:` (schema-checked), mirroring
  how `release:` worked, so Ship and Verify read it without parsing prose.
- `/agentdev:iwe-branch-name` is unchanged: a shipped plan has no `stage`, so it
  reads as `complete` until a release cut deletes it and as `missing` after;
  Ship rerun on it finds the item done and reports it already shipped.
- Cancelling deletes the plan at once: cancelled work ships nothing, and
  whatever version of the plan reached main stays in its history.

**Rejected.** Features as stories (a feature spans many plans — up to 18 — and
release pages link it); a separate `ready` stage (someday/ already is the
not-ready lane); plan only on the work branch or in `.tmp/` (breaks the plan
pull request, resumability, and Verify's checkbox evidence); dropping or folding
`spec/` (26 of 30 specs have no feature, and per-story criteria go stale once a
later story changes the behaviour); Ship deleting the plan once its final
version is on the default branch (forces a separate ship pull request for every
plan).

## Implementation Steps

### Task 1: Check the switch preconditions

**Files:** none

- [ ] `iwe find --filter '{type: plan, stage: {$exists: false}}' -f keys` lists
  only `data/plans/20261108-ephemeral-plans-and-stories`, and
  `iwe find --filter '{type: plan, stage: done, released: {$exists: false}}' -f keys`
  lists nothing. If either fails, stop and report: the remaining plans ship, or
  the maintainer runs `/agentdev:iwe-ship release <X.Y.Z>`, before this plan
  continues.

### Task 2: Delete done and cancelled plans, repointing every inbound link

**Files:** Delete: `docs/knowledge/data/plans/*.md` at `stage: done` or
`stage: cancelled`; Modify: every document under `docs/knowledge/data/` that
links one (features, bugs, architecture, someday, spec `sources:`, `log.md`)

- [ ] Take `SHA=$(git rev-parse origin/main)` (the last commit holding every
  plan). Before deleting, rewrite every link and every `sources:` `resource`
  that targets a done or cancelled plan to
  `https://github.com/plume-works/agent-devcontainer/blob/<SHA>/docs/knowledge/data/plans/<file>`,
  keeping the link text. Then `iwe delete` each such plan, so `data/plans.md`
  keeps only active plans.
  `grep -rnE '(\.\./|data/)plans/20' docs/knowledge/data` matches only this plan
  and its own hub link; `iwe schema validate` passes.

### Task 3: Move every backlog task to someday

**Files:** Move: `docs/knowledge/data/backlog/*.md` →
`docs/knowledge/data/someday/`; Modify: `docs/knowledge/data/backlog.md`,
`docs/knowledge/data/someday.md`

- [ ] For each task: `iwe rename data/backlog/<slug> data/someday/<slug>`,
  rewrite its frontmatter to `type: someday` (dropping `stage`, `priority`,
  `rank`, `created`, `completed`; keeping `description` and `sources`), and move
  its hub link to its sorted position in `data/someday.md`. `data/backlog/` is
  empty; `iwe schema validate` and
  `uv run pytest docs/knowledge/tests/test_hub_order.py` pass.

### Task 4: Switch the schemas and convert the open items

**Files:** Modify: `.iwe/schemas/task.yaml`, `.iwe/schemas/bug.yaml`,
`.iwe/schemas/plan.yaml` and their identical copies under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/.iwe/schemas/`; every bug
at `stage: planned` or `stage: done`; this plan; Create:
`docs/knowledge/data/backlog/ephemeral-plans-and-stories.md`; Modify:
`docs/knowledge/data/backlog.md`

- [ ] `task.yaml`: `stage` enum `pending | in-progress | done | cancelled`;
  `advances` required — `internal` or a non-empty list of `features/<slug>`
  keys; `released` (X.Y.Z); `completed` required when `stage: done`; body: one
  H1 holding `## Story`, `## Acceptance criteria`, `## Decisions`,
  `## Out of scope` (required, in order), then optional `## Depends on` and
  `## Plan`, additional sections allowed after them. `bug.yaml`: `planned` →
  `in-progress`; `released` (X.Y.Z). `plan.yaml`: remove the `stage`,
  `completed`, `released`, `release`, and `rank` definitions and reject those
  keys — the frontmatter is not closed, so dropping a definition alone still
  accepts the key — with a frontmatter
  `not: { anyOf: [{ required: [stage] }, { required: [completed] }, { required: [released] }, { required: [release] }, { required: [rank] }] }`;
  require `delivers` matching `^(backlog|bugs)/<slug>$`.
- [ ] Convert the graph in the same commit: each bug at `planned` →
  `in-progress`; each done bug gets `released: <latest release version>`; this
  plan's story is written at `data/backlog/ephemeral-plans-and-stories.md`
  (`advances: [features/agentdev-iwe-workflow-skills]`, `stage: in-progress`,
  its acceptance criteria taken from this plan's `## Spec changes`, its
  `## Plan` inclusion-linking this plan) and linked from `data/backlog.md`; this
  plan's frontmatter drops `release` and gains
  `delivers: backlog/ephemeral-plans-and-stories`. Both schema copies are
  byte-identical; `iwe normalize` and `iwe schema validate` pass.

The card skeleton the schema enforces:

``` markdown
---
type: task
stage: pending
priority: medium
created: <YYYY-MM-DD>
advances: internal # or a list of features/<slug> keys
description: <one sentence>
---

# <Story title>

## Story
As a <user from product.md ## Users>,
I want <capability>,
so that <outcome>.

## Acceptance criteria

#### Scenario: <name>

- **WHEN** ...
- **THEN** ...

## Decisions
- [<architecture doc>](../architecture/x.md)
- <small inline decision, e.g. compatibility>

## Out of scope
- ...

## Depends on        (optional)
- [<story>](...)
```

### Task 5: Cover the new schema rules with tests

**Files:** Modify: `docs/knowledge/tests/test_body_shape_schemas.py`,
`docs/knowledge/tests/test_released_stamp.py`,
`docs/knowledge/tests/test_rank_and_base_schemas.py`,
`docs/knowledge/tests/test_plan_checkboxes.py`; Delete:
`docs/knowledge/tests/test_plan_release_schema.py`; Create:
`docs/knowledge/tests/test_story_and_plan_links.py`

- [ ] Body shape: the task lane joins bug and feature — a story missing,
  reordering, or emptying a required card section fails validation, named by
  key. Story and plan links: a story without `advances`, or with a key outside
  `features/`, fails; a plan without `delivers`, or with `release`, `rank`, or
  `stage`, fails. Released stamp: every `released` on a story or bug names a
  release page, and the scaffold and workspace graphs both pass. Rank: lanes are
  `bugs` and `backlog`. Checkboxes: the `stage: done` branch and its two tests
  go, since no plan carries a stage. `uv run pytest docs/knowledge/tests`
  passes.

### Task 6: Rewrite Capture for the story card

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md`

- [ ] Step 3's **task** gate requires the card: the four required sections in
  order, scenarios in the spec format, `advances` naming only existing features
  — a missing feature is captured first as a proposed feature — plus `priority`
  and `description`; anything missing is listed at once and nothing is written.
  `## Promoting a someday idea` applies the same gate to the idea plus the
  caller's additions. Step 4 files a story at `stage: pending`.

### Task 7: Rewrite Plan for one story or bug

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [ ] Create mode takes one ready story or bug key; work with neither is handed
  to `/agentdev:iwe-capture task` first. The story's card is the plan's
  `## Context`, its acceptance scenarios feed `## Spec changes`, and its
  `## Out of scope` and `## Depends on` carry over. Step 2 asks only about
  choices discovery surfaces; a material gap in the card is fixed in the story,
  with the user, before the plan is written. Step 4's frontmatter is `created`
  and `delivers`; the `release` rules go. Step 5 sets the item `in-progress`,
  adds the plan's inclusion link under the item's `## Plan`, sets each
  `proposed` feature the story advances to `accepted`, and sets no `rank` on the
  plan. Revise mode never changes `delivers`.

### Task 8: Rewrite Ship to keep the plan and cut from stories and bugs

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`,
`.agents/plugins/agentdev/skills/iwe-ship/SKILL.md`

- [ ] Step 1 reads the item `delivers` names, and every feature a story
  advances; a missing or unresolvable `delivers` is a blocker report. Step 2
  (cancel) `iwe delete`s the plan, removes the emptied `## Plan` heading, and
  returns the item to `pending`. Step 6 sets the item `done` with `completed`
  and no `rank`, each advanced feature `implemented`, and a bug's `## Fix`
  without a plan link, and leaves the plan and the item's `## Plan` in place;
  the milestone-aggregator sentence in step 7 goes. Step 8 selects done stories
  and bugs without `released` (plus those this cut already stamped), takes each
  story's `advances` and each bug, and stamps `released` on them. A rerun after
  a completed ship finds the item done and reports it already shipped.
- [ ] Step 8 then fetches the remote default branch and `iwe delete`s every plan
  whose delivered item is `stage: done` and whose file
  `git diff --quiet <remote>/<default> -- <plan file>` finds identical there,
  removing each emptied `## Plan` heading. A plan absent from the remote default
  branch, or different there, stays for a later cut, and the report names it.

### Task 9: Record the Ship review on the delivered item

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md`,
`scripts/check-ship-records.py`, `scripts/tests/test_check_ship_records.py`,
`.pre-commit-config.yaml`

- [ ] `iwe-ship-reviewer` ship mode finds the ship commit as the commit that set
  the delivered item's `stage: done`
  (`git log -1 --format=%H -G '^stage: done' -- <item file>`), reads the plan
  and the item, checks the checklist below, and appends it as the item's last
  section, committing only the item. Plan mode checks `delivers` in place of
  `release`. The checklist, verbatim:

  ``` markdown
  ## Ship review

  Reviewed by `iwe-ship-reviewer` on <YYYY-MM-DD>.

  - [x] Verify reported zero CRITICAL — confirmed: <Verify's verdict line>
  - [x] Every `## Spec changes` operation is in its spec — confirmed: <spec keys> | N/A: `## Spec changes` is None
  - [x] Every spec the plan created is linked from `data/spec.md` — confirmed: <keys> | N/A: no spec created
  - [x] Every spec the plan retired was removed with `iwe delete` — confirmed: <keys> | N/A: no spec retired
  - [x] The item is `stage: done` with `completed` and no `rank` — confirmed: <completed date>
  - [x] Every feature in `advances` is `stage: implemented` — confirmed: <keys> | N/A: the item is a bug or advances `internal`
  - [x] The bug has a `## Fix` — confirmed | N/A: the item is a story
  - [x] Ship edited no hub, release page, or `data/log.md` — confirmed
  ```

  The Verify, item-stage, and hub items never take `N/A`.

- [ ] `scripts/check-ship-records.py::SHIP_REVIEW_ITEMS` holds the checklist
  above; `scripts/check-ship-records.py::check` gates a `## Ship review` on a
  story or a bug and no longer reads plans; the `ship-records` hook's `files`
  pattern is `^docs/knowledge/data/(bugs|backlog)/.*\.md$`.
  `uv run pytest scripts/tests/test_check_ship_records.py` passes, covering a
  well-formed review on a story and on a bug, a missing item, an `N/A` on each
  item that never takes one, and a plan document that is no longer checked.

### Task 10: Align Implement, Verify, Explore, Weekly, and Setup

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`,
`.agents/plugins/agentdev/agents/iwe-verifier.agent.md`,
`.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-weekly/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-setup/SKILL.md`

- [ ] Implement step 3: every prerequisite in `## Depends on` is a story or bug
  at `stage: done`. Verify step 2 lists plans with `{type: plan}` and the build
  order from story and bug `rank`, and reads the plan's `delivers` item with its
  acceptance criteria. Explore's `## Capturing`: ready to build → the story goes
  to `/agentdev:iwe-capture task`, then `/agentdev:iwe-plan` on its key; unready
  work → `data/someday/`. Weekly's shipped list is stories and bugs completed in
  the last 7 days. Setup's closing step still closes `fill-product-doc` and
  `capture-current-architecture`.
  `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.

### Task 11: Rewrite the knowledge-base documents and trackers

**Files:** Modify (each with its identical scaffold copy under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/`):
`SCHEMA.md`, `STRUCTURE.md`, `AGENTS.md`, `README.md`, `CHANGELOG.md`; Modify:
`docs/knowledge/data/plans.md`, `backlog.md`, `someday.md`, `milestone.md`,
`product.md` (the hub and tracker intros), and their scaffold counterparts

- [ ] SCHEMA.md: the plan, bug, and backlog sections and `## The build order`
  describe `delivers`, the card, `advances`, `in-progress`, `released` on
  stories and bugs, and rank on stories and bugs only. STRUCTURE.md: the funnel
  is someday → story → plan (deleted at the release cut) → release; "Milestones
  are plans of plans" becomes the iteration tracker; done plans are no longer
  history in the graph. AGENTS.md and README.md: the lifecycle list, the
  build-order queries, and the example queries match, and the rule that every
  hub member stays listed forever — in AGENTS.md and STRUCTURE.md — excepts
  plans, which leave `data/plans.md` when a release cut deletes them.
  CHANGELOG.md: one `[Unreleased]` entry with migration notes for an earlier
  clone. `milestone.md` holds a ✏️ iteration goal placeholder and the product
  goal it serves; `product.md` gains a ✏️ `## Goals` section. Every scaffold
  copy is byte-identical to its workspace file.

### Task 12: Rewrite the scaffold's seed documents

**Files:** Modify/Delete under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/`:
`plans/mvp.example.md` (delete), `plans/20260701-focus-sessions.example.md`
(delete), `plans/20260720-streak-widget.example.md`, the four `backlog/*.md`
onboarding tasks; Create: `backlog/focus-sessions.example.md`,
`backlog/streak-widget.example.md`; Modify:
`.agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md`

- [ ] The focus-sessions story is done with `released: 0.1.0`; the streak-widget
  story is `in-progress` and its `## Plan` links the streak-widget plan, which
  carries `delivers` and no rank. The onboarding tasks are cards with
  `advances: internal`, keeping the keys `iwe-setup` closes. `scaffold.md`
  describes the new seed set. A copy of the scaffold in `/tmp` passes
  `iwe normalize` with no diff and `iwe schema validate`.

### Task 13: Record the model as an architecture decision

**Files:** Create: `docs/knowledge/data/architecture/ephemeral-plans.md`;
Modify: `docs/knowledge/data/architecture.md`

- [ ] The decision, its rejected alternatives (from `## Approach`, stated
  without the graph counts, which go stale), the invariant that planned work
  lives only in stories and bugs, and the rule that only a release cut deletes a
  shipped plan, once the plan is on the default branch, linked from the hub at
  its sorted position.

### Task 14: Write the product goals and the first iteration goal

**Files:** Modify: `docs/knowledge/data/product.md`,
`docs/knowledge/data/milestone.md`

- [ ] The ✏️ placeholders are replaced with real goals. **Closed by:** the
  maintainer writing `## Goals` and the first iteration goal.

### Task 15: Observe a story through Capture and Plan

**Files:** none

- [ ] After merge, `/agentdev:iwe-capture task` refuses a card missing a section
  and files a complete one; `/agentdev:iwe-plan` on it sets the story
  `in-progress`, links the plan under `## Plan`, and asks no question the card
  settles. **Closed by:** the maintainer's first capture-and-plan run of a story
  after merge.

### Task 16: Observe a plan kept at Ship and deleted at the release cut

**Files:** none

- [ ] After merge, a ship leaves its plan in place and `iwe-ship-reviewer`
  appends `## Ship review` to the delivered item; the next release cut deletes
  that plan once it is on the default branch, and keeps one shipped on the cut's
  own branch. **Closed by:** the maintainer's first ship and release cut after
  merge.

## Spec changes

[iwe-workflow-skills](../spec/iwe-workflow-skills.md) — contract-heavy (schema,
lifecycle, release cut):

``` markdown
## REMOVED Requirements

### Requirement: Plans declare their release impact

Retired: a plan no longer carries `release`. A story declares the features it
advances, a plan names the one story or bug it delivers, and the release cut
reads done stories and bugs.

## ADDED Requirements

### Requirement: Stories keep the card shape

The task schema SHALL require a story's `advances` frontmatter — `internal` or a
non-empty list of `features/` keys — and the body sections `## Story`,
`## Acceptance criteria`, `## Decisions`, and `## Out of scope` in that order,
followed by optional `## Depends on` and `## Plan` sections, while allowing
additional sections after them. The task and bug schemas SHALL accept a `stage`
of `pending`, `in-progress`, `done`, or `cancelled`.

#### Scenario: A story is written without Capture

- **WHEN** a story lacks a required card section, has them out of order, or
  lacks `advances`
- **THEN** `iwe schema validate` fails and names the document

#### Scenario: A story advances a non-feature

- **WHEN** a story's `advances` lists a key outside `features/`
- **THEN** `iwe schema validate` fails and names the document

### Requirement: A plan delivers one story or bug

The plan schema SHALL require `delivers`, naming one `backlog/` story or
`bugs/` bug, and SHALL reject `stage`, `release`, `released`, and `rank` on a
plan. The Plan skill SHALL create a plan only from one existing story or bug,
SHALL set that item to `stage: in-progress`, SHALL add an inclusion link to the
plan under the item's `## Plan` section, and SHALL set each `proposed` feature
the story advances to `stage: accepted`. Ship SHALL set the item to
`stage: done` with `completed` and remove its `rank`, SHALL set each feature the
story advances to `stage: implemented`, SHALL write a bug's `## Fix`, and SHALL
leave the plan and the item's `## Plan` section in place. Ship SHALL never
create a feature. Cancelling SHALL delete the plan with `iwe delete`, remove the
emptied `## Plan` section, and return the item to `stage: pending` without a
`## Fix`.

#### Scenario: A story is planned

- **WHEN** Plan creates a plan for a pending story
- **THEN** the plan's `delivers` names the story, the story is `in-progress`
  with the plan linked under `## Plan`, and each proposed feature it advances
  is `accepted`

#### Scenario: Work with no story or bug is planned

- **WHEN** Plan is asked to plan work that no story or bug describes
- **THEN** Plan hands the work to Capture as a story before writing a plan

#### Scenario: A plan ships

- **WHEN** Ship ships a plan with a zero-CRITICAL Verify report
- **THEN** the delivered item is `done`, each advanced feature is
  `implemented`, and the plan stays in the graph, linked under the item's
  `## Plan`

#### Scenario: A plan is cancelled

- **WHEN** Ship cancels a plan
- **THEN** the plan is deleted, the item returns to `pending` with no
  `## Plan` section, and no `## Fix` is written

#### Scenario: A plan names no item

- **WHEN** a plan lacks `delivers`, or names a key with no document behind it
- **THEN** `iwe schema validate` fails for the missing field, and Ship returns
  a blocker report for Plan revise mode without a lifecycle transition

### Requirement: The release cut reads done stories and bugs

A release cut SHALL take every done story and done bug without `released`,
plus those already stamped with the version being cut; SHALL link each feature
a story advances — under Added when no earlier release page links it, under
Changed otherwise — and each bug under Fixed, with a story advancing
`internal` contributing nothing; SHALL stamp `released: <X.Y.Z>` on each
taken story and bug; and SHALL delete with `iwe delete` every plan whose
delivered item is `stage: done` and whose file is byte-identical at the fetched
remote default branch, removing the emptied `## Plan` section, so that the
squash-merged default branch holds every plan's final version before it is
deleted. A plan absent from the remote default branch, or different there,
SHALL stay for a later cut.

#### Scenario: A cut takes a story and a bug

- **WHEN** a release cut runs with one done story advancing a feature no
  release page links and one done bug, neither stamped
- **THEN** the release page links the feature under Added and the bug under
  Fixed, and both items carry `released: <X.Y.Z>`

#### Scenario: An internal story is cut

- **WHEN** the only done, unstamped item is a story with `advances: internal`
- **THEN** the release page adds no entry for it, and the story is stamped

#### Scenario: A cut deletes a shipped plan on the default branch

- **WHEN** a release cut runs and a plan whose delivered item is done is
  identical at the remote default branch
- **THEN** the plan no longer exists in the graph and the item keeps no
  `## Plan` section

#### Scenario: A shipped plan is not yet on the default branch

- **WHEN** a release cut runs and a plan whose delivered item is done is absent
  from the remote default branch or differs there
- **THEN** the plan stays in the graph, linked under the item's `## Plan`, and
  the cut's report names it

## MODIFIED Requirements

### Requirement: Capture files complete inbox documents

The Capture skill SHALL be the only writer of new bug, proposed-feature, and
story documents, SHALL refuse a document missing any frontmatter field or body
section `SCHEMA.md` requires for its type — for a story, the card sections, its
acceptance criteria in `#### Scenario:` WHEN/THEN form, and `advances` naming
only existing features — SHALL check the graph for a likely duplicate before
filing, SHALL file a feature at `stage: proposed` and never promote it, SHALL
file a bug at `stage: pending` — or at `stage: done` with its `## Fix` when the
same change fixed it — and a story at `stage: pending`, and SHALL link every
filed document from its hub and end with `iwe normalize` and
`iwe schema validate` passing.

#### Scenario: A complete item is captured

- **WHEN** Capture is invoked for a bug, feature, or story whose required
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
  type, including a bug's `severity` or a story's `advances`
- **THEN** Capture writes nothing and lists every missing section and field

#### Scenario: A story advances a feature that does not exist

- **WHEN** a story's `advances` names a feature with no document behind it
- **THEN** Capture writes nothing until the feature is captured as proposed

#### Scenario: A likely duplicate exists

- **WHEN** a fuzzy or lexical search finds an existing document that matches the
  item
- **THEN** Capture writes nothing and shows the match

#### Scenario: A someday idea is promoted

- **WHEN** Capture is invoked for a story with `--from someday/<slug>`
- **THEN** Capture applies the card gate to the idea plus the caller's
  additions, files the story from it, and moves the idea's link out of
  `data/someday.md`

#### Scenario: The item grew from a GitHub issue

- **WHEN** the exploration behind the item started from a GitHub issue
- **THEN** Capture records the issue under `sources:`, and after validation
  closes it with a comment naming the captured document

#### Scenario: Explore or Implement finds an inbox item

- **WHEN** Explore settles a defect, feature, or story, or Implement finds a
  defect or work its plan should not absorb
- **THEN** it hands the item to Capture rather than writing the document itself

### Requirement: Bug and feature documents keep the SCHEMA.md shape

The bug and feature schemas SHALL require the body shape `SCHEMA.md` prescribes
— a bug's `Bug:` H1 and its Symptom, Reproduction, and Root cause sections,
followed by optional Potential solution and Fix sections; a feature's Purpose,
Behaviour, Edge cases, and Open questions sections — in that order, while
allowing additional sections. The bug schema SHALL require a `stage` of
`pending`, `in-progress`, `done`, or `cancelled` and a `severity` of
`critical`, `high`, `medium`, or `low`.

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

### Requirement: Every ship is reviewed against Ship's obligations

`iwe-shipper` SHALL NOT commit a ship while the bug its plan `delivers` has no
`## Fix`. After `iwe-shipper` ships a plan, `/agentdev:iwe-ship` and Plan revise
mode answering a Ship blocker report SHALL dispatch `iwe-ship-reviewer` in ship
mode with the plan key. When it reports gaps, they SHALL dispatch `iwe-shipper`
with the operation `fix` and the gaps quoted, which SHALL perform only those
operations without running Verify, and review again, for at most 3 fix rounds.
`iwe-ship-reviewer` SHALL append the `## Ship review` checklist to the story or
bug the plan `delivers` only when every item is `confirmed` or `N/A`.

#### Scenario: a ship meets every obligation

- **WHEN** `iwe-ship-reviewer` finds every obligation met
- **THEN** the delivered item ends with a `## Ship review` whose every item is
  ticked `confirmed` or `N/A`.

#### Scenario: a ship leaves a gap

- **WHEN** `iwe-ship-reviewer` reports a delivered bug with no `## Fix`
- **THEN** `iwe-shipper` runs `fix` for that gap alone, without Verify, and the
  ship is reviewed again.

#### Scenario: gaps outlast three rounds

- **WHEN** a gap remains after 3 fix rounds
- **THEN** Ship reports the gap and the delivered item has no `## Ship review`.

#### Scenario: a plan is reviewed before implementation

- **WHEN** `iwe-ship-reviewer` runs in plan mode
- **THEN** it reports whether the plan gives Ship what it needs and changes
  nothing.
```

[pre-commit-gate](../spec/pre-commit-gate.md) — the Ship review moves from the
plan to the delivered item:

``` markdown
## MODIFIED Requirements

### Requirement: Ship records are gated in pre-commit

A pre-commit hook SHALL run a checker CLI over every bug and story document
pre-commit passes it, at commit time, over a commit range, and with
`--all-files`. The CLI SHALL fail a bug at `stage: done` that has no `## Fix`
heading, and a bug or story whose `## Ship review` section differs from the
fixed structure, and SHALL report every violation with `path:line`.

#### Scenario: a done bug has no Fix

- **WHEN** a commit stages a bug document at `stage: done` with no `## Fix`
- **THEN** the hook fails and names the document.

#### Scenario: an open bug has no Fix

- **WHEN** a bug document at `stage: pending` or `stage: in-progress` has no
  `## Fix`
- **THEN** the hook passes it.

#### Scenario: a Ship review is malformed

- **WHEN** a bug's or story's `## Ship review` misses an item, reorders the
  items, leaves one unticked, or marks the Verify, item-stage, or hub-edit
  item `N/A`
- **THEN** the hook fails and names the line.

#### Scenario: CI checks every file

- **WHEN** CI runs pre-commit with `--all-files`
- **THEN** the hook checks every bug and story document.
```

[plan-checkbox-evidence](../spec/plan-checkbox-evidence.md) — a plan has no
`stage`, so the done-plan scenarios retire:

``` markdown
## MODIFIED Requirements

### Requirement: The checkbox format is mechanically gated

A test SHALL audit every plan document and report every violation with
`path:line`, not only the first. It SHALL run from the repository's test suite,
from a pre-commit hook when a plan changes, and in the knowledge-base CI job.

#### Scenario: A plan has an unsupported tick

- **WHEN** a plan has a ticked task whose indented `- **Evidence:**` child is
  absent or empty
- **THEN** the gate fails and names the offending `path:line`

#### Scenario: A plan uses the older task heading

- **WHEN** a plan heads its checkboxes `## Tasks` rather than
  `## Implementation Steps`
- **THEN** the gate audits it, because silently skipping a whole document is the
  invisibility this contract exists to remove

#### Scenario: A checkbox appears outside the task section

- **WHEN** a checkbox appears under another section, such as a format example
  under `## Approach`, or inside a fenced code block
- **THEN** the gate does not treat it as a task
```

## Depends on

Every active plan ships first (the maintainer's decision), then a release cut
stamps every done plan; Task 1 checks both. The active plans at filing:

- [Resumable Claude review
  sessions](20260909-resumable-claude-review-sessions.md)
- [Shared BuildKit workspace](20261013-shared-buildkit-workspace.md)
- [Devcontainer home volume](20261030-devcontainer-home-volume.md)
- [Build on unshipped dependencies](20261101-build-on-unshipped-dependencies.md)
- [Per-checkout uv environments](20261101-per-checkout-uv-environments.md)
- [Backfill ship reviews](20261103-backfill-ship-reviews.md)
- [Nested dispatch depth](20261103-nested-dispatch-depth.md)
- [Per-worktree catalog](20261103-per-worktree-catalog.md)
- [Plan review skill](20261103-plan-review-skill.md)
- [Ship records gate](20261103-ship-records-gate.md)
- [Ship review](20261103-ship-review.md)
- [Shipper dispatches verifier](20261103-shipper-dispatches-verifier.md)
- [Main CI cooldown](20261104-main-ci-cooldown.md)
- [Line-free anchors](20261108-line-free-anchors.md)
- [Drop OKF provenance fields](20261108-drop-okf-provenance-fields.md)
- [Label review triggers](20261108-label-review-triggers.md)

Several of these edit `iwe-planner.agent.md`, `iwe-shipper.agent.md`, and the
anchor format; re-locate every anchor below once they have shipped.

## Verification

- `iwe normalize && git diff --exit-code` and `iwe schema validate` pass.
- `uv run pytest docs/knowledge/tests` passes.
- `uv run pytest scripts/tests/test_check_ship_records.py` and
  `uv run pre-commit run ship-records --all-files` pass.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- `iwe find --filter '{type: plan}' -f keys` lists only this plan;
  `iwe find --filter '{type: task}' -f keys` lists only
  `data/backlog/ephemeral-plans-and-stories`.
- `grep -rnE '(\.\./|data/)plans/20' docs/knowledge/data` matches only this
  plan's own links;
  `grep -rn 'stage: planned' docs/knowledge/data .iwe .agents/plugins/agentdev/skills/iwe-bootstrap/assets`
  matches nothing.
- For every file under `.iwe/` and `docs/knowledge/` (`SCHEMA.md`,
  `STRUCTURE.md`, `AGENTS.md`, `README.md`, `CHANGELOG.md`), `cmp` against its
  scaffold copy reports no difference.
- A copy of the scaffold under `/tmp` passes `iwe normalize` with no diff and
  `iwe schema validate`.
- In the files this plan changes,
  `grep -nE 'release:|released.*plan|plans of plans|stage: done.*plan'` finds no
  description of the old model.

## Out of scope

- Renaming "plan": a separate idea, [Rename the plan
  document](../someday/rename-plan-document.md).
- Acceptance criteria on bugs: a bug keeps Symptom / Reproduction / Root cause.
- Rewriting the moved backlog tasks as cards: each is promoted with
  `/agentdev:iwe-capture task --from someday/<slug>` when picked up.
- Any change to `/agentdev:iwe-branch-name`.
- The `## Tasks` legacy heading support in the checkbox gate.

## Key references

- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "Do not assume a prior Ship invocation"`
  — step 1, which reads the plan's `release` items
- `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md#plan-mode` — plan
  mode's `release` checks
- `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md#ship-mode › "Find the ship."`
  — ship mode, which finds the ship by the plan's `stage: done`
- `scripts/check-ship-records.py::SHIP_REVIEW_ITEMS` — the fixed checklist
- `scripts/check-ship-records.py::check` — dispatches on `type: bug` and
  `type: plan`
- `.pre-commit-config.yaml#repos` › `ship-records` — the hook's `files` pattern
- `.iwe/schemas/task.yaml#frontmatter.required` —
  `required: [type, stage, created]`
- `.iwe/schemas/task.yaml#frontmatter.properties.stage` — `stage` enum
- `.iwe/schemas/bug.yaml#frontmatter.properties.stage.enum` —
  `enum: [pending, planned, done, cancelled]`
- `.iwe/schemas/plan.yaml#frontmatter.properties.rank` — `rank`
- `.iwe/schemas/plan.yaml#frontmatter.properties.released` — `released`
- `.iwe/schemas/plan.yaml#frontmatter.properties.release` — `release`
- `.iwe/schemas/tracker.yaml#frontmatter.properties.stage` —
  `stage: { const: living }`
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "A choice is material when it affects scope"`
  — step 2 "Resolve decisions"
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "Write planning state."`
  — step 4 "Write planning state" (frontmatter with `release`)
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "In create mode, add an inclusion link at its"`
  — step 5 "File a created plan" (rank, features accepted, bugs planned, task
  done)
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "Select the operation and inspect current state."`
  — step 1 "Select the operation and inspect current state"
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "Do not verify implementation, synchronize"`
  — step 2 "Cancel without shipping"
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "and skip a result that is already correct."`
  — step 6 "Apply frontmatter transitions idempotently"
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "Cut a release only when the operation is"`
  — step 8 "Cut a release only when the operation is `release <X.Y.Z>`"
- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md#steps › "or its file path. A release cut takes none."`
  — release cut input
- `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md#steps › "— an H1, a body that states the work and why it matters, a"`
  — step 3 **task** gate
- `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md#steps › "data/features/<slug>.md"`
  — step 4 "Write the document"
- `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md#promoting-a-someday-idea`
  — `## Promoting a someday idea`
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#steps › "may be built on while it has an open pull request"`
  — step 3 "Check `## Depends on`"
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#steps › "If the plan key resolves to no plan or to more than"`
  — step 2 "Select the plan"
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#capturing › "Ready to build → write the handoff"`
  — "Ready to build" handoff
- `.agents/plugins/agentdev/skills/iwe-weekly/SKILL.md#steps › "Plans completed in the last 7 days"`
  — "Shipped" query
- `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md#steps › "iwe update -k data/backlog/<slug> --set stage=done --set"`
  — onboarding task closing step
- `docs/knowledge/SCHEMA.md#the-build-order--rank › "yaml"` —
  `## The build order — rank`
- `docs/knowledge/SCHEMA.md#plans--dataplansyyyymmdd-slugmd › "type: plan # required"`
  — `## Plans`
- `docs/knowledge/SCHEMA.md#bugs--databugsslugmd › "type: bug # required"` —
  `## Bugs`
- `docs/knowledge/SCHEMA.md#backlog-tasks--databacklogslugmd › "type: task # required"`
  — `## Backlog tasks`
- `docs/knowledge/STRUCTURE.md#design-decisions › "Ideas harden stepwise"` —
  "The funnel"
- `docs/knowledge/STRUCTURE.md#design-decisions › "An aggregator plan inclusion-links its child"`
  — "Milestones are plans of plans"
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-plans-declare-their-release-impact › "or a non-empty list of the"`
  — Requirement: Plans declare their release impact
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-capture-files-complete-inbox-documents › "backlog-task documents, SHALL refuse a document missing any"`
  — Requirement: Capture files complete inbox documents
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-bug-and-feature-documents-keep-the-schemamd-shape › "H1 and its Symptom, Reproduction, and Root cause sections"`
  — Requirement: Bug and feature documents keep the SCHEMA.md shape
- `docs/knowledge/data/spec/plan-checkbox-evidence.md#requirement-the-checkbox-format-is-mechanically-gated › "not only the first. It SHALL run from the repository's"`
  — Requirement: The checkbox format is mechanically gated
- `docs/knowledge/tests/test_plan_checkboxes.py::check_plan` — the
  `stage == 'done'` branch
- `docs/knowledge/tests/test_released_stamp.py::test_stamps_name_a_release_and_cover_every_older_plan`
  — `test_stamps_name_a_release_and_cover_every_older_plan`
- `docs/knowledge/tests/test_plan_release_schema.py::test_active_plan_without_valid_release_is_rejected`
  — `test_active_plan_without_valid_release_is_rejected`
- `docs/knowledge/tests/test_rank_and_base_schemas.py › "@pytest.fixture(params=['plans', 'bugs', 'backlog'])"`
  — lane parameters `['plans', 'bugs', 'backlog']`
