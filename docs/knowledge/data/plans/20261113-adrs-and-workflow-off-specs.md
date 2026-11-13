---
type: plan
created: 2026-11-13
release: internal
description: Add ADRs to the graph and change Plan, Verify, Ship, and the release cut so that no workflow skill reads or writes a spec.
sources:
- resource: https://github.com/mattpocock/skills/blob/main/skills/engineering/domain-modeling/ADR-FORMAT.md
- resource: docs/spec-audit/requirements.jsonl
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md
- resource: scripts/check-ship-records.py
---

# Add ADRs and take the workflow off specs

## Context

The repository owner decided that code and tests are the only statement of
behaviour, that an ADR registry holds the reasons, and that a glossary holds the
project terms: [Shrink the knowledge base to an issue tracker and decision
records](../backlog/shrink-knowledge-base-to-issues-and-adrs.md). [The spec
usefulness audit](../findings/spec-usefulness-audit.md) is the evidence.

The workflow skills write specs today. Plan writes `## Spec changes`, Ship
merges it into `data/spec/`, and the release cut reads the spec diff. This plan
changes those skills first, so that the later work on `data/spec/` runs without
them.

The repository owner's decisions:

- An ADR is a document in the graph at `data/adr/NNNN-<slug>.md`. Code comments
  cite it as `ADR-NNNN`.
- An ADR has the simplest format: a short title and 1 to 3 sentences that give
  the context, the decision, and the reason. `## Considered Options` and
  `## Consequences` are optional. The format and the rules for when to write an
  ADR come from the `ADR-FORMAT.md` of the `mattpocock/skills` repository. The
  MADR template was rejected as too formal.
- `stage` is the lifecycle key: `proposed`, `accepted`, `rejected`,
  `deprecated`, or `superseded`.
- An accepted ADR is never edited. A new ADR supersedes it, and the superseded
  ADR goes to the archive.
- Plan files an ADR at `stage: proposed`. Ship sets it to `accepted`. The ADR of
  a cancelled plan becomes `rejected`.
- A plan holds its acceptance scenarios in `## Acceptance`. Each scenario names
  the test that proves it. Ship copies nothing.
- The release cut reads the archived plans, the closed bugs, and the ADRs.
- The seed for a new repository and `/agentdev:iwe-setup` change in this plan.
- Spec text that this plan makes false is removed. The new behaviour gets no
  spec text.
- This plan is a task list only. It has no `## Spec changes`. No plan review, no
  Verify, and no Ship run on it. The pull request review is the check.

## Approach

**The ADR type.** A new schema, `adr`, binds `data/adr/**` and
`data/archive/*/adr/**`. The hub `data/adr.md` lists each ADR at `proposed` or
`accepted`. An ADR at `rejected`, `deprecated`, or `superseded` is in
`data/archive/next-release/adr/` until a release cut moves it. An ADR that
replaces an earlier ADR names it in a `supersedes` frontmatter list.

**The plan.** `## Acceptance` replaces `## Spec changes`. `## ADRs` links each
ADR that the plan proposes. A design decision and its rejected options go in the
ADR. `## Approach` keeps the shape of the solution.

**Verify.** The verifier judges the code against `## Acceptance`. A scenario
that names a test passes when that test runs the behaviour and passes. A
scenario that no test can reach names what the verifier reads, and the verifier
reads it.

**Ship.** The spec merge is removed. Ship accepts the ADRs of the plan and
archives each ADR that they supersede.

**The release cut.** The cut reads `data/archive/next-release/`. It writes the
changes from the `## Acceptance` scenarios of the archived plans, the fixed bugs
from the archived bugs, and the decisions from the ADRs that were accepted or
superseded after the last cut.

**The writer of an ADR.** Plan is the only writer. Explore gives a decision to
Plan in the handoff. Implement gets a decision into the plan by a plan revision.

**This plan's own ADRs.** The current skills cannot accept an ADR. Task 2 writes
ADR 0001 and ADR 0002 at `stage: accepted`, because the repository owner made
both decisions before this plan.

## Implementation Steps

### Task 1: Add the `adr` type

