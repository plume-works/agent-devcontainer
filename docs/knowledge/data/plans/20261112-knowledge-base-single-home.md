---
type: plan
created: 2026-11-12
release:
- features/agentdev-iwe-workflow-skills
description: Give every kind of knowledge in the graph one home — behaviour and its rationale in specs, findings and guides in their own types, finished work in a per-release archive — and fold the architecture notes, feature behaviour, and closed history into that layout.
sources:
- resource: docs/knowledge/AGENTS.md
- resource: docs/knowledge/SCHEMA.md
- resource: .iwe/config.toml
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
---

# One home for each kind of knowledge

## Context

The graph states one behaviour in up to three document types, and only one of
them is kept current. Ship maintains `data/spec/`. Nothing maintains
`data/architecture/` or the `## Behaviour` of a feature after it is written, and
closed plans, bugs, and tasks hold rationale that exists nowhere else.

Measured on this checkout:

- `data/architecture/`: 68 notes, 50k words. They mix decisions, behaviour
  written as prose, findings, and procedures.
- `data/features/`: 637 behaviour statements, of which a spec already states
  387, no spec states 227, and a spec contradicts 23.
  `docs/knowledge/migration/scan/features.md` lists them per feature.
- Closed plans, bugs, and tasks: 202 documents, 369k words. 103 hold knowledge
  found nowhere else, 247 items in all. `docs/knowledge/migration/scan/` holds
  one section per document in `closed-0.md` to `closed-7.md`.

The user set the principles for the new layout: DRY and KISS. The user also
decided that the whole of `docs/knowledge/data/` is redesigned, so no rule in
`docs/knowledge/AGENTS.md`, `docs/knowledge/SCHEMA.md`, or an `iwe-*` rulebook
constrains it, and that this is one plan.

This changes what the workflow skills of [agentdev IWE workflow
skills](../features/agentdev-iwe-workflow-skills.md) write. It absorbs two
backlog tasks: [Remove redundancy from the durable
specs](../backlog/deduplicate-spec-requirements.md) and [Give architecture notes
a lifecycle](../backlog/architecture-note-lifecycle.md).

## Approach

Each kind of knowledge has one home:

| Kind                          | Home                                   |
| ----------------------------- | -------------------------------------- |
| Behaviour                     | `data/spec/` requirements              |
| Why, and what was rejected    | `## Rationale` in the same spec        |
| Findings                      | `data/findings/`, a new `finding` type |
| Procedures                    | `data/guides/`, a new `guide` type     |
| Work in flight                | plans, bugs, tasks                     |
| Finished or retired documents | `data/archive/`                        |

The `architecture` type is retired and the schemas reject it. A feature keeps
`## Purpose` for the release page; once it is implemented, its `## Behaviour` is
a list of links to the spec requirements that own the behaviour.

Finished work is archived, never deleted. `data/archive/` holds one folder per
release plus `next-release`, and each holds one subfolder per type, so every
archived document stays under its type's schema. Whoever closes a plan, bug, or
task moves it to `data/archive/next-release/<type>/` with `iwe rename` in the
same change and removes its hub link. Before the move, Ship writes the plan's
lasting decision, and a closed bug's lasting root cause, into the `## Rationale`
of the spec that owns the behaviour. The release cut moves the contents of
`next-release` into the version's folder. The folder is the only record of a
document's release: the `released` field is removed. A document that no plan
closed belongs to the release that was open when it closed.

The existing documents are migrated in this plan. Migration tasks edit specs
directly: they record behaviour the code already has, each statement checked
against the code first, and a statement the code contradicts is filed as a bug
through `/agentdev:iwe-capture` and not migrated. `## Spec changes` below
carries only the behaviour this plan changes.

The catalog's `iwe-bootstrap` assets scaffold the same layout the rulebooks
write, so they change with the rulebooks. A repository that already consumed the
old scaffold is migrated by a follow-up task this plan files.

Rejected:

- **Moving specs to OpenSpec.** OpenSpec keeps specs outside the graph and
  outside the plan and Ship flow (`origin/specs-over-arch`). The user chose to
  fix the graph in place.
- **`data/architecture/` kept for decisions only.** No script can check that a
  note states no behaviour, and no workflow step maintains a note.
- **Rationale only in the plan that made the decision.** The operating loop's
  Consult step reads specs, not closed plans, so rationale needs a home that
  step reads.
