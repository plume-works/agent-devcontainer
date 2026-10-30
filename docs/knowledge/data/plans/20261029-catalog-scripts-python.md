---
type: plan
created: 2026-10-29
release:
- bugs/git-new-branch-worktree-unwritable-workspaces
description: Port every bundled shell script in the agentdev catalog, its shared bin helpers, and the publisher's Super-Linter version check to stdlib-only Python behind unchanged RESULT contracts, with a test for each script and the skill-scripts contract rewritten Python-first.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T16:18:33Z
sources:
- resource: .agents/plugins/agentdev/bin/result_codes.py
- resource: .agents/plugins/agentdev/bin/result-codes.sh
- resource: .agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py
- resource: .agents/plugins/agentdev/skills/skill-scripts/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-new-branch/agent-code/__common.sh
- resource: .agents/AGENTS.md
- resource: .github/workflows/reformat.yml
- resource: scripts/validate-super-linter-tool-versions.sh
- resource: docs/knowledge/data/plans/20260905-python-skill-scripts.md
- resource: .agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py
---

# Port the catalog's bundled shell scripts to Python

## Context

The agentdev catalog ships 30 shell scripts under `skills/*/agent-code/` and 9
under `bin/`; 26 of the 39 are named by no test file. The publisher's
`scripts/validate-super-linter-tool-versions.sh` sources the catalog's
`bin/super-linter-defaults.sh`, so it belongs with that cluster. [Python skill
scripts](20260905-python-skill-scripts.md) ported the first catalog script,
added `bin/result_codes.py` as the Python `RESULT=` contract, and recorded the
constraint that binds every catalog script: it ships in the plugin cache of any
consuming repository and runs on whatever host runs the agent, so it is
stdlib-only on `#!/usr/bin/env python3` and reaches `bin/` through `sys.path`,
never through a repository-relative path. The skill scripts `stale-map-docs.py`
and `iwe-branch-name.py` already follow that pattern.

This is the companion of [Replace the runtime shell scripts with one
agentdev-runtime CLI](20261029-off-bash-migration.md), filed separately because
its verification story is the plugin test suite and per-script output baselines,
not an image build.

The port of the git workflow skills carries a fix first: [Bug: git-new-branch
worktree mode fails on a standalone deployment's root-owned
/workspaces](../bugs/git-new-branch-worktree-unwritable-workspaces.md) lands in
`git-new-branch.sh` as Task 3, so the port's baseline carries the corrected
worktree parent. The user chose the fix: under
`AGENTDEV_RUNTIME_MODE=standalone`, worktree mode always uses
`<checkout>/.worktrees/` as the parent.

## Approach

Port skill by skill behind an unchanged stdout contract: the `RESULT=` last
line, every `KEY=value` line, help on stdout, diagnostics on stderr, and the
exit codes. The `/agentdev:semantic-refactor-audit` skill captures each script's
baseline before the port and compares afterwards, which is the proof the plan
relies on where no test exists yet; every ported script also gains a test in
`.agents/plugins/agentdev/tests/` through the `plugin_root` fixture.

Shared code lives in `bin/` as importable modules beside `result_codes.py`: the
per-skill `__common.sh` helpers (repository check, main checkout directory, help
header) become one `bin/skill_common.py`, `git-default-branch.sh` and
`github-issue.sh` become modules with the same command-line entry points, and
the Super-Linter scripts become one module whose entry points print the same
environment lines the workflows append to `GITHUB_ENV`. Each skill's `SKILL.md`
and `allowed-tools` reference `agent-code/<name>.py`; the `agent-code/*` glob
already admits it. `bin/result-codes.sh` and the bash case of its test are
deleted when the last shell script leaves, and the skill-scripts skill is
rewritten Python-first in the same task.

The worktree-parent fix is the one behaviour change, and it lands in the shell
script on its own before any port, so the git-new-branch baseline the port is
compared against already holds it. The port then decides the parent in a
function of the main checkout path, the runtime mode, and `--worktree-root`, so
a test covers the `/workspaces` cases without a writable `/workspaces`.

Rejected: a Python package installed into the plugin, because a plugin cache has
no install step and `sys.path` to `bin/` is the mechanism the catalog already
relies on; bash wrappers around Python helpers, rejected by the earlier port for
splitting one algorithm across two languages; and porting without baselines,
which would make 26 untested scripts' behaviour a matter of reading.

