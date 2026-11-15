---
type: plan
created: 2026-11-13
release: internal
description: Add a test for each behaviour that only a spec states, move the last spec text to its home, and delete data/spec/ with its schema, its hub, and every reference to it.
sources:
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: .iwe/config.toml
stage: done
completed: 2026-11-15
---

# Add the missing tests and delete the specs

## Context

The requirements that stay in `data/spec/` have one of three labels from [the
spec usefulness audit](../../../findings/spec-usefulness-audit.md): `needs-test`
(18), `user-doc` (2), or `no-home` (3). The labels were in
`docs/spec-audit/requirements.jsonl`, which Task 5 deletes. Each `needs-test`
row had a `fate_note` that said what the test must show.

This plan is the last step of [Shrink the knowledge base to an issue tracker and
decision records](../backlog/shrink-knowledge-base-to-issues-and-adrs.md). After
it, the repository has no spec.

## Approach

Each `needs-test` requirement has a test that runs the behaviour, as the test
rules in `AGENTS.md#tests` tell you to do. Five of the 18 are decisions in
workflow files, and [Test the decisions that the workflows
make](20261113-test-the-workflow-decisions.md) adds their tests. This plan adds
tests for 7 of the other 13. The 5 other requirements have no test, because each
one is configuration, a rule, or a guard against a possible future edit, and not
logic. The last one is [a deploy runtime that reuses a checkout does not
configure the git credential
helper](../../../bugs/reused-checkout-gets-no-credential-helper.md).

The 2 `user-doc` requirements are in a README already. The requirement about the
GitHub ruleset goes to the consumption guide of the `template-consume` skill.
Each consumer sets the ruleset in the settings of its repository. The 2 other
`no-home` requirements are bugs about the consumption guide.

Then Task 3 deletes `data/spec/` and each thing that exists only for it. The
glossary loses each term that no prose uses after the specs are gone. Task 5
deletes the audit data in `docs/spec-audit/` last, because each plan in the
series reads it.

The plan also changes code in two places. The `end-of-file-fixer` and
`trailing-whitespace` hooks use the default stages, so a merge commit runs them.
This change is the fix for [a merge commit skips `end-of-file-fixer` and
`trailing-whitespace`](../bugs/merge-commit-skips-two-hooks.md). The `gh`
wrapper loses three things. It does not use `/usr/bin/gh` when `PATH` has no
other `gh`. It has no `GH_WRAPPER_ACTIVE` guard. It has no code that ignores a
second copy of the wrapper. Only the image installs the wrapper, so `PATH` holds
one copy, and the wrapper uses the first `gh` on `PATH` that is not itself.

## Implementation Steps

### Task 1: Add the missing tests

**Files:** Create and Modify: the test files that each `fate_note` names

Each test shows what the `fate_note` of its row says.

- [x] A test runs `agent-file-discovery` "Git failures do not abort discovery".
  - **Evidence:**
    `py_packages/validate_agent_files/tests/test_gitignore_discovery.py` runs
    discovery with a `git` whose `check-ignore` command fails, and with no `git`
    on `PATH`. 21 tests pass.
- [x] A test runs `agentdev-runtime-images` "image builds contact no Launchpad
  host".
  - **Evidence:** `scripts/tests/test_cache_git_ppa_release.py` runs the script
    with a test PPA that a local key signs. The script publishes a release with
    `--latest=false` and replaces nothing. It publishes nothing for an incorrect
    key or an incorrect hash chain. 5 tests pass.
- [x] A test runs `agentdev-runtime-images` "the bootstrap trusts an extra CA
  bundle".
  - **Evidence:** `scripts/tests/test_devcontainer_init.py` runs the init script
    for five cases. No CA gives an empty `.extra-ca.crt`. The named bundle has
    priority over the Node bundle. The script uses the Node bundle when no
    bundle has a name. The script skips a Node bundle that it cannot read, and
    exits 1 when it cannot read the named bundle. 7 tests pass.
- [x] A test runs `catalog-lifecycle` "registering a catalog root replaces
  earlier registrations".
  - **Evidence:**
    `py_packages/agentdev_runtime/tests/test_catalog_claude_register.py` runs
    `catalog.claude` with a `claude` stub that records each call. Before it adds
    the marketplace, `catalog.claude` removes each marketplace from the same
    root in every scope. An absent plugin does not stop it. When the add command
    fails, `catalog.claude` stops with an error. 3 tests pass.
- [x] A test runs `devcontainer-git-credentials` "gh authenticates from the git
  credential helper".
  - **Evidence:** `scripts/tests/test_gh_wrapper.py` runs the gh wrapper with a
    substitute for the real gh and a real git credential helper. It covers the
    helper token, no helper, and a set token. It also covers exit 127 when
    `PATH` has no real gh. 4 tests pass.
- [x] A test runs `devcontainer-state` "the create phase re-owns the sibling
  checkout volume".
  - **Evidence:** The Docker tests in
    `scripts/tests/test_agentdev_devcontainer_lifecycle.py` cover how the create
    phase claims the volume, a volume that the runtime account owns, and the
    open workspace. `py_packages/agentdev_runtime/tests/test_claim_project.py`
    adds a case for a root account and a case with no mount. 2 tests pass.