- **Minimal validation for archived documents.** The user chose full validation;
  a schema change is applied to that type's archived documents in the same
  change.
- **A chain of plans.** The user chose one plan.

## Implementation Steps

### Task 1: Schemas and bindings for the new layout

**Files:** Create: `.iwe/schemas/finding.yaml`, `.iwe/schemas/guide.yaml`,
`docs/knowledge/data/findings.md`, `docs/knowledge/data/guides.md`,
`docs/knowledge/tests/test_archive_layout.py`. Modify: `.iwe/config.toml`,
`.iwe/schemas/okf.yaml`, `.iwe/schemas/plan.yaml`, `.iwe/schemas/feature.yaml`,
`docs/knowledge/data/index.md`, `docs/knowledge/tests/test_released_stamp.py`.

- [ ] `.iwe/config.toml` binds the plan, bug, task, and feature schemas to
  `data/archive/*/<type>/**` beside their live folders, and binds `finding` and
  `guide` to `data/findings/**` and `data/guides/**`, with both hubs in
  `[schemas.hub]` and in `data/index.md`. `iwe schema validate` passes.
- [ ] A test in `test_archive_layout.py` runs `iwe schema validate` on a scratch
  graph under `/tmp` holding an archived plan with an invalid `stage` and
  expects a failure naming the document.
- [ ] A test in `test_archive_layout.py` expects a failure for a document whose
  frontmatter says `type: architecture`.
- [ ] A test in `test_archive_layout.py` expects a failure for a plan carrying
  `released`. `test_released_stamp.py` is deleted.
- [ ] A finding requires `## Measurement` and `## Closing` and carries no
  `stage`; a guide requires an H1 and carries no `stage`. A test in
  `test_archive_layout.py` expects a failure for a finding without `## Closing`.

### Task 2: The archive placement check

**Files:** Modify: `scripts/check-ship-records.py`,
`scripts/tests/test_check_ship_records.py`, `.pre-commit-config.yaml`.

- [ ] `scripts/check-ship-records.py` fails a plan, bug, or task at
  `stage: done` or `stage: cancelled` that is outside `data/archive/`, with a
  test.
- [ ] It fails a plan without `stage`, or a bug or task at an open stage, that
  is inside `data/archive/`, with a test.
- [ ] It fails a feature at `stage: implemented` or `stage: deprecated` whose
  `## Behaviour` holds a line that is not a list item starting with a link into
  `data/spec/`, with a test.
- [ ] The `ship-records` hook's `files` pattern covers `data/backlog/`,
  `data/features/`, and `data/archive/`.

### Task 3: Scripts that find a plan by key

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py`,
`.agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py`,
`.agents/plugins/agentdev/bin/plan_predecessors.py`, `scripts/check-anchors.py`,
and their tests under `.agents/plugins/agentdev/tests/` and `scripts/tests/`.

- [ ] `iwe-branch-name.py plan-state` reports `done` for a plan that exists only
  under `data/archive/<release>/plans/`, with a test.
- [ ] `plan-state` reports `AMBIGUOUS_PLAN` when a live plan and an archived
  plan share a slug, with a test.
- [ ] `verify-cache.py` resolves an archived plan's key to its archive path,
  with a test.
- [ ] `plan_predecessors.py` reads the stage of a `## Depends on` link that
  points into `data/archive/`, with a test.
- [ ] `scripts/check-anchors.py` resolves every anchor in a `data/guides/`
  document and none in `data/findings/`, `data/archive/`, or
  `data/architecture/`, with tests.

### Task 4: The knowledge base's own documents

**Files:** Modify: `docs/knowledge/AGENTS.md`, `docs/knowledge/SCHEMA.md`,
`docs/knowledge/STRUCTURE.md`, `docs/knowledge/README.md`, `AGENTS.md`,
`docs/knowledge/data/product.md`.

- [ ] `docs/knowledge/AGENTS.md` describes the homes in the `## Approach` table,
  the archive move at close, and the release cut by folder, and names neither
  `data/architecture/` nor `released`.
- [ ] `docs/knowledge/SCHEMA.md` documents the `finding` and `guide` types, the
  archive folders, and the implemented feature's `## Behaviour`, and drops the
  architecture type and the `released` field.
- [ ] `docs/knowledge/STRUCTURE.md` and `docs/knowledge/README.md` describe the
  same layout.
