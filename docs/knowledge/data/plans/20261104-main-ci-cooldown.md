---
type: plan
created: 2026-11-04
release: internal
description: Hold each Primary checks run on main in a cancellable cooldown so back-to-back merges build once, cap the cooldown so a steady merge stream still builds, and widen the main pre-commit range to the last passing run so skipped commits are still checked.
sources:
- resource: .github/workflows/primary-checks.yml
- resource: .github/actions/paths-filter/action.yml
- resource: scripts/pre-commit-ci-range.py
- resource: openspec/specs/image-pinning/spec.md
- resource: openspec/specs/pre-commit-gate/spec.md
---

# Cool down Primary checks on main

## Context

Every push to `main` starts a full Primary checks run: a clean, multi-arch image
build and its acceptance jobs. Runs on `main` share one concurrency group that
queues instead of cancelling ([Image
pinning](../../../../openspec/specs/image-pinning/spec.md)), so pull requests
merged back to back build one after another, each from scratch, and the last
merge waits for every build before it.

The maintainer chose a cooldown on `main` over a merge queue: a merge queue
builds every queued pull request's `merge_group` ref and then the push to `main`
again, which multiplies builds instead of saving them.

The cancelled-run case is already handled for the image path filter: the shared
`paths-filter` action compares a push against the last commit Primary checks
passed on ([Bug: Image rebuild lost when a later push to main cancels its
run](../bugs/main-image-rebuild-lost-on-cancel.md)). The pre-commit job's range
still covers only the latest push ([pre-commit
gate](../../../../openspec/specs/pre-commit-gate/spec.md)).

## Approach

A new first job, `cooldown`, runs only on a `push` to `main`. It sits in its own
concurrency group with `cancel-in-progress: true` and waits before any build job
starts, so a newer push cancels a run that is still waiting and only the newest
commit of a burst builds. A run whose `ci` job has started is never cancelled by
a newer push; the `ci` job keeps a queueing group on `main`, where, as today, a
newer run waiting for the queue replaces an older one still waiting.

The wait is capped. `scripts/ci-cooldown.py` finds the oldest push run on `main`
since the newest push run that was not cancelled, and never waits beyond the cap
measured from that run's start. The defaults are 600 seconds of cooldown and an
1800-second cap, each overridable by a repository variable; a cooldown of `0`
starts the build at once.

The pre-commit job's range on a push to `main` widens to start at the head
commit of Primary checks' last successful push run, so commits whose runs were
cancelled stay checked on `main` and gitleaks scans them. The lookup of the last
successful run moves into a shared module both scripts use.

Rejected: a deployment environment wait timer. It spends no runner time, but
GitHub does not document whether concurrency cancels a job waiting on one.

## Implementation Steps

### Task 1: Shared workflow-run lookup

**Files:** Create: `scripts/ci_runs.py`, `scripts/tests/test_ci_runs.py`

- [ ] `scripts/ci_runs.py` (standard library only) resolves the calling
  workflow's id from `GITHUB_RUN_ID`, lists its `push` runs on a branch newest
  first through the REST API at `GITHUB_API_URL`, and returns the head commit of
  the last successful run, authenticating with `GH_TOKEN`. A failed request
  raises one module-defined error carrying the cause.
- [ ] Tests run the module against a local HTTP stub the test starts and owns:
  the last successful run's head commit, no successful run, and a request that
  fails.

### Task 2: Cooldown script

**Files:** Create: `scripts/ci-cooldown.py`, `scripts/tests/test_ci_cooldown.py`

- [ ] `scripts/ci-cooldown.py` reads `MAIN_COOLDOWN_SECONDS` (default `600`) and
  `MAIN_COOLDOWN_MAX_SECONDS` (default `1800`); an empty value takes the
  default, and a negative or non-integer value exits non-zero naming the
  variable.
- [ ] The script lists Primary checks' `push` runs on `main` newest first
  through `scripts/ci_runs.py`, skips its own run, and walks back over runs
  whose conclusion is `cancelled`; the first run with any other status or
  conclusion ends the walk. The anchor is the oldest walked run's `created_at`,
  or its own run's when the walk is empty.
- [ ] The script sleeps `max(0, min(cooldown, anchor + cap - now))` seconds and
  logs the anchor and the chosen wait. When the lookup fails, it warns and
  sleeps the full cooldown.
- [ ] Tests run the script with an injected clock and sleep against a local HTTP
  stub: no earlier run, an anchor already past the cap, an anchor inside the
  cooldown, a failed lookup, a cooldown of `0`, and an invalid variable.

