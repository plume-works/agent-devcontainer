---
type: plan
created: 2026-11-13
release: internal
description: File a bug for each guarantee that the code does not deliver. Then remove each spec requirement that a test, a rulebook, or clear code already states. Correct or remove the spec text that is wrong.
sources:
- resource: docs/spec-audit/requirements.jsonl
- resource: docs/spec-audit/rationale.jsonl
- resource: docs/spec-audit/README.md
stage: done
completed: 2026-11-14
---

# Remove the spec text that is redundant or wrong

## Context

[The spec usefulness audit](../../../findings/spec-usefulness-audit.md) gave a
label to each of the 264 requirements in `data/spec/`. 207 of them repeat a
test, a rulebook, or code that is clear. 34 are not fully true. The code does
not agree with 4 `## Rationale` entries. The labels are in `docs/spec-audit/`.

This plan is the first removal step of [Shrink the knowledge base to an issue
tracker and decision
records](../../../backlog/shrink-knowledge-base-to-issues-and-adrs.md). It
removes only the text that the audit already shows is not necessary or is wrong.

The repository owner's decisions:

- Before you remove the text of a guarantee that the code does not deliver, file
  a bug for it. Later, the bug can close as a guarantee that the project does
  not keep.
- After you file the bug, you can remove the requirement text with no other
  condition.

## Approach

The `fate` field in `docs/spec-audit/requirements.jsonl` decides what to do with
a requirement:

- `drop-tested`, `drop-prose-duplicate`, `drop-restates`: remove the requirement
  and its scenarios.
- Any other fate: the requirement stays for the later work. If it is not fully
  true, correct its text so that it agrees with the code.

The audit data describes commit `c81efa7e`. Before you remove or correct a
requirement that changed after that commit, compare it with the code again.

A `## Rationale` section stays, except for the 4 entries that the code does not
agree with. Remove each spec that has no requirement and no `## Rationale`
entry.

## Implementation Steps

### Task 1: File a bug for each guarantee that the code does not deliver

**Files:** Create: one document under `docs/knowledge/data/bugs/` for each bug;
Modify: `docs/knowledge/data/bugs.md`

File each bug with `/agentdev:iwe-capture bug`. Its evidence is the entry in
`data/findings/spec-usefulness-audit#requirements-that-are-not-fully-true` and
the row in `docs/spec-audit/requirements.jsonl`.

- [x] A bug records `agentdev-runtime-images` "the runtime is one CLI installed
  as a uv tool": two dependencies are ranges.
  - **Evidence:** Filed `data/bugs/runtime-dependencies-not-pinned`; the ranges
    are in `py_packages/agentdev_runtime/pyproject.toml#project.dependencies`.
- [x] A bug records `firewall` "enabled firewall default-DROPs IPv4 and blocks
  IPv6 entirely": IPv6 stays open when `ip6tables` is missing.
  - **Evidence:** Filed `data/bugs/firewall-ipv6-open-without-ip6tables`; read
    `firewall.py::block_ipv6`, which returns after the warning.
- [x] A bug records `pre-commit-gate` "every commit path runs the hooks, merges
  included": two hooks do not include the `pre-merge-commit` stage.
  - **Evidence:** Filed `data/bugs/merge-commit-skips-two-hooks`; both hooks
    still set `stages: [pre-commit, pre-push, manual]`.
- [x] A bug records `image-pinning` "published tags name only tested images":
  the `ubuntu-ansible` image has no revision label.
  - **Evidence:** Filed `data/bugs/ubuntu-ansible-tags-can-move-backwards`;
    `stable-labels: 'true'` and `select-labels.sh` still remove the label.
- [x] A bug records `standalone-opencode-runtime` "startup prepares or reuses
  one workspace": a reused checkout has no credential helper.
  - **Evidence:** Filed `data/bugs/reused-checkout-gets-no-credential-helper`;
    only `Workspace.clone` calls `git.credential_helper` in the deploy profile.
- [x] A bug records `devcontainer-git-credentials` "HTTPS git uses the gh
  login": the Coder start does not wait for the keyring session.
  - **Evidence:** Filed `data/bugs/coder-start-does-not-wait-for-keyring`;
    `coder.py::start` runs its steps with no wait.
- [x] A bug records `devcontainer-state` "the home volume starts empty and the
  bootstrap claims it": the `fish_setup` role writes into the build user's home.
  - **Evidence:** Filed `data/bugs/fish-path-setup-in-build-user-home`; the
    role's `dev.fish` destination is still `{{ user_home }}`.