- [ ] `AGENTS.md#project-memory`, `AGENTS.md#comments`, and the investigation
  rule in `docs/knowledge/data/product.md#authoring-rules` send a decision to a
  spec's `## Rationale` and a finding to `data/findings/`.

### Task 5: The workflow rulebooks

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`iwe-shipper.agent.md`, `iwe-ship-reviewer.agent.md`, `iwe-verifier.agent.md`,
`iwe-implementer.agent.md` in the same folder, and
`.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`, `iwe-capture/SKILL.md`,
`iwe-setup/SKILL.md`, `iwe-audit/SKILL.md`, `iwe-ship/SKILL.md`,
`iwe-verify/SKILL.md`, `iwe-weekly/SKILL.md` in the skills folder; and
`scripts/check-ship-records.py` for the checklist.

- [ ] `iwe-planner.agent.md#the-three-forms-of-spec-changes` says a plan names
  the `## Rationale` entries each touched spec gains.
- [ ] `iwe-planner.agent.md#steps` has a plan that grew from a backlog task mark
  the task done and move it to the archive.
- [ ] `iwe-shipper.agent.md#steps`: after the spec merge, Ship writes the
  `## Rationale` entries, replaces each listed implemented feature's
  `## Behaviour` with requirement links, sets the stages, and moves the plan and
  each bug it closes to `data/archive/next-release/` with `iwe rename`, removing
  their hub links. Cancel moves the plan the same way.
- [ ] `iwe-shipper.agent.md#steps`: the release cut reads the plans under
  `data/archive/next-release/plans/`, moves every document in `next-release` to
  `data/archive/<X.Y.Z>/`, and writes no `released`.
- [ ] The `## Ship review` template in `iwe-ship-reviewer.agent.md` and the
  fixed structure in `scripts/check-ship-records.py` replace the "edited no hub"
  item with items for the archive move and the `## Rationale` entries, with the
  checker's tests updated.
- [ ] `iwe-explore/SKILL.md#capturing`, `iwe-implementer.agent.md`
  (`#capturing-what-implementation-turns-up`), and `iwe-setup/SKILL.md` route a
  decision to a spec's `## Rationale`, a finding to `data/findings/`, and a
  procedure to `data/guides/`.
- [ ] `iwe-capture/SKILL.md` moves a bug filed at `stage: done`, and a task or
  bug it closes, to the archive.
- [ ] No file under `.agents/plugins/agentdev/agents/` or
  `.agents/plugins/agentdev/skills/iwe-*/` outside `iwe-bootstrap/assets/` names
  `data/architecture` or the `released` field.
- [ ] `uv run pytest .agents/plugins/agentdev/tests -k 'validate or catalog'`
  and the `validate_agent_files` pre-commit hook pass on the catalog.

### Task 6: The bootstrap scaffold

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/` (its
`.iwe/`, `docs/knowledge/AGENTS.md`, `SCHEMA.md`, `STRUCTURE.md`, hubs, and
example documents),
`.agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md`,
`.agents/plugins/agentdev/tests/test_iwe_bootstrap.py`.

- [ ] The scaffold installs the `finding` and `guide` types, the archive
  bindings, and no architecture hub or example, and
  `uv run pytest .agents/plugins/agentdev/tests/test_iwe_bootstrap.py` passes.
- [ ] `/agentdev:iwe-capture task` files a backlog task for migrating a
  repository that consumed the earlier scaffold.

### Task 7: Fold the architecture notes

For each note: check every behaviour statement against the code it anchors. A
statement the code confirms and no spec holds becomes a requirement with a
scenario in the destination spec. The decision in force and its rejected
alternatives go to that spec's `## Rationale`. A statement the code contradicts
is filed through `/agentdev:iwe-capture bug`. The note then moves to
`data/archive/<release>/architecture/` — the release whose plan wrote it, or
`next-release` — keeping `type: architecture`. Destinations are the table in
`origin/specs-over-arch:openspec/changes/specs-sole-source-of-truth/design.md`
(commit `19fbac9f`), with `openspec/specs/<slug>` read as `data/spec/<slug>`.

**Files:** Modify: `docs/knowledge/data/spec/*.md`,
`docs/knowledge/data/spec.md`. Create: `docs/knowledge/data/findings/*.md`,
`docs/knowledge/data/guides/*.md`, new specs `catalog-scripts`,
`cloud-session-host`, `devcontainer-state`, `ci-workflows`, `pr-description`,
`supported-harnesses`. Move: `docs/knowledge/data/architecture/*.md`.