**Files:** Create: `.iwe/schemas/adr.yaml`, `docs/knowledge/data/adr.md`,
`docs/knowledge/tests/test_adr_schema.py`; Modify: `.iwe/config.toml`,
`docs/knowledge/SCHEMA.md`, `docs/knowledge/data/index.md`,
`scripts/check-ship-records.py`, `scripts/tests/test_check_ship_records.py`

- [x] `.iwe/schemas/adr.yaml` requires the frontmatter `type: adr`, `stage`, and
  `description`. It has no date field: git holds the date.
  - **Evidence:** Wrote `.iwe/schemas/adr.yaml` with
    `required: [type, stage, description]` and no date field;
    `test_adr_schema.py` passes.
- [x] The schema permits only these values of `stage`: `proposed`, `accepted`,
  `rejected`, `deprecated`, `superseded`.
  - **Evidence:** The `stage` enum is
    `proposed, accepted, rejected, deprecated, superseded`;
    `test_unknown_stage_is_rejected` passes.
- [x] The schema permits the optional frontmatter `supersedes`, a list of
  `adr/NNNN-<slug>` keys.
  - **Evidence:** Added an optional `supersedes` array whose items match
    `^adr/[0-9]{4}-<slug>$`.
- [x] The schema requires one H1, the short title of the decision.
  - **Evidence:** The top section rule has `minContains: 1` and
    `maxContains: 1`.
- [x] The schema permits only these sections below that text, each optional:
  `## Considered Options` and `## Consequences`.
  - **Evidence:** The H1 permits only optional `Considered Options` and
    `Consequences`, with `additionalSections: false`;
    `test_unknown_section_is_rejected` passes.
- [x] `.iwe/config.toml` binds the `adr` schema to `data/adr/**` and
  `data/archive/*/adr/**`.
  - **Evidence:** Added `[schemas.adr]` with both globs; `iwe schema validate`
    passes.
- [x] `.iwe/config.toml#schemas.hub` matches `data/adr`.
  - **Evidence:** Added `data/adr` to `[schemas.hub]`.
- [x] `docs/knowledge/data/adr.md` is a hub with no member.
  - **Evidence:** Created the hub with `type: hub` and no inclusion link;
    `iwe schema validate` passes.
- [x] `docs/knowledge/data/index.md#reference` links the ADR hub.
  - **Evidence:** Added the `ADRs` bullet first under `# Reference`.
- [x] `docs/knowledge/SCHEMA.md` has a section for ADRs. It gives the file name,
  the frontmatter, the format (a short title, then 1 to 3 sentences that give
  the context, the decision, and the reason), the stages, the rule that an
  accepted ADR is never edited, and the `ADR-NNNN` form for a code comment.
  - **Evidence:** Added `## ADRs — data/adr/NNNN-<slug>.md` with the file name,
    frontmatter, format, stages, the never-edited rule, and `ADR-NNNN`.
- [x] That section says that the value of an ADR is the record that a decision
  was made and why, and that an optional section is written only when it adds
  value.
  - **Evidence:** The section says "The value of an ADR is the record that a
    decision was made and why" and to write an optional section only when it
    adds value.
- [x] `docs/knowledge/SCHEMA.md` names `adr/` as an archive folder.
  - **Evidence:** The archive section lists `adr/` with the other folders.
- [x] `docs/knowledge/tests/test_adr_schema.py` runs `iwe schema validate` on a
  fixture workspace. An ADR of one paragraph passes. An ADR with an unknown
  section fails. An ADR with an unknown stage fails.
  - **Evidence:** `uv run pytest docs/knowledge/tests/test_adr_schema.py`: 4
    passed.
- [x] `scripts/check-ship-records.py` reports an ADR at `proposed` or `accepted`
  that is in `data/archive/`.
  - **Evidence:** `check_placement` treats an ADR as live only at `proposed` or
    `accepted`; the `ship-records` hook now also matches `data/adr/`.
- [x] `scripts/check-ship-records.py` reports an ADR at `rejected`,
  `deprecated`, or `superseded` that is outside `data/archive/`.
  - **Evidence:** The same `check_placement` branch reports a closed ADR outside
    `data/archive/`.
- [x] `scripts/tests/test_check_ship_records.py` runs the script on both cases.
  - **Evidence:** `test_adr_placement_follows_its_stage` covers each stage on
    both sides; `uv run pytest scripts/tests/test_check_ship_records.py`: 46
    passed.

