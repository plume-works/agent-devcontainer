---
type: plan
created: 2026-11-15
release: internal
description: Move the evidence of a ticked plan task into the message of the commit that ticks it. Make sure that each commit has one tick and one completion evidence block.
sources:
- resource: docs/knowledge/data/adr/0086-plan-ticks-need-evidence-lines.md
- resource: docs/knowledge/tests/test_plan_checkboxes.py
---

# Put task evidence in the commit message

## Context

[Plan tasks evidence and ADRs as git
history](../archive/next-release/backlog/plan-evidence-and-decisions-in-git-history.md)
asks for the evidence of a plan task in the commit that ticks it. The commit
then connects the tick, the code change, and the reason of the agent at that
time. `git log` and `git blame` find the evidence from the code.

Today each ticked task has a `- **Evidence:**` line in the plan
([ADR-0086](../adr/0086-plan-ticks-need-evidence-lines.md)). Only
`docs/knowledge/tests/test_plan_checkboxes.py` parses the line. Verify and
`/agentdev:iwe-plan-review` tell their review agents to ignore it.
`pr-gen-description/SKILL.md` Step 5 names the plan's per-task evidence as the
record, and Task 5 changes that reference.

## Approach

The Implement session ticks one plan task in a commit and writes a completion
evidence block in the commit message. The diff shows which plan task the commit
ticks, so the block names no task. One script, `scripts/completion-evidence.py`,
has two subcommands:

- `check-message` runs as a `commit-msg` hook. It reads the staged diff of
  `docs/knowledge/data/plans/` and the message file.
- `show` prints the ticked plan task and the block of each commit of a pull
  request from `refs/pull/<N>/head`. These commits stay there after the squash
  merge.

A tick is the change of a line `- [ ] <text>` to `- [x] <text>` in a file under
`docs/knowledge/data/plans/`. The hook applies two rules to a commit that ticks
a plan task. The commit ticks only one plan task. The message has one completion
evidence block that contains text.

The block starts at a line `---` that a line `completion evidence:` follows, and
it continues to the end of the message. Git trailer lines at the end of the
message, such as `Co-Authored-By:`, are not text of the block. The hook does not
examine a merge commit, because a merge commit moves ticks from other commits.

A commit that does not run the hook has no block, and `show` then prints no
evidence for its tick. The `plan-checkboxes` check keeps only the rule that a
plan at `stage: done` has no unticked task.

## Implementation Steps

### Task 1: Check the commit message of a commit

**Files:** Create: `scripts/completion-evidence.py`,
`scripts/tests/test_completion_evidence.py`

The commit message has this format. The completion evidence block is its footer:

```
<what was done belongs to normal commit message part>

---
completion evidence:
<how it was checked>
```

- [ ] `check-message <message-file>` exits 0 for a staged tick of one plan task
  with a block, and the test passes.
- [ ] `check-message` exits 1 and names the plan task for a staged tick with no
  block, and the test passes.
- [ ] `check-message` exits 1 and names the plan task for a staged tick with an
  empty block, and the test passes.
- [ ] `check-message` exits 1 for a staged tick of two plan tasks, and the test
  passes.
- [ ] `check-message` exits 0 for a commit that ticks no plan task, and the test
  passes.
- [ ] `check-message` exits 0 while a merge is in progress (`MERGE_HEAD` exists)
  in the fixture repository, and the test passes.

### Task 2: Show the evidence of a pull request

**Files:** Modify: `scripts/completion-evidence.py`,
`scripts/tests/test_completion_evidence.py`

`show <N>` fetches `refs/pull/<N>/head` and `main` from `origin`. It prints the
ticked plan task and the block of each commit that is not a merge commit and
that is not on `main`. The test uses a bare fixture repository as `origin`.

- [ ] For a pull request whose branch merged `main` one time, `show <N>` prints
  each ticked plan task with its block, oldest first. The test passes.

### Task 3: Run the check at commit time

**Files:** Modify: `.pre-commit-config.yaml`,
`py_packages/agentdev_runtime/agentdev_runtime/project.py`, `.claude/startup.py`