- [x] A bug records `devcontainer-state` "root-only tests run through a
  launcher": the guard for unmarked tests cannot operate.
  - **Evidence:** Filed `data/bugs/root-test-guard-cannot-fire`;
    `scripts/run-root-tests` still passes `-m requires_root`.
- [x] A bug records `dependency-updates` "derived files are regenerated with the
  bump": the file filters omit one lock file.
  - **Evidence:** Filed `data/bugs/renovate-file-filters-omit-runtime-lock`;
    `fileFilters` still lists only the root `uv.lock`.
- [x] A bug records `catalog-scripts` "command lines handed to a shell are
  quoted by bash_quote": one hint has an unquoted remote name.
  - **Evidence:** Filed `data/bugs/git-new-branch-hint-unquoted-remote`; the
    hint in `git-new-branch.py::resolve_base` has no `bash_quote`.
- [x] A bug records `self-improve-learning-loop` "The mutator enforces a
  normative path allowlist": the mutator accepts a rule at any depth.
  - **Evidence:** Filed `data/bugs/self-improve-allowlist-accepts-nested-rules`;
    `allowlist.py::_kind_of` checks `len(parts) >= 2` only.
- [x] A bug records `git-new-branch` "The git-commit skill never commits on the
  default branch": the detached-`HEAD` refusal names no skill.
  - **Evidence:** Filed `data/bugs/git-commit-detached-head-names-no-skill`; the
    `PREFLIGHT_ERROR` row of the git-commit skill still names no skill.
- [x] A bug records `template-consumption` "publisher-only source never survives
  adoption": the consumption guide is older than the template tree.
  - **Evidence:** Filed
    `data/bugs/consumption-guide-keeps-publisher-source-references`; the guide
    still names no `agentdev_runtime` entry of `pyproject.toml`.
- [x] A bug records `template-consumption` "every template path has one class":
  the consumption guide is older than the template tree.
  - **Evidence:** Filed `data/bugs/consumption-guide-classifies-no-path`; `grep`
    finds none of the listed paths in the guide.
- [x] A bug records `template-consumption` "a retained custom-image bundle
  builds from an explicit choice": the consumption guide is older than the
  template tree.
  - **Evidence:** Filed `data/bugs/custom-image-bundle-misses-runtime-inputs`;
    both runtime Dockerfiles still mount `py_packages/agentdev_runtime`.
- [x] `line-free-anchors` "Live anchors resolve" has no new bug: [Resolve
  bare-path anchors or narrow the live-anchor
  requirement](../../../backlog/bare-path-anchors.md) records it already.
  - **Evidence:** `data/backlog/bare-path-anchors` is still pending; this plan
    filed no bug for it.

### Task 2: Remove the redundant requirements

**Files:** Modify: the documents under `docs/knowledge/data/spec/`

- [x] We compared each requirement that changed after commit `c81efa7e` with the
  code again, and its `fate` still applies.
  - **Evidence:** We compared 13 changed and 2 renamed requirements with the
    rulebooks and tests that they repeat; each fate is still correct.
    `ai-review-gate` "the review never executes code" has no audit row, so it
    stays.
- [x] No requirement whose `fate` is `drop-tested` is in `data/spec/`.
  - **Evidence:** A parse of each spec finds none of the 118 `drop-tested` rows.
- [x] No requirement whose `fate` is `drop-prose-duplicate` is in `data/spec/`.
  - **Evidence:** A parse of each spec finds none of the 67 rows, and neither
    renamed copy.
- [x] No requirement whose `fate` is `drop-restates` is in `data/spec/`.
  - **Evidence:** A parse of each spec finds none of the 22 rows.
- [x] Each requirement with another `fate` is in its spec with its scenarios.
  - **Evidence:** All 57 rows are present, and each block has the same bytes as
    its text before the removal.

### Task 3: Correct the requirements that stay and are not fully true

**Files:** Modify: the documents under `docs/knowledge/data/spec/`

- [x] Each of the 11 requirements whose `truth` is not `true` and whose `fate`
  is `adr`, `needs-test`, or `no-home` agrees with the code that its
  `truth_note` names.
  - **Evidence:** We corrected ten after we read the code that their notes name;
    six now name their filed bug. `stacked-prs` "Merges into dependent branches
    are blocked" is unchanged: the one clause that we can check is correct.
- [x] No correction removes a guarantee for which Task 1 filed no bug.
  - **Evidence:** Each correction with a Task 1 bug keeps its `SHALL` and adds
    the exception. The other four only state what the code was built to do.

### Task 4: Correct the `## Rationale` entries that the code contradicts