- [x] A test runs `update-branch` "update-branch brings in the branch's upstream
  before the base" for a branch that has no upstream.
  - **Evidence:** `.agents/plugins/agentdev/tests/test_update_branch.py` adds
    three cases: a branch with no upstream (`untracked`), a failed `ls-remote`
    (`FETCH_FAILED`, not `gone`), and a local upstream (`remote = .`). 14 tests
    pass.

### Task 2: Move the last spec text to its home

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`AGENTS.md`

- [x] `ansible/roles/playwright_browser/README.md` says that the Playwright
  dependencies of a project stay with the project.
  - **Evidence:** `ansible/roles/playwright_browser/README.md` already says that
    "a project-owned Playwright" can install its browser. Task 2 made no edit.
- [x] `README.md` gives the scope of the standalone OpenCode image.
  - **Evidence:** `README.md#standalone-opencode-runtime` already gives the
    scope of the image. Task 2 made no edit.
- [x] The consumption guide of the `template-consume` skill gives the GitHub
  ruleset that blocks a merge into the head branch of a dependent pull request.
  It tells how to set the ruleset.
  - **Evidence:** `consumption-guide.md#the-ruleset-on-dependent-branches` gives
    the rule and the `gh api` call. This text is a copy of the ruleset that is
    in use. Workflow B has a link to it.
- [x] The rule about stacked pull requests in `AGENTS.md` links no spec.
  - **Evidence:** The rule already links
    `adr/0068-stack-dependent-work-with-merges-only.md`. Task 2 made no edit.

### Task 3: Delete `data/spec/` and what exists only for it

**Files:** Delete: `docs/knowledge/data/spec/`, `docs/knowledge/data/spec.md`,
`.iwe/schemas/spec.yaml`, and their copies under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/`; Modify:
`.iwe/config.toml`, `docs/knowledge/data/index.md`, `docs/knowledge/SCHEMA.md`,
`docs/knowledge/STRUCTURE.md`, `docs/knowledge/AGENTS.md`,
`docs/knowledge/README.md`, `README.md`,
`.agents/plugins/agentdev/skills/iwe-audit/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`, and the scaffold copies

- [x] `docs/knowledge/data/spec/` and `docs/knowledge/data/spec.md` do not
  exist.
  - **Evidence:** `iwe delete` removed the 15 specs and the hub, and removed the
    links from 93 documents.
- [x] `.iwe/config.toml` has no `[schemas.spec]`, and
  `.iwe/config.toml#schemas.hub` does not match `data/spec`.
  - **Evidence:** Both entries are gone from `.iwe/config.toml`;
    `iwe schema validate` passes.
- [x] `.iwe/schemas/spec.yaml` does not exist.
  - **Evidence:** `git rm` removed the schema.
- [x] `docs/knowledge/data/index.md#reference` has no link to a spec hub.
  - **Evidence:** The Spec item is gone from `data/index.md`.
- [x] `docs/knowledge/SCHEMA.md`, `docs/knowledge/STRUCTURE.md`,
  `docs/knowledge/AGENTS.md`, and `docs/knowledge/README.md` describe no spec
  type and no spec folder.
  - **Evidence:** The spec type, folder, and rule are gone from `SCHEMA.md`,
    `STRUCTURE.md`, and `AGENTS.md`; `README.md` names only OpenSpec.
- [x] `README.md` links no spec.
  - **Evidence:** `grep data/spec README.md` already finds nothing. Task 3 made
    no edit.
- [x] No skill and no agent rulebook under `.agents/plugins/agentdev/` names
  `data/spec/`.
  - **Evidence:** `iwe-audit/SKILL.md` no longer names `data/spec/`;
    `grep -rn data/spec .agents/` finds nothing.
- [x] No docstring and no comment outside `docs/` names a spec.
  - **Evidence:** The spec fixture and its docstring are gone from
    `test_check_anchors.py`. The other uses of the word "spec" name the research
    documents of self-improve or the archived Ship review items.
- [x] The scaffold under the `iwe-bootstrap` assets has no spec hub and no spec
  schema. Its support files are the same as the files of the workspace.
  - **Evidence:** The scaffold lost `spec.md`, `spec.yaml`, its config entries,
    and its index item. The 6 tests in `test_iwe_seed.py` pass.
- [x] No document outside `data/archive/` links a spec.
  - **Evidence:** No link and no `sources` entry outside `data/archive/` names a
    spec file. `check-anchors` passes, and `docs/research` and
    `docs/user-stories` lost their spec links.

### Task 4: Prune the glossary

**Files:** Modify: `docs/knowledge/data/glossary.md`

- [x] Prose outside `data/archive/` uses each term in the glossary.
  - **Evidence:** A `git grep` of each term and its word forms outside
    `data/archive/` found 12 terms with no use. Task 4 removed them. The `spec`
    entry names the removed folder.

### Task 5: Delete the audit data

