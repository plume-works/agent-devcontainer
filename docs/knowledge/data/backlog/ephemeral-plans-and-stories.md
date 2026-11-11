---
type: task
stage: pending
priority: medium
created: 2026-11-11
description: Track planned work only as ready stories and bugs, make plans ephemeral implementation documents that a release cut deletes once they are on the default branch, and keep decisions in architecture docs and the iteration goal in milestone.md.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-capture/SKILL.md
- resource: scripts/check-ship-records.py
- resource: .iwe/schemas/task.yaml
- resource: .iwe/schemas/plan.yaml
- resource: .iwe/schemas/bug.yaml
- resource: docs/knowledge/SCHEMA.md
---

# Plans as ephemeral implementation documents; stories as the planned work

## Story

As this repository's maintainer, I want project memory kept at the level
XP/Agile tracks — product goals, decisions, architecture for the current
iteration, and acceptance criteria for stories — with planned work living only
in stories and bugs, so that a plan is a short-lived implementation document and
`/agentdev:iwe-plan` never has to ask *what* to build.

## Acceptance criteria

### Scenario: A story is missing a card section

- **WHEN** a story in `data/backlog/` lacks `## Story`,
  `## Acceptance criteria`, `## Decisions`, or `## Out of scope`, has them out
  of order, or does not say which features it advances (or `internal`)
- **THEN** `iwe schema validate` fails and names the story, and
  `/agentdev:iwe-capture task` refuses to file it

### Scenario: A plan is written for a story

- **WHEN** `/agentdev:iwe-plan` writes a plan for a pending story or bug
- **THEN** the plan names that one story or bug, the story or bug moves to
  `in-progress` and links the plan under its `## Plan` section, and each
  `proposed` feature the story advances moves to `accepted`

### Scenario: The work has no story or bug yet

- **WHEN** `/agentdev:iwe-plan` is asked for work that no story or bug in the
  graph describes
- **THEN** `/agentdev:iwe-plan` sends the work to `/agentdev:iwe-capture task`
  first and writes the plan only after the story is filed

### Scenario: A plan ships

- **WHEN** `/agentdev:iwe-ship` ships a plan that `/agentdev:iwe-verify`
  reported with zero CRITICAL findings, on any branch
- **THEN** the plan's story or bug is `done`, each feature the story advances is
  `implemented`, the plan file stays in `data/plans/`, and `iwe-ship-reviewer`
  appends `## Ship review` to the story or bug

### Scenario: A release is cut

- **WHEN** `/agentdev:iwe-ship release <X.Y.Z>` runs
- **THEN** the release page links each feature a done story advances and each
  done bug, each of those stories and bugs gets `released: <X.Y.Z>`, and every
  plan whose story or bug is done is deleted if its file is identical on the
  remote default branch; a plan not yet on the default branch stays until the
  next release

### Scenario: A plan is cancelled

- **WHEN** `/agentdev:iwe-ship` cancels a plan
- **THEN** the plan file is deleted at once and its story or bug returns to
  `pending`

### Scenario: The graph moves to the new model

- **WHEN** the change that implements this story merges
- **THEN** no done or cancelled plan remains in `data/plans/`, every link that
  pointed at one points at its permalink on the default branch, every earlier
  backlog task is in `data/someday/`, and `data/backlog/` holds only stories in
  the card shape

## Decisions

Every decision here is the maintainer's.

- **Feature vs story.** A feature stays the long-lived document for a
  capability; a story is one increment that advances one or more features, or is
  `internal`.
- **A story in `data/backlog/` is ready to plan.** Work not ready yet stays in
  `data/someday/`. A spike is a story whose acceptance criterion is a decision
  recorded in `data/architecture/`.
- **Stages.** Stories and bugs go `pending → in-progress → done`, or
  `cancelled`. `/agentdev:iwe-plan` writes a plan only for one ready story or
  bug.
- **A plan reaches the default branch before it is deleted.** The default branch
  is squash-merged, so `/agentdev:iwe-ship` deletes no plan when it ships;
  `/agentdev:iwe-ship release` deletes a shipped plan once the plan is on the
  default branch. Cancelling deletes the plan at once.
- **`## Ship review` goes on the story or bug**, which outlives the plan; the
  `ship-records` pre-commit hook checks it there.
- **`/agentdev:iwe-ship release` reads done stories and bugs**, not plans.
- **Build order.** Only stories and bugs carry `rank`.
- **Iteration.** `data/milestone.md` holds the current iteration's goal and the
  product goal it serves; `data/product.md` gains `## Goals`.
- **Specs stay.** A plan copies its story's acceptance scenarios into
  `## Spec changes`, and `/agentdev:iwe-ship` merges them into `data/spec/` as
  today.
- **Switch-over.** Every active plan ships under the current rules, and one last
  release is cut under them, before the graph moves to the new model.
- **Rejected:**
  - features as stories: a feature spans many plans, and release pages link it;
  - a separate `ready` stage: `data/someday/` already holds work that is not
    ready;
  - keeping a plan only on its work branch or in `.tmp/`: that breaks the plan
    pull request, resuming work, and the checkbox evidence
    `/agentdev:iwe-verify` reads;
  - dropping or folding `data/spec/`: most specs have no feature, and a story's
    criteria go stale once a later story changes the behaviour;
  - `/agentdev:iwe-ship` deleting the plan once it is on the default branch:
    that forces a separate ship pull request for every plan.

## Out of scope

- Renaming "plan": a separate idea, [Rename the plan
  document](../someday/rename-plan-document.md).
- Acceptance criteria on bugs: a bug keeps Symptom / Reproduction / Root cause.
- Rewriting the earlier backlog tasks as stories: each one is promoted with
  `/agentdev:iwe-capture task --from someday/<slug>` when someone picks it up.
- Any change to `/agentdev:iwe-branch-name`.