## Implementation Steps

### Task 1: Shared helpers in bin

**Files:** Create: `.agents/plugins/agentdev/bin/skill_common.py`,
`.agents/plugins/agentdev/bin/git_default_branch.py`,
`.agents/plugins/agentdev/bin/github_issue.py`,
`.agents/plugins/agentdev/tests/test_skill_common.py`,
`.agents/plugins/agentdev/tests/test_git_default_branch.py`,
`.agents/plugins/agentdev/tests/test_github_issue.py`; Modify:
`.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py`,
`.agents/plugins/agentdev/tests/test_iwe_branch_name_parse.py`

- [x] The three modules reproduce the helpers the `__common.sh` files and the
  two bin scripts provide, importable through the `sys.path` pattern and
  runnable with the same arguments; `iwe-branch-name.py` calls the module
  instead of the shell helper.
  - **Evidence:** commit fa0f1cc "Add the shared Python skill helpers to the
    plugin's bin"; `uv run pytest .agents/plugins/agentdev/tests` passed (339),
    including the new `test_skill_common.py`, `test_git_default_branch.py`, and
    `test_github_issue.py` and the iwe-branch-name suites.

### Task 2: Super-Linter and lint helpers

**Files:** Create: `.agents/plugins/agentdev/bin/super_linter.py`,
`.agents/plugins/agentdev/bin/python_lint_check.py`,
`.agents/plugins/agentdev/bin/shellcheck_fix.py`,
`scripts/validate-super-linter-tool-versions.py`,
`.agents/plugins/agentdev/tests/test_super_linter.py`,
`scripts/tests/test_validate_super_linter_tool_versions.py`,
`.agents/plugins/agentdev/tests/test_lint_helpers.py`; Modify:
`.github/workflows/reformat.yml`, `AGENTS.md`,
`.agents/plugins/agentdev/README.md`,
`.agents/plugins/agentdev/agents/principal-engineer.agent.md`,
`.agents/plugins/agentdev/agents/tdd-refactor.agent.md`,
`py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py`,
`.agents/plugins/agentdev/skills/sync-super-linter-tool-versions/SKILL.md`,
`.agents/plugins/agentdev/skills/local-reformat/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`docs/knowledge/data/architecture/formatter-ownership.md`,
`docs/knowledge/data/architecture/template-boundary.md`; Delete:
`.agents/plugins/agentdev/bin/super-linter-defaults.sh`,
`.agents/plugins/agentdev/bin/super-linter-env.sh`,
`.agents/plugins/agentdev/bin/super-linter-local.sh`,
`.agents/plugins/agentdev/bin/python-lint-check.sh`,
`.agents/plugins/agentdev/bin/shellcheck-fix.sh`,
`.agents/plugins/agentdev/bin/__utils.sh`,
`scripts/validate-super-linter-tool-versions.sh`

- [x] `super_linter.py` holds the defaults and prints the same `GITHUB_ENV`
  lines for `env` and `env --autofix`, runs the local Super-Linter container for
  `local`, and the version check imports its defaults from it; the two workflow
  steps and the skills name the `.py` entry points.
  - **Evidence:** commit f7a14ff "Port the Super-Linter and lint helpers to
    Python";
    `uv run pytest .agents/plugins/agentdev/tests scripts/tests/test_validate_super_linter_tool_versions.py`
    passed (355), including `test_super_linter.py`, `test_lint_helpers.py`, and
    the validator's tests.

### Task 3: Standalone worktree parent

**Files:** Modify:
`.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.sh`,
`.agents/plugins/agentdev/skills/git-new-branch/SKILL.md`,
`.agents/plugins/agentdev/tests/test_git_new_branch.py`,
`docs/knowledge/data/bugs/git-new-branch-worktree-unwritable-workspaces.md`

- [ ] Under `AGENTDEV_RUNTIME_MODE=standalone`, worktree mode without
  `--worktree-root` uses `<main checkout>/.worktrees/`, added to
  `.git/info/exclude` unless Git already ignores it, wherever the checkout
  lives; the help text and the skill say so; a test runs the standalone case for
  a checkout outside `/workspaces`; the bug's `## Fix` records the fix.