### Task 2: Write the first two ADRs

**Files:** Create:
`docs/knowledge/data/adr/0001-code-and-tests-state-behaviour.md`,
`docs/knowledge/data/adr/0002-decisions-are-adrs-in-the-graph.md`; Modify:
`docs/knowledge/data/adr.md`

- [x] `docs/knowledge/data/adr/0001-code-and-tests-state-behaviour.md` holds
  this text:

  ``` markdown
  ---
  type: adr
  stage: accepted
  description: Code and tests are the only statement of how the product behaves; ADRs hold the reasons and the glossary holds the terms.
  ---

  # Code and tests are the only statement of behaviour

  `data/spec/` states the behaviour of the repository a second time in prose,
  and [the spec usefulness audit](../findings/spec-usefulness-audit.md) found
  that 207 of its 264 requirements repeat a test, a rulebook, or plain code,
  and that 34 are not fully true. Code and tests are the only statement of
  behaviour, ADRs hold the reasons, and the glossary holds the terms, because a
  statement that no test runs moves away from the code.

  ## Considered Options

  - Keep the specs and merge each change into them at ship. Rejected: the merge
    is a careful reading, and nothing fails when it is wrong.
  - Keep a spec only for behaviour that no test can reach. Rejected: the
    rulebook is that text already.

  ## Consequences

  - The behaviour of a rulebook has no test. A plan states it as acceptance
    scenarios, Verify checks them one time at ship, and then they stay only in
    the archived plan.
  - `data/spec/` gets no new text.
  ```

  - **Evidence:** Wrote the fenced text with its list indent removed;
    `iwe normalize` moved only line breaks, and the text is the same word for
    word.

- [x] `docs/knowledge/data/adr/0002-decisions-are-adrs-in-the-graph.md` holds
  this text:

  ``` markdown
  ---
  type: adr
  stage: accepted
  description: Each decision is one short ADR in data/adr/, proposed by Plan, accepted by Ship, and never edited after that.
  ---

  # Each decision is a short ADR in the graph

  A decision and its rejected options were entries in the `## Rationale` of a
  spec, edited in place, and the code contradicts 4 of the 189 entries. Each
  decision is one short document at `data/adr/NNNN-<slug>.md` that Plan
  proposes and Ship accepts. An accepted ADR is never edited: a new ADR
  supersedes it, so that a reader sees each decision as it was made.

  ## Considered Options

  - A folder outside the graph. Rejected: `iwe` checks no link and no stage
    there.
  - The MADR template. Rejected: its sections fill with text that says nothing.
  ```

  - **Evidence:** Wrote the fenced text with its list indent removed;
    `iwe normalize` moved only line breaks, and the text is the same word for
    word.

- [x] `docs/knowledge/data/adr.md` links both ADRs in sorted order.

  - **Evidence:** Added two inclusion links, 0001 then 0002;
    `iwe schema validate` passes.

### Task 3: Change the plan shape

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`.agents/plugins/agentdev/skills/iwe-plan-review/references/plan-rules.md`

- [x] The section list in step 4 of the `iwe-planner` rulebook has
  `## Acceptance` and `## ADRs`, and no `## Spec changes`.

  - **Evidence:** Step 4 lists `## Acceptance` and `## ADRs` where
    `## Spec changes` was; `grep -n "Spec changes"` on the rulebook finds
    nothing.

- [x] The rulebook defines `## Acceptance`: one `### Scenario:` block for each
  behaviour that the plan adds, changes, or removes, with a `- **WHEN**` line
  and a `- **THEN**` line.

  - **Evidence:** Added `## Acceptance`: one `### Scenario:` block per
    behaviour, with `- **WHEN**` and `- **THEN**` lines, and an example.

- [x] The rulebook says that each scenario ends with one of two lines.
  `- **Test:**` names the test as `path::test_name`. `- **Checked at ship:**`
  names the rulebook or the file that the verifier reads, for behaviour that no
  test can reach.

  - **Evidence:** `## Acceptance` gives the `- **Test:**` line as
    `path::test_name` and the `- **Checked at ship:**` line.

