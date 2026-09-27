---
type: plan
created: 2026-09-27
description: Add the iwe-capture skill as the single writer of bug, feature, and task documents, enforce the SCHEMA.md body shape for bugs and features in the iwe schemas, and bring the existing documents into conformance.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-27T08:43:08Z
sources:
- resource: docs/knowledge/data/backlog/capture-skill.md
- resource: docs/knowledge/SCHEMA.md
- resource: docs/knowledge/AGENTS.md
- resource: .iwe/schemas/bug.yaml
- resource: .iwe/schemas/feature.yaml
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-plan/scripts/close-issue.sh
---

# Add the iwe-capture skill

## Context

The operating loop's Record step (`docs/knowledge/AGENTS.md`) defines three
inbox lanes — backlog tasks, bugs, and proposed features — and no skill owns
their format. Explore and Implement each carry an inline recipe for bugs, and
Implement another for tasks; nothing writes proposed features. The format
`SCHEMA.md` prescribes is enforced only for frontmatter, so the body shape has
drifted: no bug document opens with the `Bug:` H1, four bugs lack
`## Key references`, and every feature document lacks `## Edge cases`,
`## Open questions`, or both. Backlog tasks conform.

This plan closes [Write a capture skill](../backlog/capture-skill.md).

## Approach

One skill, `/agentdev:iwe-capture <bug|feature|task>`, writes all three lanes.
It is the capture counterpart of `/agentdev:iwe-plan`: Explore does the thinking
and hands a finished item to Capture, the way it hands a buildable one to Plan;
Implement hands off deferred work and defects the same way. Their inline recipes
are replaced by the handoff, so the format has one writer.

Capture is a gate, not a drafting aid. It checks for a likely duplicate first
and stops on a match; it refuses a document missing any section or field
`SCHEMA.md` requires for its type, listing every gap, rather than filing a
partial one. It files a feature at `stage: proposed` with `status: draft` and
never promotes one to `accepted` — that is Plan's step. `--from someday/<slug>`
promotes a someday idea to a backlog task and moves the hub link. An item whose
exploration began from a GitHub issue records the issue under `sources:` and
closes it with a comment naming the captured document.

`SCHEMA.md` is the contract and does not change; the documents that disagree
with it are fixed. The body rules — the bug H1 prefix and each type's required
sections in order — are encoded in `.iwe/schemas/bug.yaml` and `feature.yaml`,
so `iwe schema validate` rejects a non-conforming document however it was
written, and Capture's refusal lists the same sections the schema checks.
Sections beyond the required set stay allowed.

Issue closing reuses one implementation: the view-and-close logic in
`iwe-plan`'s `close-issue.sh` moves into the shared `bin/github-issue.sh`, and
each skill's script keeps only its own arguments and comment text. Capture
calling `iwe-plan`'s script directly was rejected because it couples one skill
to another's `--plan` contract; a second full copy was rejected as duplication.

Capture is model-invocable, unlike Plan: Implement must be able to file a
deferred task or a defect mid-run without stopping for the user.

## Implementation Steps

### Task 1: Enforce the SCHEMA.md body shape for bugs and features

**Files:** Modify: `.iwe/schemas/bug.yaml`, `.iwe/schemas/feature.yaml`

- [x] Add body rules: a bug's H1 matches `^Bug: ` and its top section contains
  `## Symptom`, `## Reproduction`, `## Root cause`, `## Fix`, and
  `## Key references` in that order; a feature's top section contains
  `## Purpose`, `## Behaviour`, `## Edge cases`, and `## Open questions` in that
  order. Additional sections stay allowed. Confirm with `iwe schema validate`
  that the rules flag exactly the non-conforming documents counted in
  `## Context`, and that the seed's example bug and features pass
  (`uv run pytest docs/knowledge/tests/test_iwe_seed.py`). Tasks 1–3 land in one
  commit: the pre-commit `iwe-schema-validate` hook fails on any tree between
  them.
  - **Evidence:** commit "Enforce the SCHEMA.md body shape for bugs and
    features"; before Tasks 2–3, `iwe schema validate` flagged all 12 bug H1s
    and all 18 feature docs and nothing else; `test_iwe_seed.py` 8 passed.