### Task 3: Widen the pre-commit range on main

**Files:** Modify: `scripts/pre-commit-ci-range.py`,
`scripts/tests/test_pre_commit_ci_range.py`

- [ ] On a `push` to `main` whose `before` is not all zeros, the range starts at
  the last successful push run's head commit from `scripts/ci_runs.py` instead
  of `before`, unless that commit equals `after`. `all_files` and
  `gitleaks_log_opts` follow the widened range.
- [ ] When the lookup fails or finds no successful run, the script prints a
  `::warning::` and keeps `before..after`. Pushes to other branches, pull
  requests, merge groups, `workflow_dispatch`, and an all-zero `before` keep
  their current ranges.
- [ ] Tests cover a widened range that reaches a tool-version owner only through
  a skipped commit, a failed lookup, and a push to a branch other than `main`,
  against the scratch repository and a local HTTP stub.

### Task 4: Wire the cooldown into Primary checks

**Files:** Modify: `.github/workflows/primary-checks.yml`

- [ ] The workflow-level concurrency group uses `github.run_id` on
  `refs/heads/main` and `github.ref` elsewhere, so a run on `main` waiting for
  the `ci` queue never blocks the next run's `cooldown`. Other refs keep
  cancelling in progress as today.
- [ ] A `cooldown` job runs `scripts/ci-cooldown.py` when
  `github.event_name == 'push' && github.ref == 'refs/heads/main'`, on the
  `ubuntu-24.04` runner with `timeout-minutes: 35`, permissions `actions: read`
  and `contents: read`, concurrency group `${{ github.workflow }}-main-cooldown`
  with `cancel-in-progress: true`, and `MAIN_COOLDOWN_SECONDS` /
  `MAIN_COOLDOWN_MAX_SECONDS` from `vars`.
- [ ] `pre-commit` needs `cooldown` and runs when
  `!cancelled() && (needs.cooldown.result == 'success' || needs.cooldown.result == 'skipped')`.
  It gains `actions: read` and `GH_TOKEN: ${{ github.token }}` for the range
  lookup.
- [ ] `ci` needs `cooldown` and `pre-commit`, runs when `!cancelled()`,
  `needs.pre-commit.result == 'success'`, and `cooldown` succeeded or was
  skipped, and carries concurrency group `${{ github.workflow }}-ci-main` with
  `cancel-in-progress: false` on `refs/heads/main` and `github.run_id`
  elsewhere.
- [ ] The comment above the workflow-level `concurrency` block points at
  `spec/image-pinning` for the cooldown rule.

### Task 5: Observe a burst of merges on main

**Closed by:** the maintainer, after this plan's pull request merges.

- [ ] Two pull requests merged within ten minutes of each other produce one
  Primary checks run that builds: the first run ends `cancelled` with its build
  jobs skipped, and the second run's `pre-commit` range starts at or before the
  first merge's parent.

## Spec changes

[Image pinning](../../../../openspec/specs/image-pinning/spec.md):

``` markdown
## MODIFIED Requirements

## Requirement: published tags name only tested images

CI SHALL publish `ubuntu-ansible`, `agentdev-base`, `agentdev-deploy`, and
`agentdev-devcontainer` candidates under immutable commit tags and SHALL move
event tags only after native deploy and Dev Container acceptance and the
candidate pre-commit run pass for the same digests, without rebuilding. CI SHALL
NOT move a tag to an image built from an ancestor of the commit it names.
No Primary checks run SHALL cancel a run on `main` whose `ci` job has
started.

### Scenario: every acceptance check passes

- **WHEN** the run's image and runtime checks pass
- **THEN** the event's moving tags name the exact digests that run built and
  tested.

### Scenario: a check fails or the run is cancelled

- **WHEN** any required acceptance job fails or the run is cancelled
- **THEN** every moving tag keeps its previous digest, and only the immutable
  commit tag names the new image family.

### Scenario: an older run is re-run

- **WHEN** an older commit passes after a newer commit was promoted
- **THEN** moving tags keep the newer image family.

### Scenario: pushes to main arrive during a run

- **WHEN** commits land on `main` after a run's `ci` job started and before
  that run completes
- **THEN** that run completes, and the newest waiting run follows it.

## ADDED Requirements

## Requirement: pushes to main build after a cooldown

A Primary checks run started by a push to `main` SHALL wait
`MAIN_COOLDOWN_SECONDS` (default 600) before any build job starts, and a newer
push to `main` SHALL cancel a run that is still waiting. The wait SHALL end no
later than `MAIN_COOLDOWN_MAX_SECONDS` (default 1800) after the start of the
oldest push run since the newest push run that was not cancelled. Pull requests,
merge groups, tags, and `workflow_dispatch` SHALL NOT wait. When the run
history cannot be read, the run SHALL wait the full cooldown. The waiting job
holds a runner for the whole wait.

### Scenario: pushes arrive within the cooldown

- **WHEN** several pushes land on `main`, each within the cooldown of the one
  before
- **THEN** every run but the newest ends cancelled before building, and the
  newest builds once.

### Scenario: pushes keep arriving past the cap

- **WHEN** pushes keep landing on `main` until the oldest waiting push is older
  than the cap
- **THEN** the newest run starts building at the cap, and the next push waits a
  full cooldown.

### Scenario: the cooldown is turned off

- **WHEN** `MAIN_COOLDOWN_SECONDS` is `0`
- **THEN** a push to `main` starts building at once.
```

