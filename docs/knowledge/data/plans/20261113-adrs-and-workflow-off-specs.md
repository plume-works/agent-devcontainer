---
type: plan
created: 2026-11-13
release: internal
description: Add ADRs to the graph and change Plan, Verify, Ship, and the release cut so that no workflow skill reads or writes a spec.
sources:
- resource: https://github.com/adr/madr/blob/develop/template/adr-template.md
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

- An ADR is a document in the graph at `data/adr/NNNN-<slug>.md`. It has the
  MADR headings. Code comments cite it as `ADR-NNNN`.
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

- [ ] `.iwe/schemas/adr.yaml` requires the frontmatter `type: adr`, `stage`, and
  `description`. It has no date field: git holds the date.
- [ ] The schema permits only these values of `stage`: `proposed`, `accepted`,
  `rejected`, `deprecated`, `superseded`.
- [ ] The schema permits the optional frontmatter `decision-makers`, a list of
  strings, and `supersedes`, a list of `adr/NNNN-<slug>` keys.
- [ ] The schema requires these sections under one H1, in this order:
  `## Context and Problem Statement`, `## Considered Options`,
  `## Decision Outcome`.
- [ ] The schema permits these optional sections at their MADR positions:
  `## Decision Drivers`, `## Pros and Cons of the Options`,
  `## More Information`.
- [ ] `.iwe/config.toml` binds the `adr` schema to `data/adr/**` and
  `data/archive/*/adr/**`.
- [ ] `.iwe/config.toml#schemas.hub` matches `data/adr`.
- [ ] `docs/knowledge/data/adr.md` is a hub with no member.
- [ ] `docs/knowledge/data/index.md#reference` links the ADR hub.
- [ ] `docs/knowledge/SCHEMA.md` has a section for ADRs. It gives the file name,
  the frontmatter, the sections, the stages, the rule that an accepted ADR is
  never edited, and the `ADR-NNNN` form for a code comment.
- [ ] `docs/knowledge/SCHEMA.md` names `adr/` as an archive folder.
- [ ] `docs/knowledge/tests/test_adr_schema.py` runs `iwe schema validate` on a
  fixture workspace. A complete ADR passes. An ADR with a missing required
  section fails. An ADR with an unknown stage fails.
- [ ] `scripts/check-ship-records.py` reports an ADR at `proposed` or `accepted`
  that is in `data/archive/`.
- [ ] `scripts/check-ship-records.py` reports an ADR at `rejected`,
  `deprecated`, or `superseded` that is outside `data/archive/`.
- [ ] `scripts/tests/test_check_ship_records.py` runs the script on both cases.

### Task 2: Write the first two ADRs

**Files:** Create:
`docs/knowledge/data/adr/0001-code-and-tests-state-behaviour.md`,
`docs/knowledge/data/adr/0002-decisions-are-madr-adrs-in-the-graph.md`; Modify:
`docs/knowledge/data/adr.md`

