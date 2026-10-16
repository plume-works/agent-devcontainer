---
type: plan
created: 2026-10-16
description: Every active plan declares its release impact in a schema-required release frontmatter field — internal, or the feature and bug keys it adds, changes, or fixes — so Ship applies the declaration instead of deciding, plus features and release links backfilled for shipped public-facing plans that have none.
release:
- bugs/ship-release-link-without-feature
- features/agentdev-iwe-workflow-skills
generated:
  by: claude-code/opus-5.5
  at: 2026-10-16T12:00:00Z
sources:
- resource: .iwe/schemas/plan.yaml
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
---

# Declare release impact when a plan is written

## Context

[Ship's release-link rule is undefined for a plan with no feature or
bug](../bugs/ship-release-link-without-feature.md): step 6 of the Ship rulebook
creates a feature only "if the plan requires a new feature", and no plan says
so. The fresh-context Shipper therefore ships a plan that links no feature or
bug without any release entry, or, on another model, stops for a decision.
Release pages link only feature and bug documents, so user-visible work shipped
that way is missing from `data/releases/unreleased.md` and would be missing from
the next release. Pre-1.0.0 work has the same gap on the
[1.0.0](../releases/1.0.0.md) page.

The maintainer decided that the release impact is chosen when the plan is
written and reviewed with it, that it lives in frontmatter, and that the
backfill covers every public-facing shipped plan, including those released in
1.0.0.

## Approach

A plan carries a `release` frontmatter field: either `internal`, or a list of
the `features/<slug>` and `bugs/<slug>` keys the work adds, changes, or fixes.
The plan schema requires the field while a plan is active (no `stage`), so
shipped plans that predate it stay valid untouched. Plan sets it when it files
the plan: a plan that changes behavior a workspace user or template consumer
sees, and has no feature for it, first hands the feature to Capture, which stays
the only writer of new features. Ship reads the field and applies it: one
release link per declared document, none for `internal`, and a blocker report —
never a decision of its own — when the field is missing or names a document that
does not exist. Ship no longer creates features.

A `## Release` body section was rejected: it would be a real graph link, but the
schema cannot require a body section only on active plans, so enforcement would
fall to the skills.

The backfill files features through Capture and then marks them `implemented`
directly, because their plans already shipped and Ship does not run again on a
done plan. It also sets `release` on each backfilled done plan, so the plan and
its release entry point at the same documents.

Assumptions:

- A milestone aggregator plan declares `internal`: its children carry the
  release entries.
- The feature slugs in Tasks 8 and 9 are provisional. When Capture's duplicate
  check matches an existing feature, that plan links the existing feature —
  under `## Changed` if it was released earlier — and the substitution is
  recorded under `## Verification results`.

## Implementation Steps

### Task 1: The plan schema requires `release` on active plans

**Files:** Modify: `.iwe/schemas/plan.yaml`; Create:
`docs/knowledge/tests/test_plan_release_schema.py`

- [x] Write a failing pytest, in the style of `test_body_shape_schemas.py`, that
  copies the graph into `./.tmp/` and asserts `iwe schema validate`: rejects an
  active plan without `release` and names the field; rejects an active plan
  whose `release` is any other string or names a key outside `features/` or
  `bugs/`; accepts `release: internal`; accepts a non-empty list of
  `features/<slug>` and `bugs/<slug>` keys; accepts a `stage: done` plan without
  `release`.
  - **Evidence:** `docs/knowledge/tests/test_plan_release_schema.py` in the Task
    1 commit; against the unchanged schema its five rejection cases failed.
- [x] Add the `release` property — `internal` or a non-empty list of keys
  matching `^(features|bugs)/[a-z0-9][a-z0-9.-]*$`, which admits the seed's
  `.example` keys — with a description naming both forms, and require it when
  `stage` is absent, alongside the existing `stage: done` → `completed` rule.
  The new test passes.
  - **Evidence:** `.iwe/schemas/plan.yaml` in the Task 1 commit;
    `uv run pytest docs/knowledge/tests/test_plan_release_schema.py` — 9 passed;
    `test_iwe_seed.py` and `test_body_shape_schemas.py` — 14 passed.