- [ ] The notes destined for `ai-review-gate` are folded and archived.
- [ ] The notes destined for `iwe-workflow-skills` are folded and archived.
- [ ] The notes destined for `agentdev-runtime-images` are folded and archived.
- [ ] The notes destined for `dependency-updates` are folded and archived.
- [ ] The notes destined for `catalog-lifecycle` and the new
  `supported-harnesses` are folded and archived.
- [ ] The notes destined for `claude-remote-control` are folded and archived.
- [ ] The notes with one destination each (`agent-file-discovery`,
  `plan-checkbox-evidence`, `pre-commit-gate`, `devcontainer-git-credentials`,
  `line-free-anchors`, `stacked-prs`, `devcontainer-docker-storage`,
  `devcontainer-opencode-policy`, `self-improve-learning-loop`) are folded and
  archived.
- [ ] The notes destined for `template-consumption`, `opencode-catalog-bridge`,
  `standalone-opencode-runtime`, and `nested-agent-dispatch` are folded and
  archived.
- [ ] The notes that describe behaviour no spec owns are folded into the new
  specs `catalog-scripts`, `cloud-session-host`, `devcontainer-state`,
  `ci-workflows`, and `pr-description`, each linked from `data/spec.md`, and
  archived.
- [ ] Every note whose sections are Measurement, Question, or Closing is a
  `data/findings/` document linked from `data/findings.md`.
- [ ] `drqp-devcontainer-testing`, `sibling-devcontainer-testing`,
  `skill-rehearsal-runs`, and `worktree-hooks` are `data/guides/` documents
  linked from `data/guides.md`.
- [ ] `docs/knowledge/data/architecture/` and
  `docs/knowledge/data/architecture.md` do not exist, and
  `.iwe/schemas/architecture.yaml` is bound only to
  `data/archive/*/architecture/**`.
- [ ] No code comment, workflow, or script outside `docs/knowledge/` cites
  `architecture/<slug>`:
  `git grep -nE 'architecture/[a-z0-9-]+' -- ':!docs/knowledge' ':!docs/research'`
  prints nothing.

### Task 8: Fold feature behaviour

Input: `docs/knowledge/migration/scan/features.md`. For each implemented
feature, each statement its row counts as unique and its destination table keeps
becomes a requirement or scenario in the destination spec after a check against
the code. Each conflict is resolved for the code: the stale side is corrected,
and a spec the code contradicts is corrected as a recorded behaviour, not a
change. Then the feature's `## Behaviour` becomes links to the owning
requirements and `## Edge cases` is removed.

**Files:** Modify: `docs/knowledge/data/features/*.md`,
`docs/knowledge/data/spec/*.md`, `.iwe/schemas/feature.yaml`. Create: new specs
`pr-review`, `ci-python-environment`.

- [ ] Every conflict listed under `## Conflicts` in `features.md` has its stale
  side corrected, or a bug filed through `/agentdev:iwe-capture bug` when the
  code is the wrong side.
- [ ] `data/spec/opencode-web.md` and `data/spec/catalog-lifecycle.md` agree on
  where OpenCode's data lives, matching `.devcontainer/docker-compose.yml`.
- [ ] Every implemented feature whose owning spec is `iwe-workflow-skills`,
  `plan-checkbox-evidence`, `git-new-branch`, `iwe-branch-name`, `stacked-prs`,
  `update-branch`, or `pr-merge-conflicts` is folded.
- [ ] Every implemented feature whose owning spec is `ai-review-gate`,
  `template-consumption`, `pre-commit-gate`, `dependency-updates`, or
  `image-pinning` is folded, with the new `pr-review` and
  `ci-python-environment` specs linked from `data/spec.md`.
- [ ] Every other implemented feature is folded.
- [ ] The five deprecated features are in `data/archive/` under the release that
  deprecated them, and `data/features.md` no longer links them.
- [ ] `uv run scripts/check-ship-records.py docs/knowledge/data/features/*.md`
  passes.

### Task 9: Distil and archive the closed history

Input: `closed-0.md` to `closed-7.md` under `docs/knowledge/migration/scan/`.
For each document with the verdict `HAS UNIQUE KNOWLEDGE`, each listed item is
checked against the code and then written to its owning spec — a `behaviour`
item as a requirement or scenario, every other kind in `## Rationale` — or is
struck in the scan file with the reason it is dropped. A constraint that is
about tests goes to `AGENTS.md#tests`. A conflict the scan lists is handled as
in Task 8.

