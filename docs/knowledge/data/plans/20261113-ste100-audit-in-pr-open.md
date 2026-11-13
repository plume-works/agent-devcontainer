---
type: plan
created: 2026-11-13
release: internal
description: Move the ASD-STE100 audit of added pull request prose from the pr-review skill to the pr-open skill, and limit the STE100 Auditor in plan review to two more runs.
sources:
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .agents/plugins/agentdev/agents/ste100-auditor.agent.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/873
---

# Audit the added prose in pr-open, and limit the plan-review reruns

## Context

The `pr-review` skill runs `/agentdev:audit-ste100` on the prose that a pull
request adds. Each finding blocks the merge. The audit does not give the same
findings two times for the same text: see [Bug: the ASD-STE100 audit gives
different findings for the same
text](../bugs/ste100-audit-not-deterministic.md). Thus the AI reviewer can
request changes again after each fix.

The repository owner decided these points:

- `/agentdev:pr-open` audits the added prose in diff scope before it writes the
  pull request body. It fixes each finding, and then it pushes the branch.
- `pr-review` does not audit prose against ASD-STE100.
- The new `pr-open` behavior has no spec text. Task 6 removes the `pr-review`
  requirement.
- Plan review runs the `STE100 Auditor` again two times at most for one draft.
  The third report is the last. Plan applies its findings, and the three other
  reviewers run.

This plan does not fix the bug. The bug remains `pending`, and `release` does
not list it.

## Approach

`pr-open` adds the audit at the start of step 6, `PR Draft Construction`. Before
that point, step 3 commits the work and step 4 merges the base. Thus the diff
from the base is the diff that the pull request will show. `pr-open` dispatches
the `STE100 Auditor` agent with that diff and the scope `diff`. The agent reads
the text in a new context, and the session that wrote the text does not examine
it. `pr-open` applies each replacement in the report. It commits the changes
through `/agentdev:git-commit`. Then it writes the body and pushes.

`pr-open` runs the audit one time for each run. It does not audit its own
replacements again, because a second run can report new findings on the same
text. The audit reads two types of lines. These are the lines that the diff adds
to document files and skill files. They also include the comments and docstrings
that the diff adds to code files. It does not read the pull request title, the
pull request body, or a commit message.

Task 2 removes these parts of `pr-review`:

- the ASD-STE100 item of `## Review Focus`
- the ASD-STE100 pass
- the row of the ASD-STE100 pass in the table of effort tiers
- the ASD-STE100 tier that blocks the merge

The durable-knowledge pass then runs again in the same message as the compliance
and correctness passes.

Rejected:

- **Keep the audit in `pr-review`, with findings that do not block.** Each
  review then posts a new set of threads, and each thread blocks the merge until
  a person resolves it.
- **Audit the prose in `/agentdev:iwe-ship` or in Implement.** These skills do
  not run on a pull request that no plan made.
- **Audit again until the report is `No findings.`** Because of the bug, the
  number of audits is unknown.

Plan review has the same problem. The `iwe-planner` rulebook runs
`/agentdev:iwe-plan-review` again after each correction, until the
`STE100 Auditor` reports `No findings.`. The bug makes the number of runs
unknown. The Plan session counts the runs on one draft. On the third run, its
request names that run as the last `STE100 Auditor` run. The skill then
dispatches the three other reviewers also when the report has findings. Plan
applies the findings and does not run the `STE100 Auditor` again.

## Implementation Steps

### Task 1: Add the prose audit to `pr-open`

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-open/SKILL.md`

- [x] Step 6 starts with a prose audit that dispatches the `STE100 Auditor`
  agent. The prompt gives the scope `diff`. It also gives the diff from the
  merge base to `HEAD`. The merge base is the merge base of `HEAD` and the base
  that step 6 uses.
  - **Evidence:** `pr-open/SKILL.md#6-pr-draft-construction` › "Audit the added
    prose first" dispatches the agent with the scope `diff` and
    `git diff "$(git merge-base origin/<base> HEAD)" HEAD`.
- [x] The prompt limits the audit to two types of text. These are the lines that
  the diff adds to document files and skill files, and the comments and
  docstrings that the diff adds to code files.
  - **Evidence:** the third prompt item names those two types of text.
- [x] The step tells the session to apply each replacement in the report, and to
  commit the changes through `/agentdev:git-commit` before it generates the
  body.
  - **Evidence:** "Apply each replacement in the report. Then commit the changes
    through the `git-commit` skill." comes before the body generation.
- [x] The step tells the session not to run the audit again after it applies the
  replacements.
  - **Evidence:** "Do not run the audit again after you apply the replacements".

### Task 2: Remove the ASD-STE100 audit from `pr-review`

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [x] `## Review Focus` has no ASD-STE100 item.
  - **Evidence:** reverse-applied the `pr-review` hunks of #871;
    `grep -i ste100` on the skill prints nothing.
