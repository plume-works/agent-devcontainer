---
type: plan
created: 2026-09-06
description: Give template consumption a resumable root-level progress document that records the task list and the user's choices, and summarize the adoption into the consumer's IWE graph when one exists.
generated:
  by: claude-code/opus-5
  at: 2026-09-06T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: docs/knowledge/data/spec/template-consumption.md
- resource: docs/knowledge/data/architecture/template-boundary.md
---

# Track template consumption progress and choices

## Context

Template consumption is long: the guide at
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`
runs a ten-step Workflow A and a six-step Workflow B, four scope questions, and
a PR-template mapping sub-interview. A user is not expected to finish it in one
sitting.

Today the only persisted state is `.agentdev-template.json`, written in setup
mode's final step. An interrupted setup therefore leaves nothing behind: the
next session finds no marker, detects setup mode, and restarts from the first
question. The guide already recognizes interruption as a real state — it tells
the agent to report onboarding as pending and name what is outstanding — but
there is no artifact to resume from, so the report is the whole remedy.

The same gap costs update mode. Its step 3 warns that a path the consumer
customized needs a manual merge rather than a blind overwrite, but nothing
records *which* paths were customized or *why*, so every update re-derives
consumer intent from the diff alone.

This extends the
[template consumption contract](../spec/template-consumption.md) and classifies
new consumer state in [Template boundary](../architecture/template-boundary.md).

## Approach

Add one consumer-root Markdown document, `.agentdev-template-progress.md`,
tracked in git and written from the start of setup rather than the end. It
carries the full task list for the chosen workflow with `- [ ]` checkboxes, and
a choice log that records each decision as it is made. Update mode reads and
extends the same file, so the choice log accrues across episodes and becomes the
consumer-intent record update mode's step 3 currently lacks.

The document lives at the consumer root, not in the consumer's graph. A
consumer's IWE graph does not exist until the seeding step, which is itself one
of the tasks, and a consumer who declines IWE never gets one at all. A root file
exists before task one and serves both consumers, so there is one mechanism
rather than two.

Every `- [x]` carries an indented `- **Evidence:**` child. Nothing mechanically
gates this file — the check in `docs/knowledge/tests/test_plan_checkboxes.py` is
scoped to `docs/knowledge/data/plans/` — so the convention in
[Plan checkbox evidence](../spec/plan-checkbox-evidence.md) is the only thing
distinguishing a real tick from an optimistic one.

`consumed_ref` stays in `.agentdev-template.json` and is parsed only there.
`check-updates.sh` returns `INVALID_MARKER` on a malformed marker, giving the
SHA one parse with one failure signal; a SHA carried in prose has neither, and a
wrongly advanced ref silently skips upstream changes forever. The progress
document names the SHA as context only.

When the consumer keeps IWE, the end of each episode writes a thin summary into
their graph: the adopted SHA, the workflow, the settled choices, and a pointer
back to the root file as the live record. The summary never mirrors the
checklist — two copies of the same state, both extended on every update, would
have nothing keeping them in sync. It records why the consumer is configured
this way; the root file stays the live record.

## Implementation Steps

### Task 1: Specify the progress document

**Files:** Modify: `docs/knowledge/data/spec/template-consumption.md`.

- [ ] Rewrite `## Requirement: adoption is recorded for later updates` so it
  covers both artifacts and states the division of ownership: the JSON marker
  owns `consumed_ref` and remains the only machine-parsed record, the Markdown
  progress document owns the task list and the choice log. Keep the existing
  sentences about diffing only tracked paths and never advancing the SHA past
  what was applied.
- [ ] Add a requirement that setup writes `.agentdev-template-progress.md`
  before executing the guide's steps, not after, so an interrupted session
  leaves a resumable record.
- [ ] Add a requirement that a ticked task in the progress document carries an
  `- **Evidence:**` child, matching
  [Plan checkbox evidence](../spec/plan-checkbox-evidence.md).
- [ ] Add a requirement that the progress document is never a `tracked_paths`
  member, being consumer-created state rather than a template path.
- [ ] Add a scenario for a resumed setup: a session finding a progress document
  with unticked tasks continues from them rather than restarting the interview.

