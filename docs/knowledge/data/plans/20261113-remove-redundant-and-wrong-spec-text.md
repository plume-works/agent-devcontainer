---
type: plan
created: 2026-11-13
release: internal
description: File a bug for each guarantee that the code does not deliver, then remove the spec requirements that a test, a rulebook, or plain code already states and correct or remove the spec text that is wrong.
sources:
- resource: docs/spec-audit/requirements.jsonl
- resource: docs/spec-audit/rationale.jsonl
- resource: docs/spec-audit/README.md
---

# Remove the spec text that is redundant or wrong

## Context

[The spec usefulness audit](../findings/spec-usefulness-audit.md) labelled each
of the 264 requirements in `data/spec/`. 207 of them repeat a test, a rulebook,
or code that reads plainly. 34 are not fully true. The code contradicts 4
`## Rationale` entries. The labels are in `docs/spec-audit/`.

This plan is the first removal step of [Shrink the knowledge base to an issue
tracker and decision
records](../backlog/shrink-knowledge-base-to-issues-and-adrs.md). It removes
only what the audit already shows to be redundant or wrong.

The repository owner's decisions:

- A guarantee that the code does not deliver gets a bug before its text is
  removed. The bug can close later as a dropped promise.
- After the bug is filed, the requirement text is removed freely.

## Approach

The `fate` field in `docs/spec-audit/requirements.jsonl` decides what happens to
a requirement:

- `drop-tested`, `drop-prose-duplicate`, `drop-restates`: the requirement and
  its scenarios are removed.
- Any other fate: the requirement stays for the later work. If it is not fully
  true, its text is corrected to agree with the code.

The audit data describes commit `c81efa7e`. A requirement that changed after
that commit is read against the code again before it is removed or corrected.

A `## Rationale` section stays, except for the 4 entries that the code
contradicts. A spec that has no requirement and no `## Rationale` entry is
deleted.

## Implementation Steps

### Task 1: File a bug for each guarantee that the code does not deliver

**Files:** Create: one document under `docs/knowledge/data/bugs/` for each bug;
Modify: `docs/knowledge/data/bugs.md`

Each bug is filed with `/agentdev:iwe-capture bug`. Its evidence is the entry in
`data/findings/spec-usefulness-audit#requirements-that-are-not-fully-true` and
the row in `docs/spec-audit/requirements.jsonl`.

- [ ] A bug records `agentdev-runtime-images` "the runtime is one CLI installed
  as a uv tool": two dependencies are ranges.
- [ ] A bug records `firewall` "enabled firewall default-DROPs IPv4 and blocks
  IPv6 entirely": IPv6 stays open when `ip6tables` is missing.
- [ ] A bug records `pre-commit-gate` "every commit path runs the hooks, merges
  included": two hooks omit the `pre-merge-commit` stage.
- [ ] A bug records `image-pinning` "published tags name only tested images":
  the `ubuntu-ansible` image has no revision label.
- [ ] A bug records `standalone-opencode-runtime` "startup prepares or reuses
  one workspace": a reused checkout gets no credential helper.
- [ ] A bug records `devcontainer-git-credentials` "HTTPS git uses the gh
  login": the Coder start does not wait for the keyring session.
- [ ] A bug records `devcontainer-state` "the home volume starts empty and the
  bootstrap claims it": the `fish_setup` role writes into the build user's home.
- [ ] A bug records `devcontainer-state` "root-only tests run through a
  launcher": the guard for unmarked tests cannot fire.
- [ ] A bug records `dependency-updates` "derived files are regenerated with the
  bump": the file filters omit one lock file.
- [ ] A bug records `catalog-scripts` "command lines handed to a shell are
  quoted by bash_quote": one hint has an unquoted remote name.
- [ ] A bug records `self-improve-learning-loop` "The mutator enforces a
  normative path allowlist": a rule is accepted at any depth.
- [ ] A bug records `git-new-branch` "The git-commit skill never commits on the
  default branch": the detached-`HEAD` refusal names no skill.
- [ ] A bug records `template-consumption` "publisher-only source never survives
  adoption": the consumption guide is behind the template tree.
- [ ] A bug records `template-consumption` "every template path has one class":
  the consumption guide is behind the template tree.
- [ ] A bug records `template-consumption` "a retained custom-image bundle
  builds from an explicit choice": the consumption guide is behind the template
  tree.
- [ ] `line-free-anchors` "Live anchors resolve" gets no new bug: [Resolve
  bare-path anchors or narrow the live-anchor
  requirement](../backlog/bare-path-anchors.md) records it already.

### Task 2: Remove the redundant requirements

**Files:** Modify: the documents under `docs/knowledge/data/spec/`

- [ ] Each requirement that changed after commit `c81efa7e` was read against the
  code again, and its `fate` still applies.
- [ ] No requirement whose `fate` is `drop-tested` is in `data/spec/`.
- [ ] No requirement whose `fate` is `drop-prose-duplicate` is in `data/spec/`.
- [ ] No requirement whose `fate` is `drop-restates` is in `data/spec/`.
- [ ] Each requirement with another `fate` is in its spec with its scenarios.

### Task 3: Correct the requirements that stay and are not fully true

**Files:** Modify: the documents under `docs/knowledge/data/spec/`

- [ ] Each of the 11 requirements whose `truth` is not `true` and whose `fate`
  is `adr`, `needs-test`, or `no-home` agrees with the code that its
  `truth_note` names.
- [ ] No correction removes a guarantee for which Task 1 filed no bug.

### Task 4: Correct the `## Rationale` entries that the code contradicts

**Files:** Modify: `docs/knowledge/data/spec/agent-file-discovery.md`,
`docs/knowledge/data/spec/claude-remote-control.md`,
`docs/knowledge/data/spec/iwe-workflow-skills.md`,
`docs/knowledge/data/spec/self-improve-learning-loop.md`

- [ ] `spec/agent-file-discovery` has no entry "Agent metadata is a colocated
  file with one key per consumer".
- [ ] The entry "Session mode resumes one pinned conversation per volume" in
  `spec/claude-remote-control` names only a volume that a descriptor declares.
- [ ] `spec/iwe-workflow-skills` has no entry "Revision and spec synchronization
  belong to Plan and Ship".
- [ ] The entry "The plugin lives in this repository as a second catalog plugin"
  in `spec/self-improve-learning-loop` says that the plugin is installed by
  default.

### Task 5: Delete the empty specs and repair the references

**Files:** Modify: `docs/knowledge/data/spec.md`, and each file that cites a
removed requirement or a deleted spec

- [ ] Each spec that has no requirement and no `## Rationale` entry is deleted
  with `iwe delete`.
- [ ] No code comment cites a spec that was deleted.
- [ ] No document outside `data/archive/` links a requirement that was removed.
- [ ] `README.md` and `AGENTS.md` link no spec that was deleted.

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