**Files:** Modify: `docs/knowledge/data/spec/*.md`, `AGENTS.md`,
`docs/knowledge/data/releases/*.md`, `docs/knowledge/data/plans.md`,
`docs/knowledge/data/bugs.md`, `docs/knowledge/data/backlog.md`. Move: every
closed document under `docs/knowledge/data/plans/`, `bugs/`, and `backlog/`.

- [ ] Every item in `closed-0.md` is in a spec or struck with a reason.
- [ ] Every item in `closed-1.md` is in a spec or struck with a reason.
- [ ] Every item in `closed-2.md` is in a spec or struck with a reason.
- [ ] Every item in `closed-3.md` is in a spec or struck with a reason.
- [ ] Every item in `closed-4.md` is in a spec or struck with a reason.
- [ ] Every item in `closed-5.md` is in a spec or struck with a reason.
- [ ] Every item in `closed-6.md` is in a spec or struck with a reason.
- [ ] Every item in `closed-7.md` is in a spec or struck with a reason.
- [ ] `data/spec/iwe-workflow-skills.md` states where Ship reads a dependency's
  stage, and no spec contradicts it.
- [ ] A `## Rationale` entry in `data/spec/template-consumption.md` records why
  the codebase map was retired.
- [ ] Every done plan with `released: 1.0.0` is under
  `data/archive/1.0.0/plans/` with `released` removed.
- [ ] Every done plan with `released: 2.0.0` is under
  `data/archive/2.0.0/plans/` with `released` removed.
- [ ] Every done plan with `released: 2.1.0` is under
  `data/archive/2.1.0/plans/` with `released` removed.
- [ ] Every done plan without `released`, and every cancelled plan, is under
  `data/archive/next-release/plans/` or the folder of the release open when it
  closed.
- [ ] Every closed bug and task is in the archive folder of the plan that closed
  it, or of the release open when it closed.
- [ ] `data/plans.md`, `data/bugs.md`, and `data/backlog.md` link only open
  documents, and each release page links the documents in its folder under
  `## Archive`.
- [ ] `uv run scripts/check-ship-records.py` over every document under
  `docs/knowledge/data/` passes.

### Task 10: One home for each rule inside a spec

**Files:** Modify: `docs/knowledge/data/spec/*.md`.

- [ ] In every spec, a rule stated in more than one requirement is stated in one
  and referenced from the others, and a scenario that only restates its
  requirement is removed. `/agentdev:semantic-refactor-audit` reports every
  behaviour the specs stated before the task has exactly one home after it.

### Task 11: Remove the migration inputs

**Files:** Delete: `docs/knowledge/migration/`.

- [ ] `docs/knowledge/migration/` does not exist.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md):

``` markdown
## ADDED Requirements

### Requirement: Each kind of knowledge has one home

The graph SHALL hold behaviour only in `data/spec/` requirements, the decision
in force and the alternatives it rejected only in the `## Rationale` section of
the spec that owns the behaviour, a finding only in `data/findings/`, and a
procedure only in `data/guides/`. The schemas SHALL reject a document of type
`architecture` outside `data/archive/`. A feature at `stage: implemented` or
`stage: deprecated` SHALL state behaviour only as links to spec requirements,
and the `ship-records` check SHALL fail one that does not. Nothing checks
mechanically that a `## Rationale` states no behaviour; the Durable Knowledge
Auditor and review judge it.

#### Scenario: An architecture note is written

- **WHEN** a document outside `data/archive/` carries `type: architecture`
- **THEN** `iwe schema validate` fails and names the document

#### Scenario: An implemented feature restates behaviour

- **WHEN** a feature at `stage: implemented` has a `## Behaviour` line that is
  not a list item starting with a link into `data/spec/`
- **THEN** the `ship-records` check fails and names the line

#### Scenario: A proposed feature describes behaviour

- **WHEN** a feature at `stage: proposed` or `stage: accepted` describes its
  behaviour in prose
- **THEN** the `ship-records` check passes it

### Requirement: Closed work is distilled and archived by release