- [ ] `.pre-commit-config.yaml` has a local hook `completion-evidence` at
  `stages: [commit-msg]` that runs `check-message`. In this checkout, the hook
  stops a commit that has a tick and no block.
- [ ] `HOOK_TYPES` in `py_packages/agentdev_runtime/agentdev_runtime/project.py`
  and in `.claude/startup.py` has `commit-msg`, and
  `uv run pytest scripts/tests/test_agent_runtime_workspace.py scripts/tests/test_cloud_startup.py`
  passes.

### Task 4: Remove the evidence-line rule from the plan-checkboxes check

**Files:** Modify: `docs/knowledge/tests/test_plan_checkboxes.py`

- [ ] The check has no evidence-line rule, and the change removes the tests of
  that rule. A new test shows that a ticked task with no evidence line passes.
  `uv run pytest docs/knowledge/tests/test_plan_checkboxes.py` passes.

### Task 5: Change the rules that name the evidence line

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`,
`.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`.agents/plugins/agentdev/agents/iwe-verifier.agent.md`,
`.agents/plugins/agentdev/agents/iwe-plan-reviewer.agent.md`,
`.agents/plugins/agentdev/skills/iwe-plan-review/references/plan-rules.md`,
`.agents/plugins/agentdev/skills/iwe-audit/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md`,
`docs/knowledge/AGENTS.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/AGENTS.md`,
`docs/knowledge/CHANGELOG.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/CHANGELOG.md`

- [ ] Step 6, step 8, and the rules of `iwe-implementer.agent.md` tell the
  Implement session to tick one plan task in a commit. They also tell it to
  write the block in the commit message. They show the block format of Task 1 as
  a fenced block.
- [ ] `iwe-planner.agent.md` step 4, `plan-rules.md`, `iwe-verifier.agent.md`,
  `iwe-plan-reviewer.agent.md`, and `iwe-audit/SKILL.md` name the completion
  evidence block, and
  `rg -n 'Evidence:\*\*|evidence line' .agents/plugins/agentdev/agents/iwe-implementer.agent.md .agents/plugins/agentdev/agents/iwe-planner.agent.md .agents/plugins/agentdev/agents/iwe-verifier.agent.md .agents/plugins/agentdev/agents/iwe-plan-reviewer.agent.md .agents/plugins/agentdev/skills/iwe-plan-review/references/plan-rules.md .agents/plugins/agentdev/skills/iwe-audit/SKILL.md`
  prints nothing.
- [ ] `pr-gen-description/SKILL.md` Step 5 says that the commits of the pull
  request contain the task evidence.
- [ ] Both copies of `docs/knowledge/AGENTS.md` replace the evidence-line rule
  with the commit-message rule, and `diff` of the two copies prints nothing.
- [ ] Both copies of `docs/knowledge/CHANGELOG.md` have an `[Unreleased]` entry
  for the change, and `diff` of the two copies prints nothing.
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.

### Task 6: Examine the commits of the first plan after the change

**Closed by:** the user, on the first pull request that an Implement session
makes for a plan after this change is on `main`.

- [ ] `scripts/completion-evidence.py show <N>` prints one ticked plan task and
  one completion evidence block for each commit that ticks a plan task.

## Acceptance

### Scenario: A tick with a block passes the commit-msg hook

- **WHEN** a commit ticks one plan task and its message has a completion
  evidence block with text
- **THEN** `check-message` exits 0
- **Test:**
  `scripts/tests/test_completion_evidence.py::test_one_tick_with_block_passes`

### Scenario: A tick with no block fails the commit-msg hook

- **WHEN** a commit ticks one plan task and its message has no block, or a block
  with no text
- **THEN** `check-message` exits 1 and names the plan task
- **Test:**
  `scripts/tests/test_completion_evidence.py::test_tick_without_block_fails`

### Scenario: Two ticks in one commit fail

- **WHEN** a commit ticks two plan tasks
- **THEN** `check-message` exits 1
- **Test:** `scripts/tests/test_completion_evidence.py::test_two_ticks_fail`