- [x] The rulebook says that a plan with no change in behaviour writes
  `None — no behavioral change` under `## Acceptance`.

  - **Evidence:** `## Acceptance` says to write `None — no behavioral change`.

- [x] The rulebook defines `## ADRs`: one link for each ADR that the plan
  proposes. A plan that proposes none omits the section.

  - **Evidence:** Step 4 and the `## ADRs` section give one link per proposed
    ADR, and omit the section when there is none.

- [x] The rulebook holds this text on when a plan proposes an ADR:

  ``` markdown
  Propose an ADR only when all three of these are true:

  1. **Hard to reverse.** The cost of a change of mind later is meaningful.
  2. **Surprising without context.** A future reader will look at the code and
     ask why it is done this way.
  3. **The result of a real trade-off.** There were genuine alternatives, and
     one was picked for specific reasons.

  A decision that is easy to reverse, that is not surprising, or that had no
  real alternative gets no ADR.

  What qualifies:

  - **Architectural shape.**
  - **Integration patterns between parts of the system.**
  - **Technology choices that carry lock-in.** Not every library: only the ones
    that would be expensive to swap out.
  - **Boundary and scope decisions.** The explicit no-s are as valuable as the
    yes-s.
  - **Deliberate deviations from the obvious path.** Anything where a
    reasonable reader would assume the opposite.
  - **Constraints not visible in the code.**
  - **Rejected alternatives when the rejection is non-obvious.**
  ```

  - **Evidence:** The fenced text is in `## ADRs` byte for byte; a Python `in`
    check against the plan fence prints `True`.

- [x] Step 4 tells Plan to file each ADR at `data/adr/<NNNN>-<slug>.md` with
  `stage: proposed`, the next free number in `data/adr/` and
  `data/archive/*/adr/`, and a link in `data/adr.md`.

  - **Evidence:** Step 4 files each ADR at `data/adr/<NNNN>-<slug>.md` with
    `stage: proposed`, the next free number in both folders, and a link in
    `data/adr.md`.

- [x] The rulebook says that the rejected options go in the ADR, only when they
  are worth remembering, and that `## Approach` gives the shape of the solution.

  - **Evidence:** Step 4 `## Approach` and `## ADRs` put the rejected options in
    the ADR only when worth remembering.

- [x] The rulebook says that Plan never edits an accepted ADR, and that a plan
  which changes a decision proposes a new ADR that names the earlier ADR in
  `supersedes`.

  - **Evidence:** The `## ADRs` section ends with the rule and the `supersedes`
    list.

- [x] The rulebook has no section `## The three forms of ## Spec changes` and no
  rule that names `## Spec changes`, a spec, or `## Rationale`.

  - **Evidence:** Removed the section and the three `## Spec changes` rules;
    `grep -n -i "spec\b\|specs\|rationale"` on the rulebook finds nothing.

- [x] The text about `release` in step 4 says that the release cut writes the
  page from the archive.

  - **Evidence:** Step 4 says "the release cut writes the page from the
    archive".

- [x] `plan-rules.md` has a section `## Acceptance` with one rule: each scenario
  has a `**WHEN**` line, a `**THEN**` line, and a `**Test:**` line or a
  `**Checked at ship:**` line.

  - **Evidence:** Added `## Acceptance` with the one rule "Each scenario is
    complete".

- [x] `plan-rules.md` has a rule that each ADR in `## ADRs` exists at
  `stage: proposed`.

  - **Evidence:** Added `## ADRs` with the rule "Each linked ADR is proposed".

### Task 4: Verify against `## Acceptance`

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-verifier.agent.md`,
`.agents/plugins/agentdev/skills/iwe-verify/SKILL.md`

- [ ] Step 2 of the `iwe-verifier` rulebook reads the plan, its ADRs, and its
  linked feature and bug documents. It reads no spec.
- [ ] The Completeness check judges each scenario in `## Acceptance`. A scenario
  with a `**Test:**` line whose test does not exist, does not run the behaviour,
  or fails is a CRITICAL.
- [ ] A scenario with a `**Checked at ship:**` line is judged from the named
  rulebook or file. A scenario that the file contradicts is a CRITICAL.
