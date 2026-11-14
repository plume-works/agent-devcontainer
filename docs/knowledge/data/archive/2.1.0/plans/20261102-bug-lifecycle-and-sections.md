---
type: plan
created: 2026-11-02
release:
- features/agentdev-iwe-workflow-skills
description: Give bugs an explicit stage lifecycle (pending, planned, done, cancelled) and a required severity, split the bug's Fix into an optional Potential solution and a Fix written only once fixed, stop requiring Key references, and rename the task stage planned to pending.
sources:
- resource: .iwe/schemas/bug.yaml
- resource: .iwe/schemas/task.yaml
- resource: docs/knowledge/SCHEMA.md
- resource: docs/knowledge/AGENTS.md
- resource: .agents/plugins/agentdev/skills/iwe-capture/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-weekly/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
stage: done
completed: 2026-11-02
---

# Bug lifecycle stages and sections

## Context

Changes [IWE workflow skills in
agentdev](../../1.0.0/features/agentdev-iwe-workflow-skills.md).

A bug's `## Fix` carries lifecycle state as prose. Capture requires it
(`iwe-capture/SKILL.md`: "An unfixed bug says so in `## Fix`"), so an open bug
reads "Not yet fixed" or "Open. Planned in [plan]". Ship then sets the bug to
`stage: done` in frontmatter only and never touches the body, so the shipped bug
still says it is unfixed. At least four done bugs read that way:
`ai-rereview-comment-keeps-changes-requested`,
`dispatched-review-gate-not-counted` (fixed by [Assignee-triggered AI
re-reviews](../../2.0.0/plans/20261026-assignee-review-trigger.md)),
`plan-checkbox-over-claiming`, and `pr-update-skips-review-eval`. Open bugs
repeat the pattern (`claude-json-symlink-replaced`,
`ship-ignores-unshipped-dependency`, `image-build-context-whole-repo`,
`responder-cannot-bypass-iwe-ruleset`).

`## Fix` exists to describe the correction itself — what the code does
differently — and a release page's `## Fixed` link leads its reader there. Bugs
reach `done` by two routes, and both need that record: a plan that lists the bug
in `release:`, or a pull request that fixes it directly with no plan — about
half of the done bugs, for example `xpra-test-displays-collide-under-xdist`, are
referenced by no plan.

`## Key references` holds `path:line` anchors that rot with the code
(`cbm-start-failure-latches-degraded` anchors a script that no longer exists),
while frontmatter `sources` already names the paths a bug derives from.

The maintainer decided on 2026-11-02:

- **Bug stages** are `pending | planned | done | cancelled`, and `stage` is
  required. Capture files a bug at `pending`, or directly at `done` when it was
  fixed in the same pull request. Plan moves a bug its plan lists in `release`
  to `planned`. Ship moves it to `done`; Ship's cancellation returns it to
  `pending`. "Absent means open" is retired for bugs.
- **Bug `severity`** is required: `critical | high | medium | low`, measuring
  impact, not urgency. It is descriptive only; nothing ties it to `rank`.
- **Bug sections**: `## Symptom`, `## Reproduction`, `## Root cause` stay
  required. `## Potential solution` (the intended direction, any stage) and
  `## Fix` (the fix that actually shipped, written when the bug becomes `done`)
  are optional. No section states lifecycle. `## Key references` is no longer
  required and Capture stops writing it; existing bugs keep theirs.
- **Who writes Fix**: the fixer in the direct route; Ship in the plan route,
  from Verify's evidence, linking the plan. Nothing enforces that a done bug
  carries a Fix — no schema rule, CI check, or refusal gate.
- **Unknown Reproduction or Root cause** records what is known, the hypotheses
  eliminated and what eliminated them, and links the `backlog/` task whose spike
  settles it — never a bare "unknown". Guidance, not a gate.
- **Tasks** keep their lifecycle: Plan marks a task done when a plan grows from
  it. Only the vocabulary changes, `planned | done | cancelled` to
  `pending | done | cancelled`, so `planned` means only "a plan owns this bug".
