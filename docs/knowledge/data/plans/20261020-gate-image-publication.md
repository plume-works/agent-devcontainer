---
type: plan
created: 2026-10-20
release:
- bugs/ci-publishes-images-before-acceptance
description: Publish ubuntu-ansible, agent-desktop, and agent-opencode under their moving tags only after the same run's devcontainer checks and runtime acceptance pass.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T04:00:00Z
sources:
- resource: .github/workflows/ci.yml
- resource: .github/workflows/primary-checks.yml
- resource: .github/actions/docker/multiarch-merge/action.yml
- resource: .github/actions/docker/metadata-action/action.yml
- resource: .github/actions/docker/build-push-action/action.yml
---

# Gate image publication on acceptance

## Context

[Bug: CI/CD publishes images before testing
them](../bugs/ci-publishes-images-before-acceptance.md): every image CI/CD
builds, `ubuntu-ansible`, `agent-desktop`, and `agent-opencode`, gets its moving
tags before the devcontainer checks and runtime acceptance run. A failed or
cancelled run leaves `edge` naming an untested build. Renovate then pins it, and
pull request builds use it as their warm-start base. Runs on `main` overlap,
because Renovate automerges its pull requests, and a clean build installs
unpinned OS packages that change between runs.

[Image pinning](../spec/image-pinning.md) is the contract consumers rely on: a
digest pin is only as good as the image the tag named when Renovate read it.

## Approach

Build, test, promote. Each run pushes its multi-arch manifests under an
immutable `sha-<commit>` tag only. A promotion job that needs the devcontainer
checks and native runtime acceptance then points the event's moving tags
(`edge`, `main`, `pr-<n>`, release versions) at the tested digests with
`imagetools create`, rebuilding nothing. Before moving a tag, it reads the
`org.opencontainers.image.revision` label of the image the tag names and skips
the tag when that commit descends from this run's commit, so a re-run of an
older run never moves a tag backwards. A label naming a commit outside this
checkout's history, such as a pull request's earlier merge commit, does not
block promotion.

Primary checks runs on `main` queue rather than cancel: the running pipeline
finishes and only the newest waiting run follows, so `edge` keeps advancing
while merges arrive faster than a run completes. Other refs keep cancelling.

Rejected: promoting the pull request's tested image on merge, because squash
merges and Renovate commits make `main`'s tree differ from any tested pull
request head.

## Implementation Steps

### Task 1: Push only candidate tags and promote after the tests

**Files:** Modify: `.github/workflows/ci.yml`,
`.github/actions/docker/multiarch-merge/action.yml`,
`.github/actions/docker/metadata-action/action.yml`,
`scripts/tests/test_agent_runtime_ci.py`; Create:
`.github/actions/docker/promote/action.yml`

- [x] `merge-dev-image` pushes each of the three manifests under `sha-<commit>`
  only and exports its digest.
  - **Evidence:** `multiarch-merge` derives tags with `candidate: 'true'`, which
    `metadata-action` limits to `type=sha`; `merge-dev-image` exports
    `ansible_digest`, `desktop_digest`, `opencode_digest`.
    `test_the_merge_pushes_only_the_candidate_tag` passes in
    `uv run pytest scripts/tests/test_agent_runtime_ci.py` (18 passed);
    actionlint and zizmor pass through pre-commit.
- [x] A `promote-dev-image` job needs `dev-container-ci` and
  `opencode-acceptance`, applies the event's moving tags to the three merged
  digests without rebuilding, and skips a tag whose current image is built from
  a descendant of this commit. `CI finished` needs the promotion.
  - **Evidence:** `.github/actions/docker/promote/action.yml` applies the moving
    tags with `imagetools create` and skips a tag whose revision label descends
    from `GITHUB_SHA`;
    `test_promotion_waits_for_both_test_jobs_and_reuses_the_merged_digests` and
    `test_promotion_never_moves_a_tag_back_or_rebuilds` pass in the same run;
    the action's script passes shellcheck.

### Task 2: Queue Primary checks runs on main

**Files:** Modify: `.github/workflows/primary-checks.yml`