- [ ] A plan with no `## Acceptance` section is a CRITICAL, and its route is
  `/agentdev:iwe-plan` revise mode.
- [ ] `None — no behavioral change` is judged as today: the verifier confirms
  that no behaviour changed.
- [ ] The rulebook has no "effective contract", no delta form, and no
  `### Requirement:`.
- [ ] Audit mode has no check of specs against the code.
- [ ] The descriptions of the `iwe-verifier` agent and of `/agentdev:iwe-verify`
  name acceptance scenarios, not spec requirements.

### Task 5: Ship accepts ADRs and merges no spec

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`,
`.agents/plugins/agentdev/skills/iwe-ship/SKILL.md`

- [ ] The `iwe-shipper` rulebook has no spec merge and no check of a spec merge.
- [ ] Normal shipping sets each ADR that the plan's `## ADRs` links to
  `stage: accepted`.
- [ ] For each key in the `supersedes` list of such an ADR, Ship sets that ADR
  to `stage: superseded`, moves it with `iwe rename` to
  `data/archive/next-release/adr/`, and removes its link from `data/adr.md`.
- [ ] Ship changes nothing else in an ADR.
- [ ] Cancellation sets each proposed ADR of the plan to `stage: rejected`,
  moves it to `data/archive/next-release/adr/`, and removes its hub link.
- [ ] A linked ADR that does not exist, or that is not at `proposed` before the
  ship, ends the run with a Ship blocker report. The route is
  `/agentdev:iwe-plan` revise mode.
- [ ] Ship writes no `## Rationale`. The root cause of a bug stays in the bug.
- [ ] The Ship blocker report and the rules name no spec.
- [ ] The descriptions of the `iwe-shipper` agent and of `/agentdev:iwe-ship`
  name the ADR step, not a spec merge.

### Task 6: Review a ship against the new obligations

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md`,
`scripts/check-ship-records.py`, `scripts/tests/test_check_ship_records.py`

- [ ] Plan mode of `iwe-ship-reviewer` checks that `## Acceptance` is
  `None — no behavioral change` or holds only complete scenarios.

- [ ] Plan mode checks that each ADR in `## ADRs` exists at `stage: proposed`.

- [ ] Plan mode has no check of `## Spec changes`.

- [ ] The fixed `## Ship review` structure in the rulebook is this text:

  ``` markdown
  ## Ship review

  Reviewed by `iwe-ship-reviewer` on <YYYY-MM-DD>.

  - [x] Verify reported zero CRITICAL — confirmed: <Verify's verdict line>
  - [x] Every ADR the plan proposed is `stage: accepted` — confirmed: <keys> | N/A: the plan proposed no ADR
  - [x] Every ADR the plan superseded is `stage: superseded` and archived — confirmed: <archive keys> | N/A: the plan superseded no ADR
  - [x] The plan is `stage: done` with `completed` and no `rank` — confirmed: <completed date>
  - [x] Every feature in `release` is `stage: implemented` — confirmed: <keys> | N/A: `release` lists no feature
  - [x] Every bug in `release` is `stage: done` with no `rank` — confirmed: <keys> | N/A: `release` lists no bug
  - [x] Every bug in `release` has a `## Fix` that links this plan — confirmed: <keys> | N/A: `release` lists no bug
  - [x] The plan and every feature and bug it closed are archived with no hub link — confirmed: <archive keys>
  ```

- [ ] Ship mode checks each item of that structure and no item about a spec or a
  `## Rationale`.

- [ ] `scripts/check-ship-records.py::SHIP_REVIEW_ITEMS` holds the items of that
  structure.

- [ ] `scripts/check-ship-records.py` accepts a `## Ship review` that matches
  one of the two earlier structures.

- [ ] `scripts/tests/test_check_ship_records.py` runs the script on a review in
  the new structure and on a review in each earlier structure.

### Task 7: Cut a release from the archive

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`,
`docs/knowledge/SCHEMA.md`

- [ ] The release step of the `iwe-shipper` rulebook reads no spec and makes no
  spec diff.
- [ ] The step writes the themed sections from the `## Acceptance` scenarios of
  each plan in `data/archive/next-release/plans/`.
- [ ] For an archived plan that has no `## Acceptance`, the step reads its
  `## Spec changes`.