### Task 2: Bring the bug documents into conformance

**Files:** Modify: `docs/knowledge/data/bugs/*.md`

- [x] Prefix every bug H1 with `Bug: `, and add `## Key references` with
  `path:line — symbol` anchors to `fisher-install-over-untracked-plugins`,
  `plan-checkbox-over-claiming`,
  `review-orchestrator-ends-turn-while-passes-run`, and
  `validator-warning-visibility`. Anchors come from the current checkout (for a
  fixed bug, the code the fix landed in), stamped with the date. Update each
  touched document's `generated`.
  - **Evidence:** commit "Enforce the SCHEMA.md body shape for bugs and
    features"; `iwe schema validate` reports no `data/bugs/` finding.

### Task 3: Bring the feature documents into conformance

**Files:** Modify: `docs/knowledge/data/features/*.md`

- [x] Add the missing `## Edge cases` and `## Open questions` sections to every
  feature document, placed in `SCHEMA.md` order. Edge cases are derived from the
  feature's linked spec scenarios and the code it describes; an Open questions
  section with nothing open says so in one line. Existing extra sections
  (`## Scope`, `## References`, `## Resolved decisions`) stay. Update each
  touched document's `generated`. `iwe schema validate` is clean after this
  task.
  - **Evidence:** commit "Enforce the SCHEMA.md body shape for bugs and
    features"; `iwe normalize && iwe schema validate` exit 0.

### Task 4: Share the issue-closing logic

**Files:** Modify: `.agents/plugins/agentdev/bin/github-issue.sh`,
`.agents/plugins/agentdev/skills/iwe-plan/scripts/close-issue.sh`

- [x] Move the view-state, already-closed, and close-with-comment steps out of
  `close-issue.sh` into a function in `bin/github-issue.sh`, keeping the
  script's output lines and result codes unchanged.
  `uv run pytest .agents/plugins/agentdev/tests/test_close_issue.py` passes
  unmodified.
  - **Evidence:** commit "Share the issue-closing steps in github-issue.sh";
    `test_close_issue.py` 3 passed unmodified; `shellcheck -x` clean on both
    files.

### Task 5: Write the iwe-capture skill

**Files:** Create: `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md`

- [x] Write the skill per `/agentdev:create-skill`: the three types and the
  `--from someday/<slug>` promotion; the duplicate check with `iwe find --fuzzy`
  and `--lexical`; the completeness gate reading each type's required
  frontmatter and sections from `SCHEMA.md`; writing at `data/<lane>/<slug>`
  with `stage`/`status` derived from the `SCHEMA.md` table, `generated`, and
  `sources`; the hub link (a backlog task under its priority section of
  `data/backlog.md`, bugs and features appended to `data/bugs.md` and
  `data/features.md`); `iwe normalize` and `iwe schema validate`; and issue
  closing through the Task 6 script with a RESULT table mirroring `iwe-plan`'s
  `## Closing the issue`.
  - **Evidence:** commit "Add the iwe-capture skill";
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reports 55/55 skills valid, 0 errors, 0 warnings.

### Task 6: Bundle the capture issue-closing script with its test

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-capture/scripts/close-issue.sh`,
`.agents/plugins/agentdev/skills/iwe-capture/scripts/__common.sh`,
`.agents/plugins/agentdev/tests/test_capture_close_issue.py`

- [x] Add `close-issue.sh --issue <ref> --doc <path> [--comment <text>]` built
  on the Task 4 function, following `/agentdev:skill-scripts`, whose default
  comment names the captured document. Tests cover `SUCCESS`, `ALREADY_CLOSED`,
  `ISSUE_NOT_FOUND`, `GH_UNAVAILABLE`, a missing document (`PREFLIGHT_ERROR`),
  and `--help`. `shellcheck -x` is clean.
  - **Evidence:** commit "Bundle the iwe-capture issue-closing script";
    `uv run pytest .agents/plugins/agentdev/tests` 70 passed, including 6 in
    `test_capture_close_issue.py`; `shellcheck -x` clean.

### Task 7: Route Explore and Implement through iwe-capture

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-implement/SKILL.md`