### Scenario: A block is not necessary for a commit with no tick

- **WHEN** a commit ticks no plan task
- **THEN** `check-message` exits 0 for any message
- **Test:**
  `scripts/tests/test_completion_evidence.py::test_no_tick_needs_no_block`

### Scenario: check-message does not examine a merge commit

- **WHEN** a merge adds ticks from a different branch and `MERGE_HEAD` exists
- **THEN** `check-message` exits 0
- **Test:**
  `scripts/tests/test_completion_evidence.py::test_merge_in_progress_is_skipped`

### Scenario: `show` prints the evidence of a pull request

- **WHEN** `show <N>` runs for a pull request whose commits tick plan tasks with
  blocks
- **THEN** it prints each ticked plan task with its block, oldest first, and no
  commit that is on `main`. The output also shows a commit that a predecessor
  pull request in a chain added, because that commit is not on `main`
- **Test:**
  `scripts/tests/test_completion_evidence.py::test_show_prints_each_tick`

### Scenario: A ticked task with no evidence line passes the check

- **WHEN** an active plan has a ticked task with no `- **Evidence:**` line
- **THEN** the `plan-checkboxes` check reports no rule break
- **Test:**
  `docs/knowledge/tests/test_plan_checkboxes.py::test_ticked_task_needs_no_evidence_line`

### Scenario: The Implement session writes evidence in the commit message

- **WHEN** the Implement session finishes a plan task
- **THEN** `iwe-implementer.agent.md` tells it to tick one plan task and to
  write the completion evidence block in the message of that commit.
  `iwe-implementer.agent.md` tells the Implement session to write no evidence
  line in the plan
- **Checked at ship:**
  `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

## ADRs

[The commit that ticks a plan task contains its
evidence](../adr/0092-completion-evidence-in-the-commit-message.md)

## Verification

``` bash
uv run pytest scripts/tests/test_completion_evidence.py
uv run pytest docs/knowledge/tests/test_plan_checkboxes.py
uv run pytest scripts/tests/test_agent_runtime_workspace.py scripts/tests/test_cloud_startup.py
uv run validate_agent_files --recommend . --require-marketplace claude
diff docs/knowledge/AGENTS.md .agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/AGENTS.md
diff docs/knowledge/CHANGELOG.md .agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/CHANGELOG.md
```

## Out of scope

- A change to the evidence lines of closed or archived plans. They stay as they
  are.
- A check in a consumer. The catalog rules tell the Implement session what to
  write. The hook is in this repository only.
- A check of the text in a block. The hook examines only the format of the
  block.
- A CI check of the commits of a pull request. Only a change to pushed commits
  can correct a failure of that check.
- The `## Decisions` section of the pull request body, and the sequence of
  sources that an agent reads to find an answer. [Put decisions in the git
  history](20261115-decisions-in-git-history.md) changes them.
- The `**Evidence:**` items of the `## Verification` section of a pull request
  body in `/agentdev:code-review-standards`. That section is not a plan.
- The `- **Evidence:**` lines of the progress document of
  `/agentdev:template-consume`. That document is not a plan.

## Key references

- `docs/knowledge/tests/test_plan_checkboxes.py::check_plan` — the check of the
  evidence-line rule today.
- `docs/knowledge/tests/test_plan_checkboxes.py::evidence_text` — the evidence
  parser that the change removes.
- `.pre-commit-config.yaml#repos` › "id: plan-checkboxes" — the hook of the
  `plan-checkboxes` check, and the place of the new hook.
- `py_packages/agentdev_runtime/agentdev_runtime/project.py` › "HOOK_TYPES =" —
  the hook types that the runtime installs.
- `.claude/startup.py` › "HOOK_TYPES =" — the hook types that a cloud session
  installs.
- `scripts/tests/test_gitleaks_hook.py` — a test that runs a hook in a temporary
  repository.
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#steps` › "Closing it
  is then a single edit" — the step that writes the evidence line today.
- `docs/knowledge/AGENTS.md` › "A ticked task carries the evidence that closed
  it" — the rule that the change replaces.