- [ ] The step writes `## Decisions` with the title of each ADR that was
  accepted or superseded after the base commit.
- [ ] The step writes `## Fixed` from the archived bugs, as today.
- [ ] The step moves `data/archive/next-release/adr/` with the other folders.
- [ ] The section for releases in `docs/knowledge/SCHEMA.md` describes that
  body.

### Task 8: Update the other rulebooks

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`,
`.agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md`,
`.agents/plugins/agentdev/agents/iwe-adversarial-reviewer.agent.md`,
`.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-audit/SKILL.md`,
`.agents/plugins/agentdev/README.md`

- [ ] The `iwe-implementer` rulebook loads the plan's `## Acceptance` and its
  ADRs, and no spec.
- [ ] The `iwe-implementer` rulebook treats a change to a scenario or to an ADR
  as a material deviation.
- [ ] `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#capturing-what-implementation-turns-up`
  sends a durable design fact to a plan revision that proposes an ADR.
- [ ] The `iwe-revision-evaluator` rulebook names `## Acceptance` where it named
  `## Spec changes`.
- [ ] The `iwe-adversarial-reviewer` rulebook reads the plan's `## Acceptance`
  scenarios and its ADRs.
- [ ] `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#the-stance` reads
  the related ADRs before it proposes a direction.
- [ ] `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#capturing` gives a
  decision to Plan in the handoff and writes no `## Rationale`.
- [ ] `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md#scope` lists
  `data/adr/`.
- [ ] `.agents/plugins/agentdev/README.md` describes Plan, Verify, and Ship
  without specs.

### Task 9: Update the manuals

**Files:** Modify: `AGENTS.md`, `docs/knowledge/AGENTS.md`,
`docs/knowledge/STRUCTURE.md`, `docs/knowledge/README.md`,
`docs/knowledge/data/product.md`

- [ ] `AGENTS.md#project-memory` sends a decision to an ADR that a plan
  proposes.
- [ ] Comment rule 3 in `AGENTS.md#comments` permits a reference to an ADR as
  `ADR-NNNN`.
- [ ] The operating loop in `docs/knowledge/AGENTS.md` consults ADRs, verifies
  against `## Acceptance`, and ships without a spec step.
- [ ] `docs/knowledge/AGENTS.md#conventions` gives the home of a decision as an
  ADR, and states that an accepted ADR is never edited.
- [ ] `docs/knowledge/AGENTS.md#conventions` says that `data/spec/` gets no new
  text.
- [ ] `docs/knowledge/STRUCTURE.md#design-decisions` describes ADRs, acceptance
  in the plan, and the release cut from the archive.
- [ ] `docs/knowledge/README.md` describes the workflow without specs.
- [ ] `docs/knowledge/data/product.md#authoring-rules` sends the decision from a
  spike to an ADR.
- [ ] `docs/knowledge/data/product.md#changelog` has a line for this change.

### Task 10: Switch the seed and the setup skill

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/.iwe/schemas/adr.yaml`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/adr.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/adr/0001-timer-counts-wall-clock-time.example.md`;
Delete:
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/spec/timer.example.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/backlog/draft-first-specs.md`;
Modify: the other files under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md`,
`.agents/plugins/agentdev/skills/iwe-setup/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] The seed copies of `.iwe/config.toml`, `SCHEMA.md`, `STRUCTURE.md`,
  `AGENTS.md`, and `README.md` agree with the workspace files after Tasks 1, 7,
  and 9.
- [ ] The seed holds the ADR hub and one example ADR that passes the schema.
- [ ] The seed holds no spec example and no `draft-first-specs` task.
- [ ] No seed document links the spec example or the `draft-first-specs` task.
- [ ] The example plans in the seed have `## Acceptance` and no
  `## Spec changes`.
- [ ] `scaffold.md` names `fill-product-doc` as the one task that
  `/agentdev:iwe-setup` closes.
- [ ] `/agentdev:iwe-setup` proposes and writes guides only. It writes no spec.
- [ ] The consumption guide does not say that the setup drafts specs.

### Task 11: Remove the spec text that is now false

**Files:** Modify: `docs/knowledge/data/spec/iwe-workflow-skills.md`,
`docs/knowledge/data/spec/pre-commit-gate.md`