- [x] Replace Explore's inline bug recipe in `## Capturing` with a handoff to
  `/agentdev:iwe-capture` for bugs, features, and tasks, carrying `ISSUE_URL`
  when the exploration started from an issue. Replace Implement's inline bug and
  backlog recipes in `## Capturing what implementation turns up` with the same
  handoff; a defect that cannot meet the bug bar stays in the handoff report.
  - **Evidence:** commit "Route Explore and Implement captures through
    iwe-capture"; `grep -n 'data/bugs/<slug>\|data/backlog/<slug>'` over both
    skills finds nothing; `validate_agent_files` 55/55 valid.

### Task 8: Document the skill in the workspace and catalog references

**Files:** Modify: `docs/knowledge/AGENTS.md`, `docs/knowledge/STRUCTURE.md`,
`.agents/plugins/agentdev/README.md`,
`docs/knowledge/data/features/agentdev-iwe-workflow-skills.md`,
`docs/knowledge/data/someday.md`

- [x] Route the Record step's actionable-item, bug-found, and idea-promotion
  bullets to `/agentdev:iwe-capture`, and add a proposed-feature bullet; add the
  skill to the workspace skills table, STRUCTURE's skill list, and the plugin
  README's knowledge-graph workflow table; name the skill in the IWE workflow
  skills feature doc; point the someday hub's promotion note at `--from`.
  - **Evidence:** commit "Document iwe-capture in the workspace and catalog
    references"; `iwe schema validate` exit 0; `validate_agent_files` 55/55
    valid.

### Task 9: Release the catalog version

**Files:** Modify: `.agents/plugins/agentdev/.claude-plugin/plugin.json`,
`.agents/plugins/agentdev/.codex-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `docker/desktop/agent-desktop.Dockerfile`

- [x] Bump the four aligned pins from `3.3.0` to `3.4.0` — a new skill is a
  minor release.
  - **Evidence:** commit "Release agentdev 3.4.0"; no `3.3.0` pin remains in the
    four files; `validate_agent_files` 55/55 valid.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) gains the Capture contract
and the enforced document shape:

``` markdown
## ADDED Requirements

### Requirement: Capture files complete inbox documents

The Capture skill SHALL be the only writer of new bug, proposed-feature, and
backlog-task documents, SHALL refuse a document missing any frontmatter field
or body section `SCHEMA.md` requires for its type, SHALL check the graph for a
likely duplicate before filing, SHALL file a feature at `stage: proposed` and
never promote it, and SHALL link every filed document from its hub and end
with `iwe normalize` and `iwe schema validate` passing.

#### Scenario: A complete item is captured

- **WHEN** Capture is invoked for a bug, feature, or task whose required
  sections and fields are all supplied, and no likely duplicate exists
- **THEN** Capture writes the document at its lane's key with the `stage` and
  `status` `SCHEMA.md` derives for it, stamps `generated` and `sources`, links
  it from its hub — a task under its priority section — and validates the
  graph

#### Scenario: A required section is missing

- **WHEN** the supplied content lacks any section or field required for its
  type
- **THEN** Capture writes nothing and lists every missing section and field

#### Scenario: A likely duplicate exists

- **WHEN** a fuzzy or lexical search finds an existing document that matches
  the item
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
- **THEN** it hands the item to Capture rather than writing the document
  itself

### Requirement: Bug and feature documents keep the SCHEMA.md shape