Whoever sets a plan, bug, or backlog task to `stage: done` or
`stage: cancelled` SHALL, in the same change, move it with `iwe rename` to
`data/archive/next-release/<type>/` and remove its hub link. Before Ship moves
a plan, it SHALL write the plan's decision in force and its rejected
alternatives, and each closed bug's lasting root cause, into the `## Rationale`
of the spec that owns the behaviour, and SHALL replace the `## Behaviour` of
each feature it marks implemented with links to the owning requirements. The
release cut SHALL move every document under `data/archive/next-release/` to
`data/archive/<X.Y.Z>/`, keeping the type subfolders, and SHALL link each from
the release page. The folder SHALL be the only record of a document's release:
no document SHALL carry `released`. Every archived document SHALL pass the
schema of its type. The `ship-records` check SHALL fail a closed document
outside `data/archive/` and an open one inside it.

#### Scenario: A plan ships

- **WHEN** Ship marks a plan done
- **THEN** the plan and each bug it closed are under
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
  `data/archive/X.Y.Z/`, and the release page links each

#### Scenario: A closed document is left in place

- **WHEN** a commit stages a plan, bug, or task at `stage: done` or
  `stage: cancelled` outside `data/archive/`
- **THEN** the `ship-records` check fails and names the document

#### Scenario: An archived document breaks its schema

- **WHEN** an archived plan carries a `stage` its schema does not allow
- **THEN** `iwe schema validate` fails and names the document

## MODIFIED Requirements

### Requirement: Plans declare their release impact

The plan schema SHALL require every active plan to carry a `release` frontmatter
value: `internal`, or a non-empty list of the `features/` and `bugs/` keys the
work adds, changes, or fixes. The Plan skill SHALL set that value when it files
a plan, SHALL declare `internal` only when no workspace user or template
consumer sees a difference, SHALL have Capture file a missing feature before it
files the plan, and SHALL set every bug the plan lists to `stage: planned`. Ship
SHALL take a plan's release entries only from that value, SHALL never create a
feature, SHALL write the `## Fix` of each bug it marks done, and SHALL return
each listed bug to `stage: pending` when it cancels the plan. The release cut
SHALL build the release page from the `release` values of the plans under
`data/archive/next-release/plans/`.

#### Scenario: A plan introduces user-visible behavior with no feature

- **WHEN** Plan files a plan whose work changes what a workspace user or
  template consumer sees, and no feature describes it
- **THEN** Plan hands the feature to Capture, lists its key in `release`, and
  sets the feature to `stage: accepted`

#### Scenario: A plan lists a bug

- **WHEN** Plan files a plan whose `release` lists a bug at `stage: pending`
- **THEN** Plan sets the bug to `stage: planned`

#### Scenario: A plan changes nothing users see

- **WHEN** the release cut reads an archived plan that declares
  `release: internal`
- **THEN** the plan adds no Added, Changed, or Fixed entry

#### Scenario: A plan declares features and bugs

- **WHEN** Ship ships a plan whose `release` lists feature and bug keys
- **THEN** Ship marks each feature implemented and each bug done, and writes
  each bug's `## Fix` describing the shipped fix and linking the plan

#### Scenario: A release cut collects declared documents

- **WHEN** the release cut reads the archived plans of the release
- **THEN** the release page links each listed document once — a feature no
  earlier release page links under Added, a feature an earlier page links under
  Changed, a bug under Fixed

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

### Requirement: Ship synchronizes durable specs by intelligent merge

The Ship skill SHALL treat a plan-local spec delta as reviewed intent, SHALL
derive durable updates only from intent that agrees with verified shipped
behavior, SHALL preserve unaffected requirements, scenarios, and `## Rationale`
entries, SHALL complete and verify all required spec updates before marking
work done, and SHALL be safe to resume after a partial prior attempt.

#### Scenario: Existing behavior remains unaffected

- **WHEN** a shipped change modifies one requirement or scenario in an existing
  durable spec
- **THEN** Ship updates the changed behavior while preserving all unaffected
  requirements, scenarios, ordering, and `## Rationale` entries

#### Scenario: A structured delta agrees with implementation

- **WHEN** Verify confirms that every planned delta operation and post-change
  scenario agrees with implementation evidence
- **THEN** Ship intelligently merges that behavior into the durable spec and
  verifies the complete resulting contract

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
  duplicate `## Rationale` entries, archive moves, release, and log entries,
  and continues from the first incomplete operation

#### Scenario: A durable spec is retired

- **WHEN** the verified implementation and plan explicitly remove the final
  behavior represented by a durable spec
- **THEN** Ship uses IWE's graph-aware deletion operation, repairs references,
  and does not leave an empty or orphaned spec document

### Requirement: Bug and feature documents keep the SCHEMA.md shape