### Task 2: Classify the adoption-state files in the boundary

**Files:** Modify: `docs/knowledge/data/architecture/template-boundary.md`.

- [ ] Add a subsection under `## Default template surface` classifying both
  `.agentdev-template.json` and `.agentdev-template-progress.md` as Customize /
  consumer-created, tracked in git, and never `tracked_paths` members — the same
  treatment `.github/pr-description-guidance.md` already receives at line 156.
  Neither path is currently classified anywhere in the document.

### Task 3: Write the progress document up front in setup mode

**Files:** Modify: `.agents/plugins/agentdev/skills/template-consume/SKILL.md`.

- [ ] Add a `## The Progress Document` section beside `## The Marker File` (line
  21) giving the file's shape: a `## Tasks` section of `- [ ]` items with
  evidence children, a `## Choices` section, and the adopted SHA recorded as
  context with an explicit note that the marker owns the authoritative ref.
- [ ] Insert a step into `## Setup Mode` (line 55), after the workflow question
  at line 63 and before the scope questions at line 68, that generates the task
  list for the chosen workflow and writes the file. The workflow question must
  stay first: Workflow A and Workflow B have different step lists, so the list
  cannot be generated before the workflow is known.
- [ ] Amend setup mode's step 6 (line 87) so the marker and the completed
  progress document are committed together.
- [ ] State that a setup mode run finding an existing progress document resumes
  from its unticked tasks instead of restarting the interview.

### Task 4: Read and extend the progress document in update mode

**Files:** Modify: `.agents/plugins/agentdev/skills/template-consume/SKILL.md`.

- [ ] Add a step at the start of `## Update Mode` (line 99) that reads the
  progress document's choice log, and point step 3's customized-path warning at
  it so a recorded choice is looked up rather than re-derived.
- [ ] Specify how update mode extends the file: a new `## Update <date>` task
  section per episode, derived from `CHANGED_PATHS`, while the choice log
  accumulates in place rather than being reset.
- [ ] Handle a consumer with a marker but no progress document — an adoption
  predating this plan. Create the file with the choices that can be recovered
  from the marker, and record the rest as unknown rather than guessed.
- [ ] Amend step 7 (line 170) so the advanced marker and the extended progress
  document are committed together.

### Task 5: Summarize the adoption into the consumer's IWE graph

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`.agents/plugins/agentdev/skills/template-consume/SKILL.md`.

- [ ] Add a step to the guide's `### Onboard the consumer's project memory`
  section writing a thin summary into the consumer's graph at the end of the
  episode: adopted SHA, workflow, settled choices, and a pointer to
  `.agentdev-template-progress.md` as the live record. It must not mirror the
  checklist.
- [ ] Choose and record the summary's document key and `type`. `tracker` fits
  the schema's own description of a living document edited in place, but
  `[schemas.tracker]` in `.iwe/config.toml` (line 110) matches only
  `data/product` and `data/milestone`, so adopting it means adding a third match
  to the seeded config. Decide between that and an existing bound type, and
  state the reason in the guide.
- [ ] Specify that update mode refreshes this summary at the end of each
  episode, and that a consumer without IWE skips the step entirely.

### Task 6: Extend the guide's own procedure

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`.

- [ ] Give Workflow A and Workflow B each an explicit task-list manifest the
  progress document is generated from, so two sessions produce the same list.
- [ ] Point the existing "Onboarding interrupted" paragraph (line 814) at the
  progress document, so a pending report names the file that holds the state
  instead of only describing what is outstanding.
- [ ] Record in `## Ongoing maintenance` that the progress document is
  consumer-owned and survives updates.

## Spec changes

[Template consumption](../spec/template-consumption.md) — contract-heavy: the
change alters what setup and update must persist, and a wrong `consumed_ref`
fails silently.