- **Migration**: every existing bug gets a stage and a severity — the severity
  for each proposed from its Symptom and reviewed by the maintainer in the pull
  request; open bugs' `## Fix` becomes `## Potential solution` without status
  wording; done bugs whose Fix says unfixed get the shipped fix; the someday
  spike an open bug links becomes a backlog task.

## Approach

Change the contract first, then the graph, then the skills that write it. The
bug schema change and the frontmatter migration of every existing bug land
together, because the new enum and the required `severity` reject the current
graph. The schema keeps its ordered `sections` list with `Potential solution`
and `Fix` at `minContains: 0, maxContains: 1` after `Root cause`, and drops the
`Key references` entry; `additionalSections: true` already admits the existing
bugs' Key references wherever they sit. The whole current graph validates under
that shape, `Fix` before `Root cause` is still rejected, and the relative order
of `Potential solution` and `Fix` is not enforced, which the "no enforcement"
decision accepts.

Rejected: dropping `## Fix` and pointing the release reader at the fixing plan
through `iwe find --references`. It leaves directly fixed bugs — half of all
done bugs — with no record of their fix. Also rejected: giving tasks the bug
lifecycle; a task's job ends when it becomes a plan, and that flow works.

Assumptions for minor details: a plan revision that removes a bug from `release`
returns that bug to `pending`; the promoted spike task gets `priority: medium`;
while rewriting the Capture requirement, its stale "`status`" and "a task under
its priority section" wording is corrected to match `SCHEMA.md` (no `status`
field) and the flat hubs.

## Implementation Steps

### Task 1: New bug schema and the migrated bug frontmatter