**Files:** Delete: `docs/spec-audit/`; Modify:
`docs/knowledge/data/findings/spec-usefulness-audit.md`

- [x] `docs/spec-audit/` does not exist.
  - **Evidence:** `git rm -r docs/spec-audit` removed the folder. The 14 bugs
    that named `requirements.jsonl` in `sources` do not name it now.
- [x] `findings/spec-usefulness-audit` names no file under `docs/spec-audit/`.
  - **Evidence:** The finding removes the two `sources` entries and says that
    the git history keeps the rows. `check-anchors` passes.

### Task 6: Close the backlog task

**Files:** Modify:
`docs/knowledge/data/backlog/shrink-knowledge-base-to-issues-and-adrs.md`,
`docs/knowledge/data/backlog.md`

- [x] `backlog/shrink-knowledge-base-to-issues-and-adrs` is at `stage: done`
  with `completed`, is in `data/archive/next-release/backlog/`, and has no link
  in `data/backlog.md`.
  - **Evidence:** `iwe update` set `stage: done` and `completed: 2026-11-15`.
    `iwe rename` moved the task to `data/archive/next-release/backlog/`. Task 6
    removed its link from `data/backlog.md`. `check-ship-records` passes.

### Task 7: Run the end-of-file and whitespace hooks on a merge commit

**Files:** Modify: `.pre-commit-config.yaml`,
`docs/knowledge/data/archive/next-release/bugs/merge-commit-skips-two-hooks.md`

- [x] The `end-of-file-fixer` and `trailing-whitespace` hooks in
  `.pre-commit-config.yaml` set no `stages`.
  - **Evidence:** Commit `6e89bf34` removed the `stages` line of each hook. The
    hook entries in `.pre-commit-config.yaml` now have no `stages` key.
- [x] `bugs/merge-commit-skips-two-hooks` is at `stage: done` with a `## Fix`,
  in `data/archive/next-release/bugs/`, and has no link in `data/bugs.md`.
  - **Evidence:** The bug is at `stage: done` with a `## Fix` in
    `data/archive/next-release/bugs/`, and `data/bugs.md` has no link to it.

### Task 8: Simplify the gh wrapper

**Files:** Modify: `ansible/roles/github_cli/files/gh`

- [x] `ansible/roles/github_cli/files/gh` does not use `/usr/bin/gh` when `PATH`
  has no other `gh`. It has no `GH_WRAPPER_ACTIVE` guard and no code that
  ignores a second copy of the wrapper.
  - **Evidence:** Commit `9410c8ed` removed the three parts. `grep` finds no
    `/usr/bin/gh` and no `GH_WRAPPER_ACTIVE` in the wrapper, `shellcheck`
    passes, and the 4 tests in `scripts/tests/test_gh_wrapper.py` pass.

## Acceptance

### Scenario: A merge commit runs the end-of-file and whitespace hooks

- **WHEN** git makes a merge commit with no conflict, so the `pre-merge-commit`
  stage runs
- **THEN** that stage runs `end-of-file-fixer` and `trailing-whitespace`
- **Checked at ship:** `.pre-commit-config.yaml` — the hooks
  `id: end-of-file-fixer` and `id: trailing-whitespace` set no `stages`, and
  `default_stages` includes `pre-merge-commit`

### Scenario: The gh wrapper with no real gh on PATH exits 127

- **WHEN** the `gh` wrapper runs and no `gh` on `PATH` is other than the
  wrapper, also when `/usr/bin/gh` exists
- **THEN** the wrapper writes "real gh not found on PATH" and exits 127
- **Test:**
  `scripts/tests/test_gh_wrapper.py::test_with_no_real_gh_on_path_the_wrapper_exits_127`

## Depends on

[Move the decisions from the specs into
ADRs](20261113-move-decisions-into-adrs.md)

[Make ASD-STE100 the rule for all prose](20261113-ste100-prose-rule.md)

[Test the decisions that the workflows
make](20261113-test-the-workflow-decisions.md)

## Verification

``` bash
iwe normalize && iwe schema validate
uv run scripts/check-anchors.py
uv run pytest docs/knowledge/tests
uv run pytest .agents/plugins/agentdev/tests/test_iwe_seed.py
uv run validate_agent_files --recommend . --require-marketplace claude
```

## Out of scope

- A fix for a defect that a new test finds. `/agentdev:iwe-capture bug` files
  it.
- The text of the archived documents and their `## Spec changes` sections.
  `iwe delete` removes only their links to a deleted spec.

## Key references

- `AGENTS.md#tests` — the rules that each new test follows.
- `.iwe/config.toml#schemas.hub` — the hub entry that loses `data/spec`.
- `.pre-commit-config.yaml#default_stages` — the stages that the two hooks use.
- `ansible/roles/github_cli/files/gh` — the wrapper that finds the real `gh`.
- `docs/knowledge/data/index.md#reference` — the section that links the spec
  hub.
- `.agents/plugins/agentdev/tests/test_iwe_seed.py::test_scaffold_support_files_match_the_publisher_workspace`
  — the test that compares the scaffold with the workspace.