### Task 2: SCHEMA.md documents the field

**Files:** Modify: `docs/knowledge/SCHEMA.md`

- [x] Add `release` to the plan frontmatter example and state, in one or two
  sentences, its two forms, that it is required while the plan is active, and
  that Ship takes the plan's release entries from it.
  - **Evidence:** `docs/knowledge/SCHEMA.md` `## Plans` in the Task 2 commit.

### Task 3: Every plan the schema validates declares `release`

**Files:** Modify: each active plan under `docs/knowledge/data/plans/`,
`templates/iwe/data/plans/20260720-streak-widget.example.md`,
`templates/iwe/data/plans/mvp.example.md`, the active fixture plans under
`scripts/e2e/20261007-agent-owned-ship-implement/fixtures/plans/`

- [x] Give every plan active at implementation time a `release` value by the
  rule Plan applies (Task 4). A public-facing plan with no feature gets one
  filed through `/agentdev:iwe-capture feature` and set to `stage: accepted`.
  - **Evidence:** the Task 3 commit declares `features/ai-responder-workflows`
    on `20260909-resumable-claude-review-sessions` and files
    `features/macos-native-bootstrap`, `features/shared-buildkit-builder`, and
    `features/vscode-expo-bridge` at `accepted` for the other three active
    plans; `iwe schema validate` passes.
- [x] Give the two active seed example plans a `release` value; the streak
  widget links the seed's matching feature when one exists, and the milestone
  declares `internal`. `uv run pytest docs/knowledge/tests/test_iwe_seed.py`
  passes.
  - **Evidence:** the Task 3 commit sets `features/streak-widget.example` and
    `internal`; `uv run pytest docs/knowledge/tests/test_iwe_seed.py` — 8
    passed.
- [x] Give the e2e fixture plans `release: internal`.
  - **Evidence:** the Task 3 commit sets it on all three fixture plans.

### Task 4: Plan declares the release impact when it files a plan

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-capture/SKILL.md`

- [x] Step 4's frontmatter block shows `release`, followed by the rule: list the
  feature and bug documents the work adds, changes, or fixes; `internal` only
  when no workspace user or template consumer sees a difference — refactors,
  tooling only this repository runs, project-memory-only edits, spikes, and
  milestone aggregators. `## Context` links each listed document.
  - **Evidence:** `iwe-plan/SKILL.md` step 4 in the Task 4 commit;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    — 62/62 skills valid.
- [x] Step 5: before filing, a public-facing plan with no feature hands the
  feature to `/agentdev:iwe-capture feature`, then records its key and sets it
  to `stage: accepted`. Revise mode keeps `release` in step with a change of
  intent.
  - **Evidence:** `iwe-plan/SKILL.md` step 5 and the revise-mode paragraph of
    step 4 in the Task 4 commit; the validator run above.
- [x] Capture's description names Plan among the skills that hand it a feature.
  - **Evidence:** `iwe-capture/SKILL.md` description in the Task 4 commit; the
    validator run above.