### Task 4: Git workflow skills

**Files:** Create:
`.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py`,
`.agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.py`,
`.agents/plugins/agentdev/skills/git-merge-resolve/agent-code/git-merge-resolve.py`,
`.agents/plugins/agentdev/skills/git-commit/agent-code/git-commit.py`,
`.agents/plugins/agentdev/tests/test_git_merge_resolve.py`; Modify: the four
skills' `SKILL.md`, `.agents/plugins/agentdev/tests/test_git_new_branch.py`,
`.agents/plugins/agentdev/tests/test_update_branch.py`,
`.agents/plugins/agentdev/tests/test_git_commit.py`; Delete: the four `.sh`
scripts, the `__common.sh` of git-new-branch and update-branch, and
`.agents/plugins/agentdev/bin/git-default-branch.sh`, whose last consumers they
are

- [ ] Each script reproduces its `RESULT` table, `KEY=value` lines, options, and
  stash, worktree, and conflict handling; the merge-resolve script gains its
  first test.
- [ ] `git-new-branch.py` decides the worktree parent in a function of the main
  checkout path, the runtime mode, and `--worktree-root`; a test calls it for a
  checkout directly under `/workspaces` in standalone and in other modes, and
  replaces the test that skips without a writable `/workspaces`.

### Task 5: Pull-request skills

**Files:** Create:
`.agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py`,
`.agents/plugins/agentdev/skills/pr-open/agent-code/find-branch-pr.py`,
`.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py`,
`.agents/plugins/agentdev/skills/pr-review/agent-code/post-review.py`,
`.agents/plugins/agentdev/skills/pr-gen-description/agent-code/review-git-changes.py`,
`.agents/plugins/agentdev/tests/test_find_branch_pr.py`,
`.agents/plugins/agentdev/tests/test_post_review.py`,
`.agents/plugins/agentdev/tests/test_review_git_changes.py`; Modify: the four
skills' `SKILL.md`,
`.agents/plugins/agentdev/tests/test_push_branch_map_check.py`,
`.agents/plugins/agentdev/tests/test_request_review.py`; Delete: the five `.sh`
scripts and the `__common.sh` of pr-open, pr-review, and pr-gen-description

- [ ] Each script reproduces its contract; the three untested scripts gain tests
  covering their `RESULT` paths.

### Task 6: gh-stack guard

**Files:** Create:
`.agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.py`; Modify:
`.agents/plugins/agentdev/skills/gh-stack/SKILL.md`,
`.agents/plugins/agentdev/tests/test_gh_stack_guard.py`, `AGENTS.md`,
`docs/knowledge/data/product.md`; Delete:
`.agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.sh`

- [ ] `stack-guard.py` reproduces `begin` and `publish` with the leased push and
  every refusal; root `AGENTS.md` and `product.md` name `stack-guard.py` in the
  force-push exception.

### Task 7: IWE workflow skills

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.py`,
`.agents/plugins/agentdev/skills/iwe-explore/agent-code/fetch-issue.py`,
`.agents/plugins/agentdev/skills/iwe-plan/agent-code/close-issue.py`,
`.agents/plugins/agentdev/skills/iwe-capture/agent-code/close-issue.py`; Modify:
the four skills' `SKILL.md`,
`.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`.agents/plugins/agentdev/tests/test_iwe_bootstrap.py`,
`.agents/plugins/agentdev/tests/test_fetch_issue.py`,
`.agents/plugins/agentdev/tests/test_close_issue.py`,
`.agents/plugins/agentdev/tests/test_capture_close_issue.py`; Delete: the four
`.sh` scripts, the `__common.sh` of iwe-explore, iwe-plan, and iwe-capture, and
`.agents/plugins/agentdev/bin/github-issue.sh`, whose last consumers they are

- [ ] Each script reproduces its contract; the two close-issue entry points
  share `bin/github_issue.py` while staying separate files, since a skill never
  references a sibling's code.

### Task 8: Remote Codespace session