- [x] Primary checks cancels an in-progress run on every ref except `main`.
  - **Evidence:** `primary-checks.yml` sets
    `cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`; actionlint and
    zizmor pass through pre-commit on the workflow.

### Task 3: Refresh the codebase map

**Files:** Refresh: `docs/knowledge/data/codebase/flow-image-build.md`,
`docs/knowledge/data/codebase/github/workflows.md`, and other stale mapped
sources

- [ ] Refresh the map docs whose sources moved through `/agentdev:iwe-map`;
  `stale-map-docs.py` ends `RESULT=SUCCESS`.

### Task 4: Observe gated promotion on the pull request

**Files:** none; the pull request's CI run

- [ ] **Closed by: CI on the pull request.** The run pushes only `sha-<commit>`
  for all three images before its test jobs, and its promotion job adds `pr-<n>`
  after both pass.

### Task 5: Observe gated promotion on main

**Files:** none; CI after merge

- [ ] **Closed by: CI after merge.** A `main` run promotes `edge` for all three
  images only after both test jobs pass, its revision labels name that run's
  commit, and a run whose tests fail or are cancelled leaves `edge` unchanged.

## Spec changes

Add to [Image pinning](../spec/image-pinning.md), preserving all current
requirements and scenarios:

``` markdown
## ADDED Requirements

### Requirement: published tags name only tested images

CI SHALL push each built ubuntu-ansible, agent-desktop, and agent-opencode
multi-arch image under an immutable `sha-<commit>` tag only. It SHALL point the
event's moving tags (`edge`, `main`, `pr-<n>`, and release versions) at those
digests only after the devcontainer checks and native runtime acceptance pass
in the same run, without rebuilding, and SHALL NOT move a tag to an image built
from an ancestor of the commit it names. Primary checks runs on `main` SHALL
NOT cancel one another.

#### Scenario: the tests pass

- **WHEN** a run's devcontainer checks and runtime acceptance pass
- **THEN** the event's moving tags name the digests that run built and tested.

#### Scenario: a test fails or the run is cancelled

- **WHEN** a test job fails, or the run is cancelled after the manifests merge
- **THEN** every moving tag keeps its previous digest, and only the `sha-<commit>` tag names the new build.

#### Scenario: an older run is re-run

- **WHEN** a re-run of an older commit's run passes after a newer commit was promoted
- **THEN** `edge` and `main` keep the newer commit's images.

#### Scenario: pushes to main arrive during a run

- **WHEN** commits land on `main` while its run is in progress
- **THEN** that run completes, and the newest waiting run follows it.
```

## Verification

- `uv run pytest scripts/tests/test_agent_runtime_ci.py`, and actionlint and
  zizmor through pre-commit on the changed workflows and actions.
- Tasks 4 and 5 close only on observed CI runs: inspect each image's tags and
  `org.opencontainers.image.revision` label with
  `docker buildx imagetools inspect` before and after the promotion job.
- Run `iwe normalize` and `iwe schema validate`; run `/agentdev:iwe-verify`
  against this plan and its delta before Ship merges the spec.

## Out of scope

- Deleting old `sha-<commit>` tags.
- Pinning the apt packages a clean build installs.
- Changing which jobs test an image, or what they test.

## Key references

Verified anchor points (line numbers as of 2026-10-20):

- `.github/workflows/ci.yml:64` — `build-dev-image`, pushing per-arch images by
  digest; `:182` — `merge-dev-image`, with merge steps at `:199`, `:207`, and
  `:216`; `:231` — `dev-container-ci`; `:309` — `opencode-acceptance`; `:347` —
  `finished`.
- `.github/workflows/primary-checks.yml:21-23` — `concurrency` with
  `cancel-in-progress: true`.
- `.github/actions/docker/multiarch-merge/action.yml:96` — `imagetools create`
  with every derived tag.
- `.github/actions/docker/metadata-action/action.yml:54-59` — the tag rules.
- `.github/actions/docker/build-push-action/action.yml:70` — `push-by-digest`
  per-arch output.
- `scripts/tests/test_agent_runtime_ci.py:70` —
  `test_the_runtime_gets_its_own_manifest_and_native_acceptance`.