### Task 5: Ship applies the declaration and never creates a feature

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`

- [x] Step 1 reads `release` and every document it lists. A missing field, or a
  listed document that does not exist, ends the run with a Ship blocker report
  routed to Plan revise mode, before Verify and with no mutation. Cancellation
  does not read the field.
  - **Evidence:** `iwe-shipper.agent.md` step 1 and the blocker-report routes in
    the Task 5 commit;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    — 0 errors.
- [x] Step 6 sets each listed feature to `implemented` and each listed bug to
  `done`, and adds one unreleased link per listed document by the existing Added
  / Changed / Fixed rule. `internal` adds no release entry. The "if the plan
  requires a new feature … create it" clause is removed.
  - **Evidence:** `iwe-shipper.agent.md` step 6 in the Task 5 commit; the
    validator run above.

### Task 6: The e2e harness proves the `internal` path

**Files:** Modify: `scripts/e2e/20261007-agent-owned-ship-implement/run.sh`

- [x] After the approved ship, assert on each harness that the hello plan is
  `stage: done` and that `data/releases/unreleased.md` is unchanged.
  - **Evidence:** `plan_done` and `unreleased_unchanged` checks after each
    harness's approved ship in the Task 6 commit; `shellcheck` passes. Task 7
    runs them.

### Task 7: Run the e2e harness

- [ ] `scripts/e2e/20261007-agent-owned-ship-implement/run.sh --harness claude`
  prints no FAIL.
- [ ] The same run with `--harness opencode --opencode-model <maintainer model>`
  prints no FAIL — the harness whose model stops Ship on the undefined
  release-link rule.

### Task 8: Backfill features for public-facing work shipped since 1.0.0

**Files:** Create: one `docs/knowledge/data/features/<slug>.md` per row; Modify:
`docs/knowledge/data/features.md`, `docs/knowledge/data/releases/unreleased.md`,
each listed plan, `docs/knowledge/data/log.md`

For each row: file the feature through `/agentdev:iwe-capture feature` from the
plan's Context and its synced spec, set it to `stage: implemented`, link it
under `## Added` in `releases/unreleased.md`, set the plan's `release` to the
feature key, link the plan from the feature, and add one log bullet.

- [ ] `plans/20261013-docker-storage-gc` → `features/docker-storage-limits`
- [ ] `plans/20261012-update-branch-pulls-upstream` →
  `features/update-branch-pulls-upstream`
- [ ] `plans/20261011-coder-claude-remote-control` →
  `features/coder-remote-control-autostart`
- [ ] `plans/20261009-remove-coder-agent-auth-seeding` →
  `features/agent-sign-in-without-seeding`
- [ ] `plans/20261005-codex-full-access-config` →
  `features/codex-full-access-config`
- [ ] `plans/20261002-pr-feedback-resolve-merge-conflicts` →
  `features/pr-feedback-resolves-merge-conflicts`
- [ ] `plans/20260925-bun-for-node-tooling` →
  `features/bun-only-javascript-runner`

### Task 9: Backfill the pre-1.0.0 feature onto the 1.0.0 page

**Files:** Create: `docs/knowledge/data/features/xpra-port-forwarding.md`;
Modify: `docs/knowledge/data/features.md`,
`docs/knowledge/data/releases/1.0.0.md`,
`docs/knowledge/data/plans/20260905-xpra-vscode-port-forwarding.md`,
`docs/knowledge/data/log.md`

- [ ] `plans/20260905-xpra-vscode-port-forwarding` →
  `features/xpra-port-forwarding`, filed and marked as in Task 8, linked under
  `## Added` on the 1.0.0 page rather than the unreleased one.

### Task 10: Declare existing features on shipped plans that never linked them

**Files:** Modify: the plans listed below

Each feature is already on its release page; only the plan's `release` and a
plan link from the feature are missing.

- [ ] `plans/20261005-pr-review-scenario-validation` and
  `plans/20261007-agent-owned-ship-implement` declare
  `features/ai-responder-workflows` and `features/agentdev-iwe-workflow-skills`
  respectively, both already under `## Changed` in `releases/unreleased.md`.
- [ ] `plans/20260902-audit-plan-edits-in-fresh-context` →
  `features/agentdev-iwe-workflow-skills`;
  `plans/20260903-pr-description-guidance` → `features/pr-description-guidance`;
  `plans/20260817-preserve-approved-wording` →
  `features/preserved-approved-wording`;
  `plans/20260817-no-logbooks-in-the-graph` → `features/no-working-logbooks`;
  `plans/20260816-structured-plan-spec-deltas` →
  `features/risk-scaled-spec-deltas`; `plans/20260814-drop-venv-symlink` →
  `features/uv-run-only-environment`.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — new requirement; the
