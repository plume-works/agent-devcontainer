---
type: plan
created: 2026-11-15
release: internal
description: Move the evidence of a ticked plan task into the message of the commit that ticks it. Each commit has one tick and one completion evidence block.
sources:
- resource: docs/knowledge/data/archive/next-release/adr/0086-plan-ticks-need-evidence-lines.md
- resource: docs/knowledge/tests/test_plan_checkboxes.py
stage: done
completed: 2026-11-16
---

# Put task evidence in the commit message

## Context

[Plan tasks evidence and ADRs as git
history](../backlog/plan-evidence-and-decisions-in-git-history.md) asks for the
evidence of a plan task in the commit that ticks it. The commit then connects
the tick, the code change, and the reason of the agent at that time. `git log`
and `git blame` find the evidence from the code.

[ADR-0086](../adr/0086-plan-ticks-need-evidence-lines.md) puts the evidence of
each ticked task in a `- **Evidence:**` line in the plan. Only the
`plan-checkboxes` check reads that line, and the catalog agents that review a
plan do not examine it.

## Approach

The Implement session ticks one plan task in a commit and writes a completion
evidence block in the commit message. The diff shows which plan task the commit
ticks, so the block names no task. One script, `scripts/completion-evidence.py`,
has three subcommands:

- `check-message` runs as a `commit-msg` hook. It reads the staged diff of
  `docs/knowledge/data/plans/` and the message file.
- `check-push` runs as a `pre-push` hook. It reads the commits that the push
  sends, from `PRE_COMMIT_FROM_REF` to `PRE_COMMIT_TO_REF`.
- `show` prints the ticked plan task and the block of each commit of a pull
  request from `refs/pull/<N>/head`. These commits stay there after the squash
  merge.

A tick is the change of a line `- [ ] <text>` to `- [x] <text>` in a file under
`docs/knowledge/data/plans/`. The two hooks apply two rules to a commit that
ticks a plan task. The commit ticks only one plan task. The message has one
completion evidence block that contains text.

The block starts at a line `---` that a line `completion evidence:` follows, and
it continues to the end of the message. Git trailer lines at the end of the
message, such as `Co-Authored-By:`, are not text of the block. The hooks do not
examine a merge commit, because a merge commit moves ticks from other commits.

`check-message` compares the index with `HEAD`. During an amend, `HEAD` is the
commit that the amend replaces, so `check-message` sees only the change that the
amend adds. `check-push` compares each pushed commit with its parent through
`git diff-tree`, so it also examines an amended commit. A hook never reads the
command line of a Git command.

A push with `--no-verify` does not run `check-push`, and `show` then prints no
evidence for a tick that has no block. The `plan-checkboxes` check keeps only
the rule that a plan at `stage: done` has no unticked task.

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

- [x] `check-message <message-file>` exits 0 for a staged tick of one plan task
  with a block, and the test passes.
- [x] `check-message` exits 1 and names the plan task for a staged tick with no
  block, and the test passes.
- [x] `check-message` exits 1 and names the plan task for a staged tick with an
  empty block, and the test passes.
- [x] `check-message` exits 1 for a staged tick of two plan tasks, and the test
  passes.
- [x] `check-message` exits 0 for a commit that ticks no plan task, and the test
  passes.
- [x] `check-message` exits 0 while a merge is in progress (`MERGE_HEAD` exists)
  in the fixture repository, and the test passes.

### Task 2: Show the evidence of a pull request

**Files:** Modify: `scripts/completion-evidence.py`,
`scripts/tests/test_completion_evidence.py`

`show <N>` fetches `refs/pull/<N>/head` and `main` from `origin`. It prints the
ticked plan task and the block of each commit that is not a merge commit and
that is not on `main`. The test uses a bare fixture repository as `origin`.

- [x] For a pull request whose branch merged `main` one time, `show <N>` prints
  each ticked plan task with its block, oldest first. The test passes.

### Task 3: Run the check at commit time

**Files:** Modify: `.pre-commit-config.yaml`,
`py_packages/agentdev_runtime/agentdev_runtime/project.py`, `.claude/startup.py`

- [x] `.pre-commit-config.yaml` has a local hook `completion-evidence` at
  `stages: [commit-msg]` that runs `check-message`. In this checkout, the hook
  stops a commit that has a tick and no block.