**Files:** Create:
`.agents/plugins/agentdev/skills/remote-codespace-session/agent-code/codespace-ensure.py`,
`.agents/plugins/agentdev/skills/remote-codespace-session/agent-code/codespace-sync.py`,
`.agents/plugins/agentdev/skills/remote-codespace-session/agent-code/codespace-teardown.py`,
`.agents/plugins/agentdev/skills/remote-codespace-session/agent-code/codespace-exec.py`,
`.agents/plugins/agentdev/skills/remote-codespace-session/agent-code/codespace_common.py`;
Modify: `.agents/plugins/agentdev/skills/remote-codespace-session/SKILL.md`,
`.agents/plugins/agentdev/tests/test_remote_codespace_session.py`; Delete: the
four `.sh` scripts and `__common.sh`

- [ ] The four entry points reproduce their contracts over one skill-local
  module; the test covers ensure, sync, and teardown as well as exec.

### Task 9: Template consumption and Actions log helpers

**Files:** Create:
`.agents/plugins/agentdev/skills/template-consume/agent-code/check-updates.py`,
`.agents/plugins/agentdev/skills/extract-github-actions-logs/agent-code/parse-actions-url.py`,
`.agents/plugins/agentdev/tests/test_parse_actions_url.py`; Modify: the two
skills' `SKILL.md`,
`.agents/plugins/agentdev/tests/test_template_consume_check_updates.py`; Delete:
the two `.sh` scripts and template-consume's `__common.sh`

- [ ] Both scripts reproduce their contracts; the URL parser gains its first
  test.

### Task 10: Retire the shell contract

**Files:** Modify: `.agents/plugins/agentdev/skills/skill-scripts/SKILL.md`,
`.agents/plugins/agentdev/tests/test_result_codes.py`, `.agents/AGENTS.md`;
Delete: `.agents/plugins/agentdev/bin/result-codes.sh`

- [ ] The skill-scripts skill documents the Python contract only:
  `result_codes.py`, the stdout and stderr rules, the `sys.path` import, the
  stdlib-only rule, and the `python3 -S` check; the bash test case leaves with
  the helper, and `git ls-files '.agents/**/*.sh'` prints nothing.

### Task 11: Record the constraint and refresh the map

**Files:** Create:
`docs/knowledge/data/architecture/catalog-script-language.md`; Modify:
`docs/knowledge/data/architecture.md`, `docs/knowledge/data/codebase/`

- [ ] The architecture document records why catalog scripts are stdlib-only
  Python reaching `bin/` through `sys.path`, and the rejected alternatives
  above; `/agentdev:iwe-map` refresh leaves no changed mapped source stale.

## Spec changes

Normative outcome for each: the specification SHALL name the `.py` script in
place of the `.sh` script it names today, and every requirement, `RESULT` name,
exit code, and scenario keeps its behaviour, except the git-new-branch worktree
requirement, whose delta is in its own entry below.

- [Git new branch](../spec/git-new-branch.md) — `git-new-branch.sh`,
  `git-commit.sh`, `git-default-branch.sh`

- [Git new branch](../spec/git-new-branch.md) — the worktree requirement changes
  for the standalone runtime (Task 3):

  ``` markdown
  ## MODIFIED Requirements

  ### Requirement: Worktree mode leaves the current checkout alone

  In worktree mode the git-new-branch skill SHALL create the branch in a new
  worktree named `<repo>-<branch>`, with any `/` in the branch kept as a directory
  separator, under the checkout's ignored `.worktrees/` directory when
  `AGENTDEV_RUNTIME_MODE` is `standalone`, otherwise under `/workspaces` when the
  main checkout lives there and under the checkout's ignored `.worktrees/`
  directory when it does not, and SHALL NOT change the current checkout.

  #### Scenario: Repository outside /workspaces

  - **WHEN** the main checkout is not directly under `/workspaces`
  - **THEN** the worktree is created under `<checkout>/.worktrees/` and that
    directory is ignored by Git

  #### Scenario: Standalone runtime

  - **WHEN** `AGENTDEV_RUNTIME_MODE` is `standalone`, whether or not the main
    checkout is directly under `/workspaces`
  - **THEN** the worktree is created under `<checkout>/.worktrees/` and that
    directory is ignored by Git

  #### Scenario: Branch names that differ only by `/` and `-`

  - **WHEN** worktrees for `feature/foo` and `feature-foo` are created under the
    same parent
  - **THEN** each gets its own directory
  ```