- [ ] `spec/iwe-workflow-skills` has no requirement "Plans express spec impact
  at risk-appropriate fidelity".
- [ ] `spec/iwe-workflow-skills` has no requirement "Ship synchronizes durable
  specs by intelligent merge".
- [ ] `spec/iwe-workflow-skills` has no requirement "Release notes are written
  from the spec diff".
- [ ] `spec/iwe-workflow-skills` has no requirement "Each kind of knowledge has
  one home".
- [ ] No clause that remains in `spec/iwe-workflow-skills` says that a skill
  reads or writes a spec, `## Spec changes`, or `## Rationale`.
- [ ] No clause that remains in `spec/pre-commit-gate` gives a `## Ship review`
  item that Task 6 removed.
- [ ] `iwe find --references` shows no broken link to a removed requirement.

### Task 12: Update the documents that this plan changes

**Files:** Modify: `docs/knowledge/data/backlog/ephemeral-plans-and-stories.md`,
`docs/knowledge/data/plans/20261113-ste100-prose-rule.md`

- [ ] The decision "Specs stay" in `backlog/ephemeral-plans-and-stories` says
  that the scenarios stay on the story and are never merged into a spec.
- [ ] The rejected option about `data/spec/` in that task is removed.
- [ ] Each active plan other than this plan has `## Acceptance` and `## ADRs` in
  the new shape, and no `## Spec changes`.

### Task 13: Close this plan

**Files:** Modify:
`docs/knowledge/data/plans/20261113-adrs-and-workflow-off-specs.md`,
`docs/knowledge/data/plans.md`

- [ ] The commands in `## Verification` pass.
- [ ] This plan has `stage: done` and `completed`, is in
  `data/archive/next-release/plans/`, and has no link in `data/plans.md`.

## Verification

The session that does the tasks runs these commands. No Verify run and no Ship
run reads this plan.

``` bash
iwe normalize && iwe schema validate
uv run scripts/check-anchors.py
uv run pytest docs/knowledge/tests
uv run pytest scripts/tests/test_check_ship_records.py
uv run pytest .agents/plugins/agentdev/tests/test_iwe_seed.py
uv run validate_agent_files --recommend . --require-marketplace claude
```

## Out of scope

- The removal of a requirement that is redundant or wrong for another reason.
- The move of `## Rationale` entries into ADRs, and the change of the code
  comments that cite `spec/<key>`.
- The tests that are missing, and the removal of `data/spec/`, its schema, and
  its hub.
- The glossary. [Make ASD-STE100 the rule for all
  prose](../archive/next-release/plans/20261113-ste100-prose-rule.md) writes it.
- The other parts of [Plans as ephemeral implementation documents; stories as
  the planned work](../backlog/ephemeral-plans-and-stories.md).
- A check that stops an edit to an accepted ADR.

## Key references

- `.iwe/config.toml#schemas.hub` — the hub binding that gains `data/adr`.
- `.iwe/schemas/bug.yaml` — a schema that checks body sections in order.
- `docs/knowledge/SCHEMA.md` — the frontmatter reference.
- `docs/knowledge/data/index.md#reference` — the section that links the ADR hub.
- `scripts/check-ship-records.py::SHIP_REVIEW_ITEMS` — the fixed Ship review
  items.
- `scripts/check-ship-records.py::check_placement` — the check of which side of
  the archive a document is on.
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps` — step 4 holds
  the section list.
- `.agents/plugins/agentdev/skills/iwe-plan-review/references/plan-rules.md` —
  the rules that `iwe-plan-reviewer` checks.
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#steps` — step 3 holds
  the Completeness check.
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps` — steps 4 and 5
  are the spec merge, and step 8 is the release cut.
- `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md#ship-mode` — the
  fixed `## Ship review` structure.
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#capturing-what-implementation-turns-up`
  — where a durable design fact is routed.
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#capturing` — where
  Explore routes a decision.
- `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md#steps` — the steps that
  draft specs.
- `.agents/plugins/agentdev/tests/test_iwe_seed.py::test_scaffold_support_files_match_the_publisher_workspace`
  — the test that compares the seed with the workspace.