- [x] In `## Review Focus`, the tier that blocks the merge has two passes: the
  correctness pass and the durable-knowledge pass.
  - **Evidence:** the blocking tier reads "anything from a **correctness pass**
    ... or a **durable-knowledge pass**".
- [x] The table of effort tiers has no `audit-ste100` row.
  - **Evidence:** the table ends with the `iwe-audit` and `validation` rows.
- [x] The tier paragraph under the table of effort tiers does not name an
  ASD-STE100 pass.
  - **Evidence:** the paragraph names the Step 3 metadata gate and the Step 4
    durable-knowledge pass only.
- [x] Step 4 has no ASD-STE100 pass. The durable-knowledge pass runs in the same
  message as the compliance and correctness passes, and no step dispatches
  passes in a second message.
  - **Evidence:** Step 4 lists the compliance, correctness, and
    durable-knowledge passes, and the Claude Code item issues every pass in a
    single message.

### Task 3: Limit the `STE100 Auditor` reruns in plan review to two

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md`,
`.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [x] `iwe-plan-review` step 3 does not stop on a finding when the request names
  the run as the last `STE100 Auditor` run.
  - **Evidence:** `iwe-plan-review/SKILL.md#steps` › "Do not stop when the
    request names the run as the last `STE100 Auditor` run".
- [x] `iwe-plan-review` step 4 dispatches the three other agents after the last
  `STE100 Auditor` run, also when its report has findings.
  - **Evidence:** step 4 dispatches "when the report has no finding, or when the
    request names the run as the last `STE100 Auditor` run".
- [x] `iwe-planner` step 7 tells Plan to name the third run of
  `/agentdev:iwe-plan-review` on one draft as the last `STE100 Auditor` run.
  - **Evidence:** `iwe-planner.agent.md#steps` › "In the request of the third
    run, name that run as the last `STE100 Auditor` run".
- [x] `iwe-planner` step 7 tells Plan to apply the findings of the last
  `STE100 Auditor` run and not to run the `STE100 Auditor` again.
  - **Evidence:** step 7 › "Apply the findings of the last `STE100 Auditor` run,
    and do not run the `STE100 Auditor` again".

### Task 4: Observe the audit in a real pull request

**Closed by:** the first pull request that `/agentdev:pr-open` opens or updates
after this plan merges, and the AI review of that pull request.

- [ ] The `pr-open` run dispatches the `STE100 Auditor` before it generates the
  body.
- [ ] When the pull request adds a document line with a word that ASD-STE100
  does not approve, the `pr-open` run pushes a commit with the replacement.
- [ ] The AI review of that pull request posts no ASD-STE100 finding.

### Task 5: Observe the rerun limit in a real plan review

**Closed by:** the first plan draft after this plan merges whose third
`/agentdev:iwe-plan-review` run receives an `STE100 Auditor` finding.

- [ ] On that run, the skill dispatches the three other reviewers.
- [ ] Plan applies the `STE100 Auditor` findings of that run without a fourth
  `STE100 Auditor` run.

### Task 6: Edit the specs by hand

**Files:** Modify: `docs/knowledge/data/spec/pr-review.md`,
`docs/knowledge/data/spec/iwe-workflow-skills.md`

Ship merges no spec, so this task makes the spec edits that this plan needs.

- [ ] `spec/pr-review` has no requirement "added prose gets an ASD-STE100 pass
  before the durable-knowledge pass".

- [ ] The `description` of `spec/pr-review` does not name the ASD-STE100 pass.

- [ ] `spec/pr-review` has no `## Rationale` entry "The ASD-STE100 pass checks
  from the model's knowledge of the standard".