- [ ] `docs/knowledge/data/adr/0001-code-and-tests-state-behaviour.md` holds
  this text:

  ``` markdown
  ---
  type: adr
  stage: accepted
  decision-makers:
  - the repository owner
  description: Code and tests are the only statement of how the product behaves; ADRs hold the reasons and the glossary holds the terms.
  ---

  # Code and tests are the only statement of behaviour

  ## Context and Problem Statement

  `data/spec/` states the behaviour of the repository a second time, in prose.
  [The spec usefulness audit](../findings/spec-usefulness-audit.md) compared
  264 requirements with the code. 207 of them repeat a test, a rulebook, or code
  that reads plainly. 34 of them are not fully true, and 20 of the 40 specs
  hold one of those. Which document states how the product behaves?

  ## Decision Drivers

  - A statement of behaviour that no test runs moves away from the code.
  - The code does not show the reason for a decision or the options that were
    rejected.
  - A project term needs one definition.

  ## Considered Options

  - Code and tests state behaviour. ADRs state reasons. The glossary states
    terms.
  - Keep the specs and merge each change into them at ship.
  - Keep a spec only for behaviour that no test can reach.

  ## Decision Outcome

  Chosen option: "Code and tests state behaviour. ADRs state reasons. The
  glossary states terms.", because each statement then has one home, and a
  change cannot merge without an update to that home.

  ### Consequences

  - Good, because a statement of behaviour cannot be false while its test
    passes.
  - Good, because Plan, Verify, and Ship do no spec work.
  - Bad, because the behaviour of a rulebook has no test. Its acceptance
    scenarios are checked one time at ship and then stay only in the archived
    plan.
  - A plan holds its acceptance scenarios in `## Acceptance`, and each scenario
    names its test. Ship copies nothing.
  - The release cut reads the archived plans, the closed bugs, and the ADRs.
  - `data/spec/` gets no new text. Later work moves its reasons into ADRs, adds
    the tests that are missing, and deletes it.

  ### Confirmation

  No workflow skill and no agent rulebook reads or writes a file under
  `data/spec/`.

  ## Pros and Cons of the Options

  ### Keep the specs and merge each change into them at ship

  - Good, because one document gathers behaviour that many files implement.
  - Bad, because the merge is a careful reading, and nothing fails when it is
    wrong.
  - Bad, because 87% of the requirements only repeat what a test or a rulebook
    states.

  ### Keep a spec only for behaviour that no test can reach

  - Good, because the behaviour of a rulebook keeps a written contract.
  - Bad, because the rulebook is that text already. The audit found 67
    requirements that are a second copy of a rulebook.

  ## More Information

  The decision and its scope are in [Shrink the knowledge base to an issue
  tracker and decision
  records](../backlog/shrink-knowledge-base-to-issues-and-adrs.md).
  ```

- [ ] `docs/knowledge/data/adr/0002-decisions-are-madr-adrs-in-the-graph.md`
  holds this text:

  ``` markdown
  ---
  type: adr
  stage: accepted
  decision-makers:
  - the repository owner
  description: Each decision is one MADR document in data/adr/, proposed by Plan, accepted by Ship, and never edited after that.
  ---

  # Each decision is a MADR ADR in the graph

  ## Context and Problem Statement

  A decision and its rejected options were entries in the `## Rationale` of a
  spec. An entry was edited in place when the decision changed. [The spec
  usefulness audit](../findings/spec-usefulness-audit.md) found 189 entries, and
  the code contradicts 4 of them. Where is a decision kept, and how does it
  change?

  ## Considered Options

  - One MADR document for each decision, in the graph at `data/adr/`.
  - One MADR document for each decision, in a folder outside the graph.
  - Entries in a `## Rationale` section that are edited in place.

  ## Decision Outcome

  Chosen option: "One MADR document for each decision, in the graph at
  `data/adr/`", because plans and bugs can link an ADR, and the schema can check
  its headings and its stage.

  - The file is `data/adr/NNNN-<slug>.md`. A number is never used again.
  - The headings are those of the MADR template.
  - `stage` is the lifecycle key, as in each other document: `proposed`,
    `accepted`, `rejected`, `deprecated`, `superseded`. The MADR `status` key is
    not used.
  - Plan files an ADR at `proposed` in the pull request of the plan. Ship sets
    it to `accepted`. The ADR of a cancelled plan becomes `rejected`.
  - An accepted ADR is never edited. A new ADR supersedes it. The superseded ADR
    moves to `data/archive/`.
  - A code comment cites an ADR as `ADR-NNNN`.

  ### Consequences

  - Good, because a reader sees each decision as it was made.
  - Good, because the hub lists only the ADRs that are in force or proposed.
  - Bad, because a small correction to a decision needs a new ADR.

  ### Confirmation

  `iwe schema validate` checks the headings and the stage. The `ship-records`
  hook checks that an ADR is on the correct side of the archive.

  ## Pros and Cons of the Options

  ### One MADR document for each decision, in a folder outside the graph

  - Good, because tools for ADRs find the folder.
  - Bad, because `iwe` does not check the links or the schema of a document
    outside the graph.

  ### Entries in a `## Rationale` section that are edited in place

  - Good, because the reason is near the statement of behaviour.
  - Bad, because an edit removes the decision that was in force before.

  ## More Information

  The template is the MADR template at
  <https://github.com/adr/madr/blob/develop/template/adr-template.md>.
  ```

- [ ] `docs/knowledge/data/adr.md` links both ADRs in sorted order.

### Task 3: Change the plan shape

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`.agents/plugins/agentdev/skills/iwe-plan-review/references/plan-rules.md`

- [ ] The section list in step 4 of the `iwe-planner` rulebook has
  `## Acceptance` and `## ADRs`, and no `## Spec changes`.
- [ ] The rulebook defines `## Acceptance`: one `### Scenario:` block for each
  behaviour that the plan adds, changes, or removes, with a `- **WHEN**` line
  and a `- **THEN**` line.
- [ ] The rulebook says that each scenario ends with one of two lines.
  `- **Test:**` names the test as `path::test_name`. `- **Checked at ship:**`
  names the rulebook or the file that the verifier reads, for behaviour that no
  test can reach.
- [ ] The rulebook says that a plan with no change in behaviour writes
  `None — no behavioral change` under `## Acceptance`.
- [ ] The rulebook defines `## ADRs`: one link for each ADR that the plan
  proposes. A plan that proposes none omits the section.
- [ ] The rulebook says when a plan proposes an ADR: the plan makes a decision
  that a developer must know and that the code cannot show.
- [ ] Step 4 tells Plan to file each ADR at `data/adr/<NNNN>-<slug>.md` with
  `stage: proposed`, the next free number in `data/adr/` and
  `data/archive/*/adr/`, and a link in `data/adr.md`.
- [ ] The rulebook says that the rejected options go in the ADR, and that
  `## Approach` gives the shape of the solution.
- [ ] The rulebook says that Plan never edits an accepted ADR, and that a plan
  which changes a decision proposes a new ADR that names the earlier ADR in
  `supersedes`.
- [ ] The rulebook has no section `## The three forms of ## Spec changes` and no
  rule that names `## Spec changes`, a spec, or `## Rationale`.
- [ ] The text about `release` in step 4 says that the release cut writes the
  page from the archive.
- [ ] `plan-rules.md` has a section `## Acceptance` with one rule: each scenario
  has a `**WHEN**` line, a `**THEN**` line, and a `**Test:**` line or a
  `**Checked at ship:**` line.
- [ ] `plan-rules.md` has a rule that each ADR in `## ADRs` exists at
  `stage: proposed`.

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
  prose](20261113-ste100-prose-rule.md) writes it.
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
