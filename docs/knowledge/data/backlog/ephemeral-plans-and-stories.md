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

### Scenario: A story is written without its card

- **WHEN** a backlog story lacks `## Story`, `## Acceptance criteria`,
  `## Decisions`, or `## Out of scope`, has them out of order, or names no
  feature it advances (or `internal`)
- **THEN** `iwe schema validate` fails and names the document, and Capture
  refuses to file it

### Scenario: A story is planned

- **WHEN** Plan creates a plan for a pending story or bug
- **THEN** the plan names that one item, the item is `in-progress` with the plan
  linked under its `## Plan`, and each proposed feature the story advances is
  `accepted`

### Scenario: Work with no story or bug is planned

- **WHEN** Plan is asked to plan work no story or bug describes
- **THEN** the work goes to Capture as a story before a plan is written

### Scenario: A plan ships

- **WHEN** Ship ships a plan with a zero-CRITICAL Verify report, on any branch
- **THEN** the item is `done`, each feature it advances is `implemented`, the
  plan stays in place, and `## Ship review` is appended to the item

### Scenario: A release cut deletes shipped plans on the default branch

- **WHEN** a release cut runs
- **THEN** it links each feature a done story advances and each done bug, stamps
  `released` on them, and deletes every plan whose item is done and whose file
  is identical on the remote default branch; any other plan stays for a later
  cut

### Scenario: A plan is cancelled

- **WHEN** Ship cancels a plan
- **THEN** the plan is deleted at once and the item returns to `pending`

### Scenario: The graph switches over

- **WHEN** the new model lands
- **THEN** done and cancelled plans are gone from the graph with every link to
  them repointed at a permalink on the default branch, every backlog task has
  moved to `data/someday/`, and only cards remain in `data/backlog/`

## Decisions

Every decision here is the maintainer's.

- **Feature vs story.** A feature stays the durable, capability-level document;
  a story is one increment that advances features or is `internal`.
- **Filed means ready.** Unformed work stays in `data/someday/`; a spike is a
  story whose acceptance criterion is a decision recorded in
  `data/architecture/`.
- **Lifecycle.** Stories and bugs go `pending → in-progress → done` (`cancelled`
  stays). A plan is created only from one ready story or bug.
- **Plans reach the default branch before they are deleted.** The default branch
  is squash-merged, so Ship deletes nothing; only the release cut deletes a
  shipped plan, once it is on the default branch. Cancelling deletes at once.
- **The Ship review lives on the delivered story or bug**, which outlives the
  plan; the `ship-records` pre-commit hook gates it there.
- **Release cut** reads done stories and bugs, not plans.
- **Build order.** `rank` lives on stories and bugs only.
- **Iteration.** `milestone.md` becomes the iteration tracker — a goal and the
  product goal it serves; `product.md` gains `## Goals`.
- **Specs stay.** A plan lifts its story's acceptance scenarios into
  `## Spec changes`; Ship merges them as today.
- **Switch.** Every active plan ships under the old rules and a last old-rules
  release is cut before the graph migrates.
- **Rejected:** features as stories (a feature spans many plans, and release
  pages link it); a separate `ready` stage (someday already is the not-ready
  lane); keeping a plan only on its work branch or in `.tmp/` (breaks the plan
  pull request, resumability, and Verify's checkbox evidence); dropping or
  folding `spec/` (most specs have no feature, and per-story criteria go stale);
  Ship deleting the plan once it is on the default branch (forces a separate
  ship pull request for every plan).

## Out of scope

- Renaming "plan": a separate idea, [Rename the plan
  document](../someday/rename-plan-document.md).
- Acceptance criteria on bugs: a bug keeps Symptom / Reproduction / Root cause.
- Rewriting the moved backlog tasks as cards: each is promoted when picked up.
- Any change to `/agentdev:iwe-branch-name`.