[pre-commit gate](../../../../openspec/specs/pre-commit-gate/spec.md):

``` markdown
## MODIFIED Requirements

### Requirement: CI runs the pre-commit hooks as the lint gate

Primary checks SHALL run `pre-commit run` inside the `agentdev-devcontainer`
image pinned by the same tag and digest as `devcontainer-compose-pins.yml`, over
the files the event's commit range changed, and the `ci` job SHALL start only
after it succeeds.

#### Scenario: a pull request changes source files

- **WHEN** a pull request changes files a hook matches
- **THEN** the pre-commit job runs those hooks on the files changed between the
  base and head commits, and fails when any hook fails or rewrites a file.

#### Scenario: a push to main

- **WHEN** commits are pushed to `main`
- **THEN** the job checks the files changed between the head commit of Primary
  checks' last successful push run on `main` and `after`, and skips
  `no-commit-to-branch`.

#### Scenario: the last successful run cannot be found

- **WHEN** a push to `main` finds no successful Primary checks push run, or the
  lookup fails
- **THEN** the job warns and checks the files changed between `before` and
  `after`.

#### Scenario: a manual run

- **WHEN** Primary checks is started by `workflow_dispatch`
- **THEN** the job checks every file.
```

## Verification

- `uv run pytest scripts/tests/test_ci_runs.py scripts/tests/test_ci_cooldown.py scripts/tests/test_pre_commit_ci_range.py`
  passes.
- `uv run pre-commit run --files .github/workflows/primary-checks.yml scripts/ci_runs.py scripts/ci-cooldown.py scripts/pre-commit-ci-range.py`
  passes, including `actionlint` on the workflow.
- `grep -n "SHALL NOT cancel one another" docs/knowledge/data/spec/image-pinning.md`
  finds nothing after Ship.
- Task 5's observation is recorded.

## Out of scope

- A merge queue, and any change to `merge_group` runs.
- Cooldowns for other workflows that run on `main` (`validate-*.yml`,
  `delete-old-containers.yml`); they are cheap and keep cancelling in progress.
- Moving the `paths-filter` action's own `last-pass` step onto
  `scripts/ci_runs.py`.
- A cooldown that spends no runner time.

## Key references

- `.github/workflows/primary-checks.yml › "main queues instead of cancelling, so edge keeps advancing"`
  — workflow-level `concurrency`, queueing on `main`
- `.github/workflows/primary-checks.yml#jobs.pre-commit` — `pre-commit` job and
  its permissions
- `.github/workflows/primary-checks.yml › "name: Select the range"` —
  `Select the range` step running `scripts/pre-commit-ci-range.py`
- `.github/workflows/primary-checks.yml#jobs.ci` — `ci` job calling
  `.github/workflows/ci.yml`
- `.github/actions/paths-filter/action.yml#runs.steps` — `last-pass`, the
  existing lookup of the last passing push run
- `scripts/pre-commit-ci-range.py::_event_range` — `_event_range`, the `push`
  branch returning `before..after`
- `scripts/pre-commit-ci-range.py::outputs` — `outputs`
- `scripts/pre-commit-ci-range.py::main` — `main`
- `openspec/specs/image-pinning/spec.md#requirement-published-tags-name-only-tested-images`
  — Requirement: published tags name only tested images
- `openspec/specs/pre-commit-gate/spec.md#requirement-ci-runs-the-pre-commit-hooks-as-the-lint-gate`
  — Requirement: CI runs the pre-commit hooks as the lint gate