- [ ] The requirement "Plan review runs its reviewers from fresh contexts and
  changes nothing" in `spec/iwe-workflow-skills` holds this text and these
  scenarios:

  ``` markdown
  ## MODIFIED Requirements

  ### Requirement: Plan review runs its reviewers from fresh contexts and changes nothing

  `/agentdev:iwe-plan-review <plan>` SHALL first dispatch the `STE100 Auditor`
  alone, with a prompt that carries only the plan file path and the scope `plan`.
  When that report holds a finding, the skill SHALL return it verbatim under the
  agent's name and SHALL dispatch no other agent, unless the request names the
  run as the last `STE100 Auditor` run.

  When the report holds none, or the request names the run as the last `STE100
  Auditor` run, the skill SHALL dispatch the `Durable Knowledge Auditor`,
  `iwe-plan-reviewer`, and `iwe-ship-reviewer` in one message. The skill SHALL
  NOT forward conversation turns. The prompt of the auditor SHALL carry only the
  plan file path and the scope `plan`. The prompt of `iwe-plan-reviewer` SHALL
  carry only the plan key and the absolute path of the skill's
  `references/plan-rules.md`. The prompt of `iwe-ship-reviewer` SHALL carry only
  the plan key and the mode `plan`.

  The `iwe-planner` rulebook SHALL run the `STE100 Auditor` on one draft three
  times at most. Its third request SHALL name the run as the last `STE100
  Auditor` run, and Plan SHALL apply the findings of that run without a fourth
  run.

  The skill SHALL perform no review step itself. It SHALL return every report
  verbatim under the name of each agent. It SHALL edit no file and SHALL commit
  nothing. Its caller applies the verdicts. The skill SHALL be model-invocable, so
  the `iwe-planner` rulebook can run it in every mode.

  #### Scenario: Plan reaches its review step

  - **WHEN** `iwe-planner` reaches its review step on a created or revised plan,
    and the `STE100 Auditor` reports no finding
  - **THEN** the skill dispatches the three other agents in parallel with only
    those prompts. The four reports return unchanged. The plan file stays
    unchanged until Plan applies them.

  #### Scenario: The draft breaks the prose rule

  - **WHEN** the `STE100 Auditor` reports a finding on the draft, and the request
    does not name the run as the last `STE100 Auditor` run
  - **THEN** only that report returns, no other agent is dispatched, and the plan
    file is unchanged

  #### Scenario: The last STE100 Auditor run reports a finding

  - **WHEN** the `STE100 Auditor` reports a finding on the third run for one
    draft, which the request names as the last `STE100 Auditor` run
  - **THEN** the skill dispatches the three other agents, and the four reports
    return unchanged. Plan applies the `STE100 Auditor` findings and does not run
    the `STE100 Auditor` again.
  ```

## Acceptance

### Scenario: pr-open audits the added prose before it pushes

- **WHEN** `/agentdev:pr-open` reaches step 6 on a branch whose diff adds prose
- **THEN** it dispatches the `STE100 Auditor` with the scope `diff`, applies
  each replacement, commits it, and only then writes the body and pushes
- **Checked at ship:** `.agents/plugins/agentdev/skills/pr-open/SKILL.md`

### Scenario: pr-review does not audit prose against ASD-STE100

- **WHEN** `/agentdev:pr-review` reviews a pull request that adds prose
- **THEN** no pass checks the prose against ASD-STE100, and the
  durable-knowledge pass runs in the same message as the compliance and
  correctness passes
- **Checked at ship:** `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

### Scenario: The draft breaks the prose rule

- **WHEN** the `STE100 Auditor` reports a finding on a plan draft, and the
  request does not name the run as the last `STE100 Auditor` run
- **THEN** `/agentdev:iwe-plan-review` returns only that report and dispatches
  no other agent
- **Checked at ship:**
  `.agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md`

### Scenario: The last STE100 Auditor run reports a finding

- **WHEN** the `STE100 Auditor` reports a finding on the third run for one
  draft, which the request names as the last `STE100 Auditor` run
- **THEN** the skill dispatches the three other agents, and Plan applies the
  `STE100 Auditor` findings without a fourth `STE100 Auditor` run
- **Checked at ship:** `.agents/plugins/agentdev/agents/iwe-planner.agent.md`

## Verification

1. `uv run validate_agent_files --recommend . --require-marketplace claude`
   exits 0.
2. `grep -n -i "ste100\|prose focus" .agents/plugins/agentdev/skills/pr-review/SKILL.md`
   prints nothing.
3. `grep -n "STE100 Auditor" .agents/plugins/agentdev/skills/pr-open/SKILL.md`
   prints the lines of the step 6 audit.
4. `grep -n -i "last .STE100 Auditor. run" .agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md .agents/plugins/agentdev/agents/iwe-planner.agent.md`
   prints lines from both files.
5. `uv run scripts/check-anchors.py` exits 0.

## Out of scope

- The fix of [Bug: the ASD-STE100 audit gives different findings for the same
  text](../bugs/ste100-audit-not-deterministic.md).
- An audit of the pull request title, the pull request body, or a commit
  message.
- A spec for `pr-open`.

## Key references

- `.agents/plugins/agentdev/skills/pr-open/SKILL.md#6-pr-draft-construction` —
  the step that adds the audit.
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md#4-branch-sync-with-the-base-branch`
  — the step that sets the base for the diff.
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#review-focus` › "**Prose
  focus** (ASD-STE100 Issue 9)" — the item to remove.
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#effort-tiers` › "|
  audit-ste100 |" — the row of the table of effort tiers to remove.
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#steps` › "1x **ASD-STE100
  pass**" — the pass to remove.
- `.agents/plugins/agentdev/agents/ste100-auditor.agent.md` — the agent that
  `pr-open` dispatches.
- `.agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md#steps` › "Stop on a
  finding" — the step that has the exception for the last run.
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps` › "Review the
  plan from a fresh context" — the step that counts the runs.
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-plan-review-runs-its-reviewers-from-fresh-contexts-and-changes-nothing`
  — the requirement that Ship modifies.
- `docs/knowledge/data/spec/pr-review.md#requirement-added-prose-gets-an-asd-ste100-pass-before-the-durable-knowledge-pass`
  — the requirement that Ship removes.