The bug and feature schemas SHALL require the body shape `SCHEMA.md` prescribes
— a bug's `Bug:` H1 and its Symptom, Reproduction, and Root cause sections,
followed by optional Potential solution and Fix sections; a feature's Purpose
and Behaviour sections, followed by optional Edge cases and Open questions
sections — in that order, while allowing additional sections. The bug schema
SHALL require a `stage` of `pending`, `planned`, `done`, or `cancelled` and a
`severity` of `critical`, `high`, `medium`, or `low`.

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
separate delta files, or a claimed programmatic delta application engine. The
graph SHALL remain a conformant OKF v0.2 bundle — `data/index.md` lists the
hubs, `data/log.md` stays date-grouped, and the `okf`, `okf-index`, and
`okf-log` schemas check every document — and SHALL diverge from OKF only where
OKF costs merges or upkeep. No document under `data/` SHALL set OKF's optional
`status`, because `stage` is the lifecycle field, nor OKF's `generated` or
`verified`, because source control records when and by whom a document changed.
The `banned-frontmatter-keys` pre-commit check SHALL reject a document that
sets any of them.

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
```

`## Rationale` entries for this spec: the decisions and rejected alternatives in
`## Approach`.

[Pre-commit gate](../spec/pre-commit-gate.md):

``` markdown
## MODIFIED Requirements

### Requirement: Ship records are gated in pre-commit

A pre-commit hook SHALL run a checker CLI over every bug, plan, backlog task,
and feature document pre-commit passes it, live or archived, at commit time,
over a commit range, and with `--all-files`. The CLI SHALL fail a bug at
`stage: done` that has no `## Fix` heading, and a plan whose `## Ship review`
section differs from the fixed structure, and SHALL report every violation with
`path:line`. Its archive placement and feature behaviour failures are those
`iwe-workflow-skills` states.

#### Scenario: a done bug has no Fix

- **WHEN** a commit stages a bug document at `stage: done` with no `## Fix`
- **THEN** the hook fails and names the document.

#### Scenario: an open bug has no Fix

- **WHEN** a bug document at `stage: pending` or `stage: planned` has no
  `## Fix`
- **THEN** the hook passes it.

#### Scenario: a Ship review is malformed

- **WHEN** a plan's `## Ship review` misses an item, reorders the items, leaves
  one unticked, or marks the Verify, plan-stage, or archive-move item `N/A`
- **THEN** the hook fails and names the line.

#### Scenario: CI checks every file

- **WHEN** CI runs pre-commit with `--all-files`
- **THEN** the hook checks every bug, plan, task, and feature document.
```

[Line-free anchors](../spec/line-free-anchors.md):

``` markdown
## MODIFIED Requirements

### Requirement: Live anchors resolve

The same script SHALL resolve every anchor under `## Key references` in a plan
without `stage`, and every anchor in a bug or backlog item at `stage: pending`
or `stage: planned` and in every `guides/` document, against the current
checkout, and SHALL fail naming each anchor that does not resolve. A Python
symbol resolves through its syntax tree; a symbol in any other language resolves
when each dotted segment occurs as a whole word in order, so a symbol moved into
a comment still resolves. A quote resolves when it occurs, whitespace-collapsed,
in the anchored region. Anchors elsewhere in a plan, in a finding, and in
archived documents are not resolved.

#### Scenario: A refactor renames an anchored function

- **WHEN** a commit renames a function an active plan's `## Key references` or
  a `guides/` document anchors
- **THEN** the hook fails naming the document and the anchor, until the anchor
  is updated

#### Scenario: A plan names code it will create

- **WHEN** an active plan's task names `scripts/new.py::main`, which does not
  exist yet
- **THEN** the resolver does not check it, because it is outside
  `## Key references`

#### Scenario: An archived plan names deleted code

- **WHEN** a plan under `data/archive/` anchors a file that has since been
  deleted
- **THEN** the resolver does not check it
```

[iwe-branch-name](../spec/iwe-branch-name.md):

``` markdown
## MODIFIED Requirements

### Requirement: Plan state is read in the checkout

The skill SHALL read the plan from the working tree, never from another branch,
looking under `data/plans/` and under every `data/archive/<release>/plans/`,
reporting `missing`, `cancelled`, `done`, `complete` when the plan has no
`stage`, has at least one task checkbox under `## Implementation Steps` or
`## Tasks`, and every such checkbox is ticked, or `incomplete` otherwise, and
SHALL refuse a slug that matches more than one plan with `AMBIGUOUS_PLAN`.