- [x] `HOOK_TYPES` in `py_packages/agentdev_runtime/agentdev_runtime/project.py`
  and in `.claude/startup.py` has `commit-msg`, and
  `uv run pytest scripts/tests/test_agent_runtime_workspace.py scripts/tests/test_cloud_startup.py`
  passes.

### Task 4: Remove the evidence-line rule from the `plan-checkboxes` check

**Files:** Modify: `docs/knowledge/tests/test_plan_checkboxes.py`

- [x] The check has no evidence-line rule, and the change removes the tests of
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
`docs/knowledge/schema/plans.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/schema/plans.md`

- [x] Step 6, step 8, and the rules of `iwe-implementer.agent.md` tell the
  Implement session to tick one plan task in a commit. They also tell it to
  write the block in the commit message. They show the block format of Task 1 as
  a fenced block.
- [x] `iwe-planner.agent.md` step 4, `plan-rules.md`, `iwe-verifier.agent.md`,
  `iwe-plan-reviewer.agent.md`, and `iwe-audit/SKILL.md` name the completion
  evidence block, and
  `rg -n 'Evidence:\*\*|evidence line' .agents/plugins/agentdev/agents/iwe-implementer.agent.md .agents/plugins/agentdev/agents/iwe-planner.agent.md .agents/plugins/agentdev/agents/iwe-verifier.agent.md .agents/plugins/agentdev/agents/iwe-plan-reviewer.agent.md .agents/plugins/agentdev/skills/iwe-plan-review/references/plan-rules.md .agents/plugins/agentdev/skills/iwe-audit/SKILL.md`
  prints nothing.
- [x] `pr-gen-description/SKILL.md` Step 5 says that the commits of the pull
  request contain the task evidence.
- [x] Both copies of `docs/knowledge/schema/plans.md` define the completion
  evidence block in place of the indented `- **Evidence:**` item. Both copies of
  `docs/knowledge/AGENTS.md` replace the evidence-line rule with the
  commit-message rule. `diff` of the two copies of each file prints nothing.
- [x] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.

### Task 6: Examine the commits of the pull request of this plan

**Closed by:** the Implement session of this plan, after it opens the pull
request of this plan.

- [x] Run `scripts/completion-evidence.py show <N>` for the pull request of this
  plan. For each commit that ticks a plan task of Tasks 1 to 5, it prints one
  ticked plan task and one completion evidence block.

### Task 7: Check the commits of a push

**Files:** Modify: `scripts/completion-evidence.py`,
`scripts/tests/test_completion_evidence.py`, `.pre-commit-config.yaml`

- [x] `check-push` exits 1 for a pushed commit that ticks a plan task with no
  block. It names the commit and the plan task, and the test passes.
- [x] `check-push` exits 1 for a pushed commit that an amend made and that ticks
  two plan tasks, and the test passes.
- [x] `check-push` exits 0 for a pushed range whose commits tick one plan task
  at most, each with a block, and that has a merge commit. The test passes.
- [x] `.pre-commit-config.yaml` has a local hook `completion-evidence-push` at
  `stages: [pre-push]` that runs `check-push`. In this checkout, the hook stops
  `git push` of a local commit that has a tick and no block.
- [x] `check-message` compares the index with `HEAD`. The change removes
  `amending()` from `scripts/completion-evidence.py`, and
  `rg -n '/proc' scripts/completion-evidence.py` prints nothing.

## Acceptance

### Scenario: A tick with a block passes the `commit-msg` hook

- **WHEN** a commit ticks one plan task and its message has a completion
  evidence block with text
- **THEN** `check-message` exits 0
- **Test:**
  `scripts/tests/test_completion_evidence.py::test_one_tick_with_block_passes`

### Scenario: A tick with no block fails the `commit-msg` hook

- **WHEN** a commit ticks one plan task and its message has no block, or a block
  with no text
- **THEN** `check-message` exits 1 and names the plan task
- **Test:**
  `scripts/tests/test_completion_evidence.py::test_tick_without_block_fails`

### Scenario: Two ticks in one commit fail

- **WHEN** the staged change of a commit ticks two plan tasks
- **THEN** `check-message` exits 1. During an amend, `check-message` examines
  only the change that the amend adds