- [Update branch](../spec/update-branch.md) — `update-branch.sh`

- [IWE bootstrap](../spec/iwe-bootstrap.md) — `bootstrap-iwe.sh`

- [IWE workflow skills](../spec/iwe-workflow-skills.md) — `close-issue.sh`,
  `fetch-issue.sh`, `push-branch.sh`

- [Stacked PRs](../spec/stacked-prs.md) and [PR merge
  conflicts](../spec/pr-merge-conflicts.md) — `stack-guard.sh`

- [AI review refresh](../spec/ai-review-refresh.md) — `request-review.sh`

- [iwe-branch-name](../spec/iwe-branch-name.md) — `git-default-branch.sh`

- [Template consumption](../spec/template-consumption.md) — `check-updates.sh`,
  `scripts/validate-super-linter-tool-versions.sh`

## Verification

- `uv run pytest .agents/plugins/agentdev/tests`
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- For every ported script, a `/agentdev:semantic-refactor-audit` baseline
  captured before the port matches the port's output
- `for f in $(git ls-files '.agents/plugins/agentdev/bin/*.py' '.agents/plugins/agentdev/skills/*/agent-code/*.py'); do python3 -S "$f" --help >/dev/null; done`
  succeeds, proving every script runs on the standard library alone
- `uv run ruff check .agents scripts`
- `git ls-files '.agents/**/*.sh' 'scripts/validate-super-linter-tool-versions.sh'`
  prints nothing
- `uv run pytest scripts/tests/test_validate_super_linter_tool_versions.py`
- The reformat workflow passes on the current head with the `.py` entry points
- `iwe normalize`, `iwe schema validate`, the knowledge-base tests, and an
  `/agentdev:iwe-map` refresh with no stale mapped source

## Out of scope

- The runtime, docker, and publisher scripts of [Replace the runtime shell
  scripts with one agentdev-runtime CLI](20261029-off-bash-migration.md).
- The self-improve plugin's `agent-code/si` launcher and `docker/bin/gh`.
- Any change to a `RESULT` vocabulary, exit code, option, or output line.
- Installing the catalog's helpers as a package.

## Key references

Verified anchor points (line numbers as of 2026-10-30):

- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:22` —
  `sys.path` to `bin/`
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py:191`
  — `remote_default_branch`, which calls the `bin/git_default_branch.py` module
- `.agents/plugins/agentdev/skills/git-new-branch/agent-code/__common.sh:13` —
  shell equivalent
- `.agents/plugins/agentdev/bin/result-codes.sh:43` — `quit_by_code`
- `.agents/plugins/agentdev/bin/result-codes.sh:62` — `report_signal`
- `.agents/plugins/agentdev/bin/result_codes.py:49` — Python `quit_by_code`
- `.agents/plugins/agentdev/tests/test_result_codes.py:13` — bash contract test
  to retire
- `.agents/plugins/agentdev/tests/test_result_codes.py:71` — Python contract
  test
- `.agents/plugins/agentdev/tests/conftest.py:23` — `plugin_root`
- `.agents/plugins/agentdev/skills/skill-scripts/SKILL.md:92` — shell helper
  instructions
- `.agents/plugins/agentdev/skills/gh-stack/SKILL.md:34` — `stack-guard.sh` link
- `.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.sh:211`
  — the `/workspaces` worktree-parent default Task 3 fixes
- `.agents/plugins/agentdev/tests/test_git_new_branch.py:581` — the test that
  skips without a writable `/workspaces`
- `docs/knowledge/data/spec/git-new-branch.md:97` — the worktree requirement
- `.agents/plugins/agentdev/skills/git-new-branch/SKILL.md:51` —
  `git-new-branch.sh` link
- `.github/workflows/reformat.yml:207` — `super_linter.py env --autofix`
- `.github/workflows/reformat.yml:246` — `super_linter.py env`
- `.github/workflows/reformat.yml:269` —
  `validate-super-linter-tool-versions.py`
- `.agents/plugins/agentdev/skills/local-reformat/SKILL.md:34` —
  `super_linter.py` link
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md:152` — `close-issue.sh`
  in the rulebook
- `AGENTS.md:7` — force-push exception naming `stack-guard.sh`
- `docs/knowledge/data/product.md:132` — the same exception