#### Scenario: Working-tree edits count

- **WHEN** a plan's last checkbox is ticked only in the working tree
- **THEN** `plan-state` reports `complete`

#### Scenario: The remote default branch does not count

- **WHEN** a plan is finished only on the remote default branch
- **THEN** `plan-state` reports the plan as the working tree holds it

#### Scenario: A plan with no task checkboxes is not complete

- **WHEN** a plan has no `stage` and no task checkbox
- **THEN** `plan-state` reports `incomplete`

#### Scenario: The older task heading counts

- **WHEN** a plan without `stage` lists every task ticked under `## Tasks`
- **THEN** `plan-state` reports `complete`

#### Scenario: An archived plan is a dependency

- **WHEN** a plan exists only under `data/archive/2.1.0/plans/` at
  `stage: done`
- **THEN** `plan-state` reports `done`

#### Scenario: Two plans share a slug

- **WHEN** `data/plans/20261001-foo` and
  `data/archive/2.1.0/plans/20261020-foo` both exist in the working tree
- **THEN** a lookup by slug `foo` reports `AMBIGUOUS_PLAN`
```

Specs that Tasks 7 to 10 create or extend record behaviour the code already has
and change none: `catalog-scripts`, `cloud-session-host`, `devcontainer-state`,
`ci-workflows`, `pr-description`, `supported-harnesses`, `pr-review`,
`ci-python-environment`.

## Verification

- `iwe normalize` leaves no diff, and `iwe schema validate` exits 0.
- `uv run pytest docs/knowledge/tests scripts/tests/test_check_anchors.py scripts/tests/test_check_ship_records.py`
  passes.
- `uv run pytest .agents/plugins/agentdev/tests/test_iwe_branch_name_plan_state.py .agents/plugins/agentdev/tests/test_plan_predecessors.py .agents/plugins/agentdev/tests/test_verify_cache.py .agents/plugins/agentdev/tests/test_iwe_bootstrap.py`
  passes.
- `uv run scripts/check-anchors.py` exits 0.
- `uv run scripts/check-ship-records.py $(git ls-files 'docs/knowledge/data/**/*.md')`
  exits 0.
- `test ! -e docs/knowledge/data/architecture && test ! -e docs/knowledge/migration`
  succeeds.
- `iwe find --filter '{released: {$exists: true}}' -f keys` prints nothing.
- `iwe find --filter '{type: {$in: [plan, bug, task]}, stage: {$in: [done, cancelled]}}' -f keys`
  prints only keys under `data/archive/`.
- `iwe stats` reports no broken link.

## Out of scope

- Migrating a repository that already consumed the earlier scaffold; Task 6
  files the follow-up.
- Rules about the graph that `docs/knowledge/AGENTS.md`, `SCHEMA.md`, and the
  rulebooks each restate.
- The `product`, `milestone`, `concept`, and `someday` documents.
- Any change to code the specs describe: a contradiction between a spec and the
  code is recorded or filed, never fixed here.

## Key references

- `.iwe/config.toml#schemas.plan` — the path binding each type's archive folders
  join.
- `.iwe/config.toml#schemas.hub` — the closed hub set.
- `.iwe/schemas/architecture.yaml` — the type being retired.
- `.iwe/schemas/feature.yaml` — the feature body shape.
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps` — the spec merge,
  the stage transitions, and the release cut.
- `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md#ship-mode` — the
  fixed checklist.
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps` — where a plan
  closes the backlog task it grew from.
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#capturing` — where a
  decision is routed to `data/architecture/`.
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py::find_plan`
  — looks only under `data/plans`.
- `.agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py::canonical_target`
  — maps a plan to `data/plans/<name>`.
- `.agents/plugins/agentdev/bin/plan_predecessors.py::stage_of` — reads a
  dependency's stage.
- `scripts/check-anchors.py::resolver_spans` — which documents have their
  anchors resolved.
- `scripts/check-ship-records.py::check` — the per-document dispatch the new
  checks join.
- `docs/knowledge/tests/test_released_stamp.py::test_released_must_be_a_version`
  — the test of the field being removed.
- `docs/knowledge/AGENTS.md#the-operating-loop` — the record step that names
  each home.
- `docs/knowledge/SCHEMA.md#features--datafeaturesslugmd` — the feature shape.