- **Test:** `scripts/tests/test_completion_evidence.py::test_two_ticks_fail`

### Scenario: A block is not necessary for a commit with no tick

- **WHEN** a commit ticks no plan task
- **THEN** `check-message` exits 0 for any message
- **Test:**
  `scripts/tests/test_completion_evidence.py::test_no_tick_needs_no_block`

### Scenario: `check-message` does not examine a merge commit

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

### Scenario: The `pre-push` hook stops a pushed tick with no block

- **WHEN** a push sends a commit that ticks one plan task and its message has no
  completion evidence block
- **THEN** `check-push` exits 1 and names the commit and the plan task
- **Test:**
  `scripts/tests/test_completion_evidence.py::test_push_tick_without_block_fails`

### Scenario: The `pre-push` hook stops an amended commit with two ticks

- **WHEN** an amend makes a commit that ticks two plan tasks, and a push sends
  it
- **THEN** `check-push` exits 1
- **Test:**
  `scripts/tests/test_completion_evidence.py::test_push_amended_two_ticks_fail`

### Scenario: The `pre-push` hook passes correct commits and merge commits

- **WHEN** a push sends commits that each tick one plan task at most with a
  block, and a merge commit
- **THEN** `check-push` exits 0
- **Test:**
  `scripts/tests/test_completion_evidence.py::test_push_valid_range_passes`

### Scenario: The Implement session writes evidence in the commit message

- **WHEN** the Implement session completes a plan task
- **THEN** `iwe-implementer.agent.md` tells it to tick one plan task in a commit
  and to write the completion evidence block in the message of that commit.
  `iwe-implementer.agent.md` tells the Implement session to write no evidence
  line in the plan
- **Checked at ship:**
  `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

## ADRs

[The commit that ticks a plan task contains its
evidence](../../../adr/0093-completion-evidence-in-the-commit-message.md)

## Verification

``` bash
uv run pytest scripts/tests/test_completion_evidence.py
uv run pytest docs/knowledge/tests/test_plan_checkboxes.py
uv run pytest scripts/tests/test_agent_runtime_workspace.py scripts/tests/test_cloud_startup.py
uv run validate_agent_files --recommend . --require-marketplace claude
diff docs/knowledge/AGENTS.md .agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/AGENTS.md
diff docs/knowledge/schema/plans.md .agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/schema/plans.md
```

## Out of scope

- A change to the evidence lines of closed or archived plans. They stay as they
  are.
- A check in a consumer. The catalog rules tell the Implement session what to
  write. The hook is in this repository only.
- A check of the text in a block. The hook examines only the format of the
  block.
- A check that the installed plugin cache of a consumer has the new rules.
- A CI check of the commits of a pull request. Only a change to pushed commits
  can correct a failure of that check.
- The `## Decisions` section of the pull request body, and the sequence of
  sources that an agent reads to find an answer. [Put decisions in the git
  history](../../../plans/20261115-decisions-in-git-history.md) changes them.
- The `**Evidence:**` items of the `## Verification` section of a pull request
  body in `/agentdev:code-review-standards`. That section is not a plan.
- The `- **Evidence:**` lines of the progress document of
  `/agentdev:template-consume`. That document is not a plan.

## Key references

- `docs/knowledge/tests/test_plan_checkboxes.py::check_plan` — the
  `plan-checkboxes` check.
- `.pre-commit-config.yaml#repos` › "id: plan-checkboxes" — the hook of the
  `plan-checkboxes` check, and the place of the new hook.
- `py_packages/agentdev_runtime/agentdev_runtime/project.py` › "HOOK_TYPES =" —
  the hook types that the runtime installs.
- `.claude/startup.py` › "HOOK_TYPES =" — the hook types that a cloud session
  installs.
- `scripts/tests/test_gitleaks_hook.py` — a test that runs a hook in a temporary
  repository.
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#steps` › "Then close
  the task with one edit" — the step that ticks one plan task and writes the
  completion evidence block in the commit message.
- `docs/knowledge/schema/plans.md` › "Its message ends with the completion
  evidence block" — the definition of the completion evidence block.
- `docs/knowledge/AGENTS.md#conventions` › "A tick and the code are in one
  commit" — the commit-message rule.