The bug and feature schemas SHALL require the body shape `SCHEMA.md`
prescribes — a bug's `Bug:` H1 and its Symptom, Reproduction, Root cause, Fix,
and Key references sections; a feature's Purpose, Behaviour, Edge cases, and
Open questions sections — in that order, while allowing additional sections.

#### Scenario: A document is written without Capture

- **WHEN** a bug or feature document lacks a required section, has them out of
  order, or a bug's H1 lacks the `Bug:` prefix
- **THEN** `iwe schema validate` fails and names the document
```

## Verification

- `iwe normalize && iwe schema validate` pass on the tree with every bug and
  feature document conforming.
- A scratch bug document missing `## Root cause` makes `iwe schema validate`
  fail; removing it restores a clean run.
- `uv run pytest docs/knowledge/tests/test_iwe_seed.py` passes.
- `uv run pytest .agents/plugins/agentdev/tests/test_close_issue.py .agents/plugins/agentdev/tests/test_capture_close_issue.py`
  passes.
- `shellcheck -x` is clean on both `close-issue.sh` scripts and
  `bin/github-issue.sh`.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes with the new skill counted.
- `grep -n 'data/bugs/<slug>\|data/backlog/<slug>'` over the Explore and
  Implement skills finds no inline recipe — each names `/agentdev:iwe-capture`.

## Out of scope

- Changing `SCHEMA.md`, or the task schema's body — tasks conform today and
  `SCHEMA.md` prescribes no task body sections.
- Body-shape enforcement for other document types.
- Capturing someday, architecture, or concept documents; Explore keeps those.
- Promoting a feature past `proposed`, which stays with Plan.

## Key references

Verified anchor points (line numbers as of 2026-09-27):

- `docs/knowledge/SCHEMA.md:98` — feature body sections
- `docs/knowledge/SCHEMA.md:102` — bug H1 `Bug:` rule
- `docs/knowledge/SCHEMA.md:111` — bug body sections
- `docs/knowledge/SCHEMA.md:131` — backlog task frontmatter
- `.iwe/schemas/bug.yaml:5` — `maxDepth`, where body rules join the frontmatter
  schema
- `.iwe/schemas/feature.yaml:5` — `maxDepth`, same
- `.iwe/config.toml:66` — schema bindings for features, bugs (69), and backlog
  (75)
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md:86` — `## Capturing`
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md:99` — inline bug recipe
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:99` — inline bug
  recipe
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:102` — inline backlog
  recipe
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:127` — `close-issue.sh`
  invocation
- `.agents/plugins/agentdev/skills/iwe-plan/scripts/close-issue.sh:110` —
  view-state and close steps to share
- `.agents/plugins/agentdev/bin/github-issue.sh:10` — `parse_issue_ref`, the
  shared issue helpers
- `.agents/plugins/agentdev/tests/test_close_issue.py:15` — `SCRIPT_PATH`
- `docs/knowledge/AGENTS.md:36` — Record step: idea, actionable item
- `docs/knowledge/AGENTS.md:49` — Record step: bug found
- `docs/knowledge/AGENTS.md:216` — workspace skills table
- `docs/knowledge/STRUCTURE.md:26` — skill list
- `.agents/plugins/agentdev/README.md:117` — knowledge-graph workflow table
- `docs/knowledge/data/someday.md:14` — promotion note
- `docs/knowledge/data/backlog.md:17` — priority sections
- `docs/knowledge/data/spec/iwe-workflow-skills.md:392` — last requirement;
  Capture requirements precede it
- `.agents/plugins/agentdev/.claude-plugin/plugin.json:3` — version
- `.agents/plugins/agentdev/.codex-plugin/plugin.json:3` — version
- `.claude-plugin/marketplace.json:13` — agentdev version
- `docker/desktop/agent-desktop.Dockerfile:18` — `AGENTDEV_PLUGIN_VERSION`
