---
type: plan
created: 2026-11-07
release: internal
description: Copy every finished plan, bug, and feature that changed the coder-ide-baseline template into that repository's IWE workspace, after cutting agent-devcontainer 2.1.0 so each copy carries its release, and delete the two template-only originals here.
sources:
- resource: docs/knowledge/data/plans/20261031-coder-template-knowledge-split.md
- resource: https://github.com/plume-works/coder-ide-baseline/tree/5ff6817/docs/knowledge
stage: done
completed: 2026-11-07
---

# Move the template's finished history into coder-ide-baseline

## Context

[Move the Coder template's knowledge into
coder-ide-baseline](../../2.1.0/plans/20261031-coder-template-knowledge-split.md)
gave `plume-works/coder-ide-baseline` its own IWE workspace with the template's
spec, runbook, and the two documents that were only about the template. Every
other finished document that changed the template stayed here, so the template's
own memory holds little of the history behind its code.

The maintainer decided:

- Every finished document whose work changed the template is in
  `coder-ide-baseline`'s workspace. A document that also covers this repository
  is copied whole; its original stays here.
- The template-only originals here,
  [bugs/coder-devcontainer-lost-on-restart](https://github.com/plume-works/coder-ide-baseline/blob/main/docs/knowledge/data/bugs/coder-devcontainer-lost-on-restart.md)
  and
  [plans/20261011-persist-coder-workspace-containerd](https://github.com/plume-works/coder-ide-baseline/blob/main/docs/knowledge/data/plans/20261011-persist-coder-workspace-containerd.md),
  already copied, are deleted.
- `agent-devcontainer` 2.1.0 is cut before anything is copied, so every copied
  plan carries `released`.

## Approach

A finished document is in scope when its work changed `coder-ide-baseline` or
ran in it: a plan with a task whose files are in that repository, a bug whose
fix changed it, or a feature whose behavior the template carries part of.
Finished means plan `stage: done`, bug `stage: done`, feature
`stage: implemented`. The set, from the current checkout:

- Plans: `20261011-coder-agent-gh-credential-helper`,
  `20261011-coder-claude-remote-control`, `20261013-docker-storage-gc`,
  `20261016-opencode-web-coder-autostart`, `20261029-off-bash-migration`,
  `20261031-coder-template-knowledge-split`, and
  `20261101-docker-storage-periodic-gc`.
- Bugs: `coder-askpass-push-hang` and `coder-docker-storage-accumulates`.
- Features: `coder-remote-control-autostart`, `docker-storage-limits`, and
  `opencode-web-coder-autostart`.

Each copy is the original at the commit copied, unchanged apart from links and
one `sources` entry naming that original. A link to a document that exists in
the template workspace — copied here or earlier, including the two template-only
documents — becomes relative to it; every other relative link becomes an
`agent-devcontainer` URL on `main`. Frontmatter keys stay as they are: a copied
plan's `release` may name a feature or bug that is not copied, and its
`released` names the `agent-devcontainer` version, which `sources` makes
traceable.

The release cut comes first because the template workspace's release cut
collects every done plan without `released`; a copy without it would be claimed
as a template release. Once every copy merges, the two template-only originals
here are deleted with `iwe delete`, and each reference it flattens to plain text
becomes a link to the `coder-ide-baseline` copy on `main`, as does each
`sources` entry naming an original, so history here stays navigable.

Rejected: writing a template-only record of each mixed document, which
paraphrases finished history and leaves two accounts of one change; moving mixed
documents, which takes this repository's half with them.

## Implementation Steps

Tasks 4-7 run in a `coder-ide-baseline` checkout, from its repository root.

### Task 1: The knowledge split is on main

**Files:** none

- [x] [plume-works/agent-devcontainer#734](https://github.com/plume-works/agent-devcontainer/pull/734)
  is merged, so `20261031-coder-template-knowledge-split` is `stage: done` on
  `main`.
  - **Closed by:** the maintainer merging the pull request.
  - **Evidence:** #734 merged as `ca519534` on `main`; the plan carries
    `stage: done` at that commit.

### Task 2: Cut agent-devcontainer 2.1.0

**Files:** Create: `docs/knowledge/data/releases/2.1.0.md`; Modify:
`docs/knowledge/data/releases.md`, `docs/knowledge/data/log.md`, and every done
plan without `released`

- [x] `/agentdev:iwe-ship release 2.1.0` cuts the release on a branch from fresh
  `origin/main`; `20261101-docker-storage-periodic-gc` and
  `20261031-coder-template-knowledge-split` carry `released: 2.1.0`.
  - **Evidence:** `a50e6888` cuts 2.1.0 on top of `7dab00a1` (`origin/main`);
    both plans carry `released: 2.1.0`, and the done-without-`released` query
    prints nothing at that commit.

### Task 3: Merge the release

**Files:** none

- [x] The pull request carrying Task 2 merges to `main`.
  - **Closed by:** the maintainer merging the pull request.
  - **Evidence:** #740 merged to `main` as `2612a847` after CI passed and an
    approving AI review.

### Task 4: Copy the documents

**Files:** Create (in `plume-works/coder-ide-baseline`): the seven plans under
`docs/knowledge/data/plans/`, the two bugs under `docs/knowledge/data/bugs/`,
and the three features under `docs/knowledge/data/features/`, each at the key it
has here

- [x] Each document in `## Approach`'s set is copied from `agent-devcontainer`
  `main` after Task 3, with the link and `sources` changes `## Approach` names
  and no other change.
  - **Evidence:** `plume-works/coder-ide-baseline@55d3df0` adds the twelve
    copies from `main` at `2612a847`; with link targets and the added `sources`
    entry blanked, each copy matches its original token for token apart from the
    table rule `iwe normalize` widened, and `iwe schema validate` passes.

### Task 5: Link the copies from the hubs

**Files:** Modify (in `plume-works/coder-ide-baseline`):
`docs/knowledge/data/plans.md`, `docs/knowledge/data/bugs.md`,
`docs/knowledge/data/features.md`

- [x] Each copy is an entry in its hub's flat sorted list.
  - **Evidence:** `plume-works/coder-ide-baseline@b59c4b9` links all twelve
    copies, sorted by key without the date prefix; `iwe stats` there lists only
    root files as orphans.

### Task 6: Validate and push the template branch

**Files:** none

- [x] `iwe normalize` and then `iwe schema validate` pass in the template
  checkout, and the branch is pushed with a pull request open.
  - **Evidence:** both pass on `b59c4b9`, which is pushed as the head of
    plume-works/coder-ide-baseline#37.

### Task 7: Merge the template pull request

**Files:** none (in `plume-works/coder-ide-baseline`)

- [x] The pull request carrying Tasks 4-6 passes the required
  `Docker Build and Push` check and merges to `main`.
  - **Closed by:** the maintainer merging the pull request.
  - **Evidence:** plume-works/coder-ide-baseline#37 passed
    `Docker Build and Push` on `b59c4b9` and merged to `main` as `6711547`.

### Task 8: Delete the template-only originals

**Files:** Delete:
`docs/knowledge/data/bugs/coder-devcontainer-lost-on-restart.md`,
`docs/knowledge/data/plans/20261011-persist-coder-workspace-containerd.md`;
Modify: every document `iwe delete` updates

- [x] `iwe delete` removes both documents and their hub entries.
  - **Evidence:** `4e1d5743` deletes both documents and their `bugs.md` and
    `plans.md` entries; `iwe schema validate` passes on it.

### Task 9: Point the flattened references at the copies

**Files:** Modify: `docs/knowledge/data/log.md`,
`docs/knowledge/data/releases/2.0.0.md`,
`docs/knowledge/data/plans/20261011-coder-agent-gh-credential-helper.md`,
`docs/knowledge/data/plans/20261031-coder-template-knowledge-split.md`, and this
plan's `## Context`, which `iwe delete` flattens too

- [x] Each reference Task 8 flattened to plain text is a link to the
  `coder-ide-baseline` copy on `main`, and each `sources` entry naming a deleted
  original names that copy; no other text changes.
  - **Evidence:** `98674631` links every flattened reference, restoring the
    `releases/2.0.0.md` entry `iwe delete` removed; with link targets blanked,
    the four named files match their text at `6c67b36f`. `537eb6f5` points the
    two `sources` entries in `20261031-coder-template-knowledge-split` at the
    copies. Both URLs resolve through `gh api` on `coder-ide-baseline` `main`.

## Spec changes

None — no behavioral change.

## Depends on

- [Move the Coder template's knowledge into
  coder-ide-baseline](../../2.1.0/plans/20261031-coder-template-knowledge-split.md)

## Verification

- In the template checkout on `main`: `iwe schema validate` passes, and
  `iwe find --filter '{type: plan, stage: done, released: {$exists: false}}' -f keys`
  prints nothing.
- For each copied document, a diff against its original at the commit its
  `sources` names shows only rewritten links and the added `sources` entry.
- Every `agent-devcontainer` URL in the copies returns the file from
  `gh api repos/plume-works/agent-devcontainer/contents/<path>?ref=main`.
- Here: `iwe schema validate` passes, `iwe stats` reports no broken links, and
  every link and `sources` entry that
  `grep -rn 'coder-devcontainer-lost-on-restart\|persist-coder-workspace-containerd' docs/knowledge/data`
  matches is a `coder-ide-baseline` URL; its other matches are plain paths in
  code spans or this plan's own text.
- Here: `git diff` of Tasks 8-9 touches only the deleted documents, their hubs,
  and the four files Task 9 names.

## Out of scope

- Open work about the template: the active [shared BuildKit
  plan](../../../someday/shared-buildkit-builder.md), the accepted [shared
  BuildKit builder](../../../someday/shared-buildkit-builder.md) feature, and
  the pending [supervised Remote
  Control](../../../backlog/coder-supervised-remote-control.md) task.
- Finished documents that mention the template without changing it: the Remote
  Control plans that name its `coder_script` as a caller,
  `20261018-opencode-v2-default`, `20261014-expo-eas-template-profile`, the bug
  `workspace-image-lacks-hook-binaries`, and the features `expo-eas-builds` and
  `claude-remote-control-server-mode`.
- Specs and architecture: the specs were split by the knowledge split, and no
  architecture document here is about the template.
- Deleting or editing the mixed originals here.

## Key references

- `docs/knowledge/data/plans/20261011-coder-agent-gh-credential-helper.md#task-3-template-runs-the-agent-start-script`
  — Task 3: Template runs the agent-start script;
  `docs/knowledge/data/plans/20261011-coder-agent-gh-credential-helper.md#verification`,
  `docs/knowledge/data/plans/20261011-coder-agent-gh-credential-helper.md#verification`
  — links to the two template-only originals
- `docs/knowledge/data/plans/20261011-coder-claude-remote-control.md#task-4-template-coder_script-in-coder-ide-baseline`
  — Task 4: Template `coder_script` in coder-ide-baseline
- `docs/knowledge/data/plans/20261013-docker-storage-gc.md#task-4-bound-the-workspace-engine-in-coder-ide-baseline`
  — Task 4: Bound the workspace engine in coder-ide-baseline
- `docs/knowledge/data/plans/20261016-opencode-web-coder-autostart.md#task-12-add-the-opencode-app-to-the-coder-template`
  — Task 12: Add the OpenCode app to the Coder template
- `docs/knowledge/data/plans/20261029-off-bash-migration.md#task-19-the-coder-template-starts-the-agent-through-the-cli`
  — Task 19: The Coder template starts the agent through the CLI
- `docs/knowledge/data/plans/20261101-docker-storage-periodic-gc.md#task-5-the-workspace-engines-collector`
  — Task 5: The workspace engine's collector
- `docs/knowledge/data/bugs/coder-askpass-push-hang.md#fix` — `## Fix`
- `docs/knowledge/data/bugs/coder-docker-storage-accumulates.md#fix` — `## Fix`
- `docs/knowledge/data/features/coder-remote-control-autostart.md#behaviour › "template attaches a"`
  — the template's `coder_script`
- `docs/knowledge/data/features/docker-storage-limits.md#purpose › "A Coder workspace runs two Docker engines — the workspace"`
  — the workspace engine
- `docs/knowledge/data/features/opencode-web-coder-autostart.md#behaviour › "app that opens the same address. OpenCode v2's web"`
  — the dashboard `OpenCode` app
- `docs/knowledge/data/log.md#2026-10-12`,
  `docs/knowledge/data/log.md#2026-10-12` — links to the two template-only
  originals
- `docs/knowledge/data/releases/2.0.0.md#fixed › "restart](../bugs/coder-devcontainer-lost-on-restart.md)"`
  — link to `bugs/coder-devcontainer-lost-on-restart`
- `docs/knowledge/data/bugs.md`, `docs/knowledge/data/plans.md` — hub entries of
  the two template-only originals, removed by Task 8
- `docs/knowledge/data/plans/20261031-coder-template-knowledge-split.md#context`,
  `docs/knowledge/data/plans/20261031-coder-template-knowledge-split.md#context`
  — links;
  `docs/knowledge/data/plans/20261031-coder-template-knowledge-split.md › "resource"`,
  `docs/knowledge/data/plans/20261031-coder-template-knowledge-split.md › "resource"`
  — `sources` entries naming them to the two template-only originals
- `coder-ide-baseline@5ff6817:docs/knowledge/data/bugs/coder-devcontainer-lost-on-restart.md`
  and `docs/knowledge/data/plans/20261011-persist-coder-workspace-containerd.md`
  — the copies already in the template workspace