``` markdown
## MODIFIED Requirements

### Requirement: adoption is recorded for later updates

Setup SHALL write two records at the consumer root, both tracked in git.

`.agentdev-template.json` SHALL record the full commit SHA of the template
consumed, the workflow used, the optional bundles kept, and the template paths
still tracked. It SHALL remain the only machine-parsed record of the consumed
ref. Update mode SHALL diff only those paths from that SHA and SHALL NOT
advance the SHA past what was actually applied.

`.agentdev-template-progress.md` SHALL record the task list for the chosen
workflow and the choices the user made. Setup SHALL write it before executing
the guide's steps, so an interrupted session leaves a resumable record. It MAY
name the adopted SHA as context, but SHALL NOT be read as the source of truth
for it.

Neither file SHALL appear in `tracked_paths`; both are consumer-created state,
not template paths.

#### Scenario: setup is interrupted and resumed

- **WHEN** a setup session ends with tasks in `.agentdev-template-progress.md`
  still unticked
- **THEN** the next session continues from those tasks and the recorded
  choices, rather than restarting the workflow and scope interview

#### Scenario: a task is completed during consumption

- **WHEN** a consumption task is finished
- **THEN** its checkbox is ticked in the same edit that writes an indented
  `- **Evidence:**` child naming what closed it

#### Scenario: a choice constrains a later update

- **WHEN** update mode considers a changed template path the consumer's choice
  log records as customized
- **THEN** the recorded choice is applied rather than re-derived, and the path
  is merged manually rather than overwritten

## ADDED Requirements

### Requirement: adoption is summarized into a consumer's knowledge base

When the consumer kept the IWE knowledge base, setup and update SHALL write a
summary document into the consumer's graph at the end of the episode recording
the adopted SHA, the workflow, and the settled choices, and pointing at
`.agentdev-template-progress.md` as the live record. It SHALL NOT mirror the
task list. A consumer without a knowledge base SHALL skip this step, and its
absence SHALL NOT block consumption.
```

## Depends on

[Repository-owned IWE seed for consumers](20260905-consumer-iwe-seed.md) — Task
5 writes into the consumer graph that plan's seeding step creates, and Task 5's
schema decision may add a match to the `.iwe/config.toml` it ships.

## Verification

- `iwe normalize` and `iwe schema validate` both exit 0 from the repository
  root.
- `uv run pytest docs/knowledge/tests/` passes.
- The spec's modified requirement names both artifacts and states which one owns
  `consumed_ref`.
- `.agentdev-template.json` and `.agentdev-template-progress.md` each appear
  exactly once in the boundary classification.
- Reading `SKILL.md` alone, a session can state when the progress document is
  written, what generates its task list, and how update mode extends it.
- `check-updates.sh` is unchanged: no task in this plan alters marker parsing.

## Out of scope

- Changing `consumed_ref`'s format, location, or parser, or any edit to
  `check-updates.sh`.
- Making the progress document machine-parsed. It is written and read by agents;
  no script consumes it.
- A mechanical gate over the progress document's checkboxes. The plan gate in
  `docs/knowledge/tests/test_plan_checkboxes.py` is scoped to `data/plans/` and
  stays that way; the evidence convention here is a written contract only.
- Migrating existing consumers. Update mode creates a missing progress document
  as Task 4 specifies; no separate migration is shipped.
- Changing the guide's actual consumption steps. This plan records progress
  through them, it does not alter them.

## Key references

Verified anchor points (line numbers as of 2026-09-06):

- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:21` —
  `## The Marker File`
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:55` —
  `## Setup Mode`
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:63` — setup step 1,
  the workflow question
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:68` — setup step 2,
  the scope questions
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:87` — setup step 6,
  writing the marker
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:99` —
  `## Update Mode`
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:170` — update step
  7, advancing the marker
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:176` —
  `## Default Template Surface`
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:791`
  — `### Onboard the consumer's project memory`
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:814`
  — the "Onboarding interrupted" paragraph
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:893`
  — `## Ongoing maintenance`
- `docs/knowledge/data/spec/template-consumption.md:80` —
  `## Requirement: adoption is recorded for later updates`
- `docs/knowledge/data/architecture/template-boundary.md:75` —
  `## Default template surface`
- `docs/knowledge/data/architecture/template-boundary.md:156` — the
  `.github/pr-description-guidance.md` consumer-created row
- `.iwe/config.toml:110` — `[schemas.tracker]`, matching only `data/product` and
  `data/milestone`