**Files:** Modify: `docs/knowledge/data/spec/agent-file-discovery.md`,
`docs/knowledge/data/spec/claude-remote-control.md`,
`docs/knowledge/data/spec/iwe-workflow-skills.md`,
`docs/knowledge/data/spec/self-improve-learning-loop.md`

- [x] `spec/agent-file-discovery` has no entry "Agent metadata is a colocated
  file with one key per consumer".
  - **Evidence:** Removed the entry; nothing outside the archive linked it.
- [x] The entry "Session mode resumes one pinned conversation per volume" in
  `spec/claude-remote-control` names only a volume that a descriptor declares.
  - **Evidence:** It now names `agentdev-home-${devcontainerId}`, which
    `docker/devcontainer/agentdev-devcontainer.Dockerfile` declares, and
    `remote_control.py::config_dir` holds the ID file.
- [x] `spec/iwe-workflow-skills` has no entry "Revision and spec synchronization
  belong to Plan and Ship".
  - **Evidence:** `grep` finds no such entry; commit `3fef60bc` removed it
    before this plan started.
- [x] The entry "The plugin lives in this repository as a second catalog plugin"
  in `spec/self-improve-learning-loop` says that the runtime installs the plugin
  by default.
  - **Evidence:** The entry now says that the runtime installs and enables it by
    default in every container; `lifecycle.py::created` installs at user scope.

### Task 5: Delete the empty specs and repair the references

**Files:** Modify: `docs/knowledge/data/spec.md`, and each file that cites a
removed requirement or a deleted spec

- [x] Remove each spec that has no requirement and no `## Rationale` entry with
  `iwe delete`.
  - **Evidence:** A count per spec finds at least one `## Rationale` entry in
    each of the 40, so no spec agrees with the condition, and we removed no
    spec.
- [x] No code comment cites a spec that was deleted.
  - **Evidence:** No spec was deleted; each spec that a comment cites still
    exists.
- [x] No document outside `data/archive/` links a requirement that was removed.
  - **Evidence:** `data/backlog/observe-planned-adversarial-review` now points
    at the `iwe-implementer` rulebook; the merge of #881 archived the plan that
    linked a removed heading, and `check-anchors.py` passes.
- [x] `README.md` and `AGENTS.md` link no spec that was deleted.
  - **Evidence:** No spec was deleted, and `data/spec.md` still lists all 40.

## Acceptance

None — no behavioral change

## Depends on

[Add ADRs and take the workflow off
specs](20261113-adrs-and-workflow-off-specs.md)

## Verification

``` bash
iwe normalize && iwe schema validate
uv run scripts/check-anchors.py
uv run pytest docs/knowledge/tests
docs/spec-audit/aggregate.py --fate drop-tested
```

## Out of scope

- A fix for a bug that Task 1 files.
- The move of `## Rationale` entries into ADRs.
- The tests that are missing, and the removal of the requirements that wait for
  them.
- An update of the labels in `docs/spec-audit/`.

## Key references

- `docs/spec-audit/requirements.jsonl` — one row for each requirement, with its
  `fate`, `truth`, and `truth_note`.
- `docs/spec-audit/rationale.jsonl` — one row for each `## Rationale` entry,
  with `accurate`.
- `docs/spec-audit/README.md` — the meaning of each field.
- `docs/spec-audit/aggregate.py` — lists the requirements with one `fate`.
- `docs/knowledge/data/spec.md` — the hub that loses the deleted specs.

## Ship review

`iwe-ship-reviewer` did this review on 2026-11-14.

- [x] Verify found no CRITICAL problem — correct: Ready to ship:
  data/plans/20261113-remove-redundant-and-wrong-spec-text (commit
  85e733787367064ba0d1820bdb15cb134b90be4d)
- [x] Every ADR that the plan proposed is `stage: accepted` — not applicable:
  the plan proposed no ADR
- [x] Every ADR that the plan superseded is `stage: superseded` and in the
  archive — not applicable: the plan superseded no ADR
- [x] The plan is `stage: done` with `completed` and no `rank` — correct:
  2026-11-14
- [x] Every feature in `release` is `stage: implemented` — not applicable:
  `release` lists no feature
- [x] Every bug in `release` is `stage: done` with no `rank` — not applicable:
  `release` lists no bug
- [x] Every bug in `release` has a `## Fix` that links this plan — not
  applicable: `release` lists no bug
- [x] The plan and every feature and bug that it completed are in the archive,
  and no hub links them — correct:
  data/archive/next-release/plans/20261113-remove-redundant-and-wrong-spec-text