**Files:** Modify: `.iwe/schemas/bug.yaml`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/.iwe/schemas/bug.yaml`,
every `docs/knowledge/data/bugs/*.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/bugs/timer-drift-after-sleep.example.md`

- [x] `bug.yaml` (both copies, byte-identical):
  `required: [type, stage, severity]`; `stage` enum
  `pending, planned, done, cancelled`; `severity` enum
  `critical, high, medium, low`; sections `Symptom`, `Reproduction`,
  `Root cause` required, then `Potential solution` and `Fix` each
  `minContains: 0, maxContains: 1`; no `Key references` entry; the schema
  `description` and the order hint name the new shape
  - **Evidence:** commit f1721d3f changes both `bug.yaml` copies identically
    (`cmp` clean); `iwe schema validate` passed in its pre-commit hook
- [x] Every bug without a stage gets `stage: planned` when an active plan lists
  it in `release`, otherwise `stage: pending` (as of `00f33655`: 12 bugs, 6
  planned — recount at implementation)
  - **Evidence:** commit f1721d3f; 12 stage-less bugs migrated, 6 to `planned` —
    exactly the bugs active plans list in `release`
- [x] Every bug gets a `severity`. The proposed value per bug, with a one-line
  reason from its Symptom, goes into the pull request description as a table for
  the maintainer to review
  - **Evidence:** commit f1721d3f gives all 57 bugs a `severity`; the per-bug
    table with reasons is in the description of
    [#641](https://github.com/plume-works/agent-devcontainer/pull/641)
- [x] The bootstrap example bug is `stage: pending` with a `severity`, its
  `## Fix` renamed `## Potential solution`, and no `## Key references`
  - **Evidence:** commit f1721d3f;
    `uv run pytest .agents/plugins/agentdev/tests/test_iwe_bootstrap.py docs/knowledge/tests`
    passed (121 tests)
- [x] `iwe normalize` and `iwe schema validate` pass
  - **Evidence:** commit f1721d3f; both passed locally and in its
    `iwe-normalize` / `iwe-schema-validate` pre-commit hooks

### Task 2: Schema tests for the bug shape

**Files:** Modify: `docs/knowledge/tests/test_body_shape_schemas.py`,
`docs/knowledge/tests/test_rank_and_base_schemas.py` (only if its open-item
selection breaks)

- [x] The `bug-out-of-order` case moves a required section (`Root cause` after
  `Symptom`) instead of the now-optional `Fix`
  - **Evidence:** commit dcd65bf0 moves `Root cause` after `Symptom`; the case
    passes
- [x] New rejection cases: a bug with no `stage`, a bug with no `severity`, a
  bug whose `severity` is outside the enum
  - **Evidence:** commit dcd65bf0 adds
    `test_malformed_bug_frontmatter_is_rejected` (no stage, no severity, bad
    severity, bad stage)
- [x] New acceptance cases: a bug with neither `Potential solution` nor `Fix`,
  and one with both
  - **Evidence:** commit dcd65bf0 adds `test_optional_bug_sections_are_accepted`
    (neither, both)
- [x] `uv run pytest docs/knowledge/tests/test_body_shape_schemas.py docs/knowledge/tests/test_rank_and_base_schemas.py`
  passes
  - **Evidence:** commit dcd65bf0; the two files passed, 41 tests;
    `test_rank_and_base_schemas.py` needed no change

### Task 3: Task stage `planned` becomes `pending`

**Files:** Modify: `.iwe/schemas/task.yaml` and its bootstrap copy, every
`docs/knowledge/data/backlog/*.md` at `stage: planned`, the four bootstrap seed
tasks under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/backlog/`,
`docs/knowledge/tests/test_iwe_seed.py`,
`.agents/plugins/agentdev/tests/test_iwe_bootstrap.py`,
`.agents/plugins/agentdev/skills/iwe-weekly/SKILL.md`

- [x] `task.yaml` (both copies): enum and description `pending, done, cancelled`
  - **Evidence:** commit 08e9aecf; both copies identical (`cmp` clean),
    `iwe schema validate` passed
- [x] Every task at `stage: planned` (13 as of `00f33655`) and the four seed
  tasks move to `stage: pending`
  - **Evidence:** commit 08e9aecf moves 13 backlog tasks and the 4 seed tasks to
    `pending`
- [x] The seed and bootstrap tests expect `pending` for the onboarding tasks
  - **Evidence:** commit 08e9aecf updates `test_iwe_seed.py` and
    `test_iwe_bootstrap.py`
- [x] Weekly's backlog-head query selects `stage: pending`
  - **Evidence:** commit 08e9aecf changes the backlog-head query in
    `iwe-weekly/SKILL.md` to `stage: pending`
- [x] `uv run pytest docs/knowledge/tests/test_iwe_seed.py .agents/plugins/agentdev/tests/test_iwe_bootstrap.py`
  passes
  - **Evidence:** commit 08e9aecf; the two files passed, 39 tests

### Task 4: SCHEMA.md and knowledge AGENTS.md describe the new model

**Files:** Modify: `docs/knowledge/SCHEMA.md`, `docs/knowledge/AGENTS.md`, and
their bootstrap copies under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/`

- [x] `SCHEMA.md` Bugs section: the stage enum with what moves each stage, the
  `severity` field and its meaning, the body sections with which are optional,
  and that no section states lifecycle; Backlog tasks:
  `pending | done | cancelled`; the `rank` paragraph names pending and planned
  bugs and pending tasks
  - **Evidence:** commit 049831ae rewrites the Bugs section, the task stage
    line, and the `rank` paragraph
- [x] `AGENTS.md`: the lifecycle bullets (bug found, work ships, plan abandoned,
  actionable item), the build-order sentence, and the stage vocabularies match
  `SCHEMA.md`
  - **Evidence:** commit 049831ae updates the build-order sentence, the
    actionable-item, work-starts, work-ships, plan-abandoned and bug-found
    bullets, and the stage vocabularies
- [x] Both bootstrap copies are byte-identical to the repository's
  (`test_scaffold_support_files_match_the_publisher_workspace` passes)
  - **Evidence:** commit 049831ae;
    `test_scaffold_support_files_match_the_publisher_workspace` passed

### Task 5: Capture files bugs in the new shape

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md`

- [x] Step 3's bug gate requires the `Bug:` H1, `## Symptom`, `## Reproduction`,
  `## Root cause` and a `severity`; names `## Potential solution` and `## Fix`
  as optional; and no longer asks for Key references or anchors
  - **Evidence:** commit 8c189a48 rewrites the bug gate in
    `iwe-capture/SKILL.md` step 3; `validate_agent_files --recommend` reported 0
    errors, 0 warnings
- [x] An unknown Reproduction or Root cause states what is known, the hypotheses
  eliminated and what eliminated them, and links the `backlog/` task that
  settles it; no section states lifecycle
  - **Evidence:** commit 8c189a48, same step 3 bullet
- [x] Step 4 files a bug at `stage: pending`, or at `stage: done` with a
  `## Fix` describing the fix when the bug was fixed in the same change; a task
  at `stage: pending`
  - **Evidence:** commit 8c189a48 rewrites the step 4 `stage` bullet

### Task 6: Plan moves listed bugs to `planned`

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [x] Step 5 sets every bug the plan lists in `release` to `stage: planned`, as
  it sets listed features to `accepted`
  - **Evidence:** commit c7f5f7d6, `iwe-planner.agent.md` step 5;
    `validate_agent_files --recommend` reported 0 errors, 0 warnings
- [x] Revise mode returns a bug the revision removes from `release` to
  `stage: pending`
  - **Evidence:** commit c7f5f7d6, step 5's revise-mode sentence (a bug added by
    a revision becomes `planned`, one removed returns to `pending`)

### Task 7: Ship writes the Fix and reverts cancelled bugs

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`

- [x] Step 6: when it sets a listed bug to `stage: done`, Ship writes the bug's
  `## Fix` — the shipped fix in a few sentences, taken from Verify's evidence,
  linking the plan — after any `## Potential solution`; it leaves an
  already-accurate Fix as it is
  - **Evidence:** commit 7ce37f4c adds the `## Fix` bullet to
    `iwe-shipper.agent.md` step 6; `validate_agent_files --recommend` reported 0
    errors, 0 warnings
- [x] Step 2: cancellation sets every bug the plan lists in `release` back to
  `stage: pending`, skipping a bug already there
  - **Evidence:** commit 7ce37f4c, step 2 returns listed bugs at `planned` to
    `pending`, skipping any already moved
- [x] Step 7's re-inspection covers the bug bodies Ship wrote
  - **Evidence:** commit 7ce37f4c, step 7 names the step 6 `## Fix` sections in
    its re-inspection

### Task 8: Weekly lists open bugs by stage

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-weekly/SKILL.md`

- [x] The open-bugs query selects `stage: {$in: [pending, planned]}`
  - **Evidence:** commit 4b1ea469; the query returns the 12 open bugs

### Task 9: Open bugs carry a Potential solution, not status

**Files:** Modify: every `docs/knowledge/data/bugs/*.md` at `stage: pending` or
`stage: planned`

- [x] Each `## Fix` becomes `## Potential solution`, and status wording ("Not
  yet fixed", "Unfixed", "Open.", "Planned in [plan]") is removed while the
  direction it describes stays
  - **Evidence:** commit 57ca665f rewrites all 12 open bugs; none keeps a
    `## Fix`, and `grep -iE 'not yet fixed|unfixed|planned in'` finds no open
    bug
- [x] `self-improve-reviewer-decline-asymmetry`, whose Root cause is unknown,
  links its backlog spike (Task 11); the rule that an unknown Reproduction or
  Root cause links a backlog task binds new captures (Task 5)
  - **Evidence:** commit d326e567 links the bug to
    `data/backlog/self-improve-execution-tracing`; commit 8c189a48 puts the rule
    in `iwe-capture/SKILL.md` step 3

### Task 10: Done bugs describe the fix that shipped

**Files:** Modify: the done bugs whose `## Fix` states they are unfixed or
describes a superseded fix

- [x] Read every `stage: done` bug's `## Fix` and list those that contradict
  `done` — at least `ai-rereview-comment-keeps-changes-requested`,
  `dispatched-review-gate-not-counted`, `plan-checkbox-over-claiming`,
  `pr-update-skips-review-eval`
  - **Evidence:** all 42 done bugs read; six contradict `done`: the four named,
    `stack-guard-reverts-post-merge-rebase` ("Planned by"), and
    `pin-bumps-invalidate-map-docs` ("Planned in"); rewritten in commits
    418f87ac and b5329f49
- [x] Rewrite each listed Fix to describe the fix that shipped, from the plan
  whose `release` lists the bug (`iwe find --references data/bugs/<slug>`),
  linking that plan
  - **Evidence:** commit 418f87ac rewrites the five, each linking the plan whose
    `release` lists it or that fixed it (`plan-checkbox-over-claiming` predates
    `release`: `20260815-honest-plan-checkboxes`); `iwe schema validate` passed

### Task 11: The self-improve spike becomes a backlog task

**Files:** Modify:
`docs/knowledge/data/someday/self-improve-execution-tracing.md` (moved to
`data/backlog/`), `docs/knowledge/data/someday.md`,
`docs/knowledge/data/backlog.md`

- [x] `/agentdev:iwe-capture task --from someday/self-improve-execution-tracing`
  with `priority: medium`, so `self-improve-reviewer-decline-asymmetry` links a
  backlog task
  - **Evidence:** commit d326e567, through `/agentdev:iwe-capture`:
    `data/backlog/self-improve-execution-tracing` at `stage: pending`,
    `priority: medium`; the bug's link follows the rename; `test_hub_order.py`
    passed

### Task 12: Migration note for template consumers

**Files:** Modify: `docs/knowledge/CHANGELOG.md` and its bootstrap copy

- [x] An `[Unreleased]` entry under `### Changed` states the new bug stages and
  `severity`, the optional sections, the task stage rename, and what a cloned
  workspace changes in its own bugs and tasks to validate again
  - **Evidence:** commit d6518a7c adds three `### Changed` entries to both
    copies;
    `uv run pytest docs/knowledge/tests/test_iwe_seed.py .agents/plugins/agentdev/tests/test_iwe_bootstrap.py`
    passed (39 tests)

### Task 13: Verify audits open bugs by stage

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-verifier.agent.md`

- [x] Audit mode selects open bugs with
  `iwe find --filter '{type: bug, stage: {$in: [pending, planned]}}' -f keys`
  and points at a bug whose `sources` paths, or `## Key references` where it has
  one, no longer exist
  - **Evidence:** commit 02c925a4 rewrites the audit-mode bullet in
    `iwe-verifier.agent.md`; the query returns the 12 open bugs;
    `validate_agent_files --recommend` reported 0 errors, 0 warnings

## Spec changes

IWE workflow skills:

``` markdown
## MODIFIED Requirements

### Requirement: Plans declare their release impact

The plan schema SHALL require every active plan to carry a `release` frontmatter
value: `internal`, or a non-empty list of the `features/` and `bugs/` keys the
work adds, changes, or fixes. The Plan skill SHALL set that value when it files
a plan, SHALL declare `internal` only when no workspace user or template
consumer sees a difference, SHALL have Capture file a missing feature before
it files the plan, and SHALL set every bug the plan lists to `stage: planned`.
Ship SHALL take a plan's release entries only from that value, SHALL never
create a feature, SHALL write the `## Fix` of each bug it marks done, and SHALL
return each listed bug to `stage: pending` when it cancels the plan.

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
  `SCHEMA.md` derives for it, stamps `generated` and `sources`, links it from
  its hub at its sorted position, and validates the graph

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
```

## Verification

- `iwe normalize` leaves the tree unchanged and `iwe schema validate` passes.
- `uv run pytest docs/knowledge/tests/` passes.
- `uv run pytest .agents/plugins/agentdev/tests/test_iwe_bootstrap.py` passes.
- `iwe find --filter '{type: bug, stage: {$exists: false}}' -f keys` and
  `iwe find --filter '{type: task, stage: planned}' -f keys` both return
  nothing.
- `iwe find --filter '{type: bug, stage: planned}' -f keys` returns exactly the
  bugs that active plans list in `release`.
- No bug at `stage: pending` or `stage: planned` has a `## Fix` section, and no
  `## Fix` or `## Potential solution` contains "Not yet fixed", "Unfixed", or
  "Planned in" (`grep` over `docs/knowledge/data/bugs/`).
- The pull request description carries the severity table, and the maintainer
  has reviewed it.

## Out of scope

- Reopening a regressed done bug; Capture's duplicate check still stops on it.
- Bugs a plan mitigates rather than fixes; no such bug exists in the graph.
- Ranking the deferred backlog tasks plans link, and owners for the open
  questions implemented features still list.
- Stripping `## Key references` from existing bugs, and any check that a done
  bug carries a `## Fix`.
- Backlog spikes for other existing open bugs whose Reproduction or Root cause
  is unknown; only `self-improve-reviewer-decline-asymmetry` gains one.
- The task lifecycle itself; only its stage name changes.

## Key references

- `.iwe/schemas/bug.yaml#sections.header.sections.header.description` —
  `&order-hint` naming the body order
- `.iwe/schemas/bug.yaml#sections.header.sections.header` — `Fix` section entry
- `.iwe/schemas/bug.yaml#sections.header.sections.header.description` —
  `Key references` section entry
- `.iwe/schemas/bug.yaml#frontmatter` — frontmatter `required: [type]`
- `.iwe/schemas/bug.yaml#frontmatter.properties.type` — `stage` enum
  `[done, cancelled]`
- `.iwe/schemas/task.yaml#frontmatter.properties.stage.enum` — `stage` enum
  `[planned, done, cancelled]`
- `docs/knowledge/SCHEMA.md#the-build-order--rank › "Active plans, pending and planned bugs, and pending backlog"`
  — `rank` paragraph naming open bugs and planned tasks
- `docs/knowledge/SCHEMA.md#bugs--databugsslugmd` — `## Bugs` section
- `docs/knowledge/SCHEMA.md#releases--datareleasesversionmd` — task
  `stage: planned` line
- `docs/knowledge/AGENTS.md#start-of-every-session › "active plans, open bugs, and pending tasks together, lowest"`
  — build-order sentence
- `docs/knowledge/AGENTS.md#the-operating-loop › "priority), linked from"` —
  actionable item `stage: planned`
- `docs/knowledge/AGENTS.md#the-operating-loop › "stage: planned"` — work ships
  bullet
- `docs/knowledge/AGENTS.md#the-operating-loop › "removed (it stays listed —"` —
  bug found bullet
- `docs/knowledge/AGENTS.md#conventions › "lower first. Ranks step by 100 and an"`
  — stage vocabularies
- `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md#steps › "— an H1 starting"`
  — bug gate in step 3
- `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md#steps › "data/features/<slug>.md"`
  — step 4 `stage` per type
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › ". Set every proposed feature the plan lists to"`
  — step 5 sets listed features to `accepted`
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "Do not verify implementation, synchronize"`
  — step 2 cancel without shipping
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "rank"` — step 6
  sets listed bugs to `done`
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#steps › "Open bugs"` —
  audit mode's open-bugs bullet
- `.agents/plugins/agentdev/skills/iwe-weekly/SKILL.md#steps › "iwe find --filter '{type: bug, stage: {$in: [pending"`
  — open-bugs query
- `.agents/plugins/agentdev/skills/iwe-weekly/SKILL.md#steps › "iwe find --filter '{type: task, stage: pending, priority"`
  — backlog-head query
- `docs/knowledge/tests/test_body_shape_schemas.py::workspace` —
  `bug-out-of-order` case moving `Fix`
- `docs/knowledge/tests/test_iwe_seed.py::test_onboarding_tasks_are_present_and_open`
  — onboarding task stage assertion
- `.agents/plugins/agentdev/tests/test_iwe_bootstrap.py::test_installed_graph_carries_what_iwe_setup_needs`
  — onboarding task stage assertion
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-plans-declare-their-release-impact`
  — Requirement: Plans declare their release impact
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-capture-files-complete-inbox-documents`
  — Requirement: Capture files complete inbox documents
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-bug-and-feature-documents-keep-the-schemamd-shape`
  — Requirement: Bug and feature documents keep the SCHEMA.md shape