plan schema and Ship's release behavior change, so this is a structured delta:

``` markdown
## ADDED Requirements

### Requirement: Plans declare their release impact

The plan schema SHALL require every active plan to carry a `release`
frontmatter value: `internal`, or a non-empty list of the `features/` and
`bugs/` keys the work adds, changes, or fixes. The Plan skill SHALL set that
value when it files a plan, SHALL declare `internal` only when no workspace user
or template consumer sees a difference, and SHALL have Capture file a missing
feature before it files the plan. Ship SHALL take a plan's release entries only
from that value and SHALL never create a feature.

#### Scenario: A plan introduces user-visible behavior with no feature

- **WHEN** Plan files a plan whose work changes what a workspace user or
  template consumer sees, and no feature describes it
- **THEN** Plan hands the feature to Capture, lists its key in `release`, and
  sets the feature to `stage: accepted`

#### Scenario: A plan changes nothing users see

- **WHEN** Ship ships a plan that declares `release: internal`
- **THEN** Ship marks the plan done and adds no release entry

#### Scenario: A plan declares features and bugs

- **WHEN** Ship ships a plan whose `release` lists feature and bug keys
- **THEN** Ship marks each feature implemented and each bug done, and adds one
  unreleased inclusion link per listed document — a feature new in this version
  under Added, a feature released in an earlier version under Changed, a bug
  under Fixed

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
```

## Verification

- `uv run pytest docs/knowledge/tests/test_plan_release_schema.py docs/knowledge/tests/test_iwe_seed.py docs/knowledge/tests/test_body_shape_schemas.py`
  passes.
- `iwe normalize` then `iwe schema validate`, from the repository root, pass.
- `uv run validate-agent-files` passes on the changed skill and agent files.
- Task 7's e2e runs print no FAIL.
- `releases/unreleased.md` lists each Task 8 feature once under `## Added`, and
  `releases/1.0.0.md` lists `features/xpra-port-forwarding` once under
  `## Added`.
- Listing done plans that link no `features/` or `bugs/` document and declare no
  `release` finds only internal work:
  `plans/20260929-pr-review-scenario-bar-spike` and the plans that never changed
  what users see.

## Out of scope

- Declaring `release` on shipped plans outside Tasks 8–10; the schema leaves
  them valid.
- Verify cross-checking `release: internal` against a non-empty
  `## Spec changes`.
- What happens to an `accepted` feature when its plan is cancelled.
- Migrating a template consumer's active plans; the template-consume update flow
  already shows schema failures and leaves migration to the consumer.
- Plans on unmerged branches; the knowledge-base validation on their pull
  requests reports the missing field once this lands on main.

## Key references

Verified anchor points (line numbers as of 2026-10-16):

- `.iwe/schemas/plan.yaml:12` — `stage` property
- `.iwe/schemas/plan.yaml:93` — `if` / `then` requiring `completed` on a done
  plan
- `docs/knowledge/SCHEMA.md:68` — `## Plans` frontmatter and body
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:46` — step 4, write
  planning state
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:105` — step 5, file a
  created plan; proposed feature set to `accepted`
- `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md:3` — description naming
  Capture's callers
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:54` — step 1, read the
  linked feature or bug
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:115` — step 6,
  new-feature clause
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:119` — step 6, one
  unreleased link per work
- `docs/knowledge/tests/test_body_shape_schemas.py:100` —
  `test_unmodified_graph_validates`, the graph-copy fixture pattern
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh:233` —
  `claude ship approved: publish ran`
- `templates/iwe/data/plans/20260720-streak-widget.example.md:1` — active seed
  plan frontmatter
- `templates/iwe/data/plans/mvp.example.md:1` — milestone seed plan frontmatter
