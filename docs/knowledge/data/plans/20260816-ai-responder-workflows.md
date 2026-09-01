---
type: plan
created: 2026-08-16
description: Import Dr-QP's AI responder and required-AI-review workflows, Claude-only, with the responder running the devcontainer lifecycle hooks so it reviews using the branch's own agentdev catalog and an indexed CBM.
generated:
  by: claude-code/opus-5
  at: 2026-08-17T18:10:00Z
sources:
- resource: https://github.com/plume-works/agent-devcontainer/pull/65#discussion_r3794941822
stage: done
completed: 2026-08-31
---

# AI responder workflows

## Context

This repository has no automated PR review. Dr-QP runs two workflows that
together provide one: `ai-responder.yml` answers `@claude` mentions and reviews
PRs, and `require-ai-review.yml` blocks merge until an AI review exists. They
are a matched pair — the gate is satisfiable because the responder produces the
review.

Importing them surfaced a prerequisite. The responder must run in a container
with the project toolchain to produce a grounded review, and the review is
driven by the `agentdev:pr-review` skill. A GitHub Actions `container:` job runs
no devcontainer lifecycle hooks, so nothing installs that skill and the
responder would improvise a review — producing a green required check over an
ungrounded review.

The fix is the one the devcontainer already uses: the job checks out the branch
and runs the lifecycle scripts itself. That gives the responder the *branch's
own* catalog — a PR that changes a skill is reviewed by the skill as changed —
plus an indexed codebase-memory-mcp, which is what makes the review grounded.

The reasoning, including the image-build-time install that was considered and
rejected once the checkout was recognized as always present, is recorded in
[CI agent plugin availability](../architecture/ci-agent-plugin-availability.md).

## Approach

The image is used as-is. The responder job checks out the branch and runs the
devcontainer lifecycle scripts, which is how the workspace catalog already
reaches both agents.

Which scripts matters more than "postCreate and postStart" suggests. The
checkout-based catalog install and the CBM *index* live in **postAttach**, not
postStart; postStart only *starts* CBM. All three hooks are therefore needed:

| hook       | what the responder needs from it                                |
| ---------- | --------------------------------------------------------------- |
| postCreate | **CBM install**, auth symlinks, `uv-sync`, image-scoped catalog |
| postStart  | `codebase-memory-mcp-start.sh` — starts CBM, does not index     |
| postAttach | **CBM index**, `uv-sync`, **catalog from this checkout**        |

CBM needs all three: it is *installed* into agent config from postCreate
(`postCreateCommand.sh:52`), *started* by postStart, and *indexed* by
postAttach.

Two postStart steps are pure cost in a review job and get `AGENTDEV_*` guards,
defaulting to today's behavior so the devcontainer is unchanged:
`setup-pre-commit.sh` runs `pre-commit install --install-hooks`, which eagerly
builds a virtualenv for every hook in the repo — minutes, for hooks a review job
never fires — and `/start-xpra.sh --background` starts a remote desktop nothing
will connect to. `setup-keyring.sh` needs no guard: it already exits cleanly
when the keyring stack is absent.

The rest of the setup is cheap. A cold CBM index measures ~3.5s in this
repository, so hook installation is the only step worth skipping for time;
upstream's 30-minute job timeout carries over unchanged.

The guards are not the whole story: the hooks also depend on
`devcontainer.json`'s `containerEnv` and mounts, which a `container:` job does
not apply. Tasks 7 and 8 supply what they need. The boundary and its minimal
contract are recorded in
[CI agent plugin availability](../architecture/ci-agent-plugin-availability.md).

`ai-responder.yml` is imported Claude-only: the `codex-respond` job, the codex
preflight conditions, the `AI_RESPONDERS` variable with its validation step and
`enabled()` helper, and every ROS-specific element (the
`scripts/with-ros-env.sh` preflight check and the prompt line naming it) are all
dropped. The fork gate and the write-access gate are kept verbatim — they are
the security spine.

`require-ai-review.yml` is imported verbatim apart from one line:
`actions/checkout` is repinned from upstream's `v6.0.3` to the `v7.0.1` every
other workflow here uses, because this repository pins actions and images
deliberately rather than letting a second version float in. Its codex acceptance
path is live, not dead: Codex reviews arrive via Codex web as
`chatgpt-codex-connector[bot]`, entirely outside GitHub Actions.

Rejected: installing the catalog into the image at build time (the checkout is
always present, so the image never needed to carry an install — and it would
have made the image ship a `~/.claude.json` it does not ship today); running the
responder on a bare runner (gives up the toolchain that makes a review
grounded); and vendoring a repo-local `pr-review` skill (forks from the catalog
copy and drifts).

## Implementation Steps

### Task 1: Split git safe.directory setup out of pre-commit setup

**Files:** Create: `.devcontainer/scripts/setup-git-safe-directory.sh`; Modify:
`.devcontainer/scripts/setup-pre-commit.sh`,
`.devcontainer/scripts/postStartCommand.sh`

Separating these is what lets Task 2 guard hook installation without also
skipping safe.directory — the responder needs the latter (its checkout is owned
by a different uid) and never needs the former.

- [x] Move `git config --global --add safe.directory` and its `command -v git`
  check out of `setup-pre-commit.sh:8-11` into `setup-git-safe-directory.sh`
  - **Evidence:** `.devcontainer/scripts/setup-git-safe-directory.sh` created
    with the `command -v git` check and the `safe.directory` config; both lines
    removed from `setup-pre-commit.sh`.
- [x] Call the new script from `postStartCommand.sh` before
  `setup-pre-commit.sh`
  - **Evidence:** `postStartCommand.sh` now calls `setup-git-safe-directory.sh`
    on the line above `setup-pre-commit.sh`.
- [x] Remove the leftover `git status` troubleshooting line
  (`setup-pre-commit.sh:12`)
  - **Evidence:** `setup-pre-commit.sh` no longer contains `git status`; the
    file is now 13 lines, ending at the `pre-commit install` call.
- [x] Confirm `shellcheck` passes on both scripts
  - **Evidence:**
    `shellcheck setup-git-safe-directory.sh setup-pre-commit.sh postStartCommand.sh`
    — exit 0, no output.

### Task 2: Guard the lifecycle steps a review job does not need

**Files:** Modify: `.devcontainer/scripts/setup-pre-commit.sh`,
`.devcontainer/scripts/postStartCommand.sh`

Both guards default to today's behavior, so the devcontainer is unchanged and
only a caller that opts in skips anything.

- [x] Guard `pre-commit install --install-hooks` behind
  `AGENTDEV_SKIP_PRE_COMMIT`; it eagerly builds a virtualenv per hook, which
  costs minutes for hooks a review job never fires
  - **Evidence:** early `exit 0` added to `setup-pre-commit.sh` when the
    variable is non-empty; run with it set prints the skip message and exits 0,
    run with it unset still reaches `pre-commit install --install-hooks`.
- [x] Guard `/start-xpra.sh --background` in `postStartCommand.sh:14` behind
  `AGENTDEV_SKIP_XPRA`
  - **Evidence:** `if/else` around the call in `postStartCommand.sh`; the guard
    block sourced with the variable set prints only the skip message, and unset
    it runs `/start-xpra.sh --background` (Xpra server startup banner).
- [x] Confirm `shellcheck` passes and that neither guard changes behavior when
  its variable is unset
  - **Evidence:** `shellcheck setup-pre-commit.sh postStartCommand.sh` — exit 0.
    Unset runs reach `pre-commit install --install-hooks` and start Xpra, the
    same steps as before the guards.

### Task 3: Provision repository secrets and environment

**Files:** none — repository settings

Stands alone: it is the maintainer's action in GitHub settings, not a code
change, and Task 4 cannot be exercised until it is done.

The Claude GitHub App is **not** required: the workflow passes `github_token`
explicitly, so the app only changes whether the review is attributed to
`claude[bot]` or `github-actions[bot]`, and `require-ai-review.yml:71-74`
accepts both. All three items are documented for template consumers, with the
app marked optional, in [Template consumption](../spec/template-consumption.md).

- [x] Install the [Claude GitHub App](https://github.com/apps/claude) —
  optional, affects review attribution only
  - **Evidence:** installed by the maintainer during this work;
    `gh api orgs/plume-works/installations` lists `claude` alongside `renovate`
    and `chatgpt-codex-connector`.
- [x] Create the `CLAUDE_CODE_OAUTH_TOKEN` repository secret
  - **Evidence:** created by the maintainer, who confirmed it is in place.
    Secret *values* are not readable via the API by design, so this rests on
    that confirmation; a green responder run is what proves it end to end.
- [x] Create the `claude-review` environment
  - **Evidence:** `gh api repos/:owner/:repo/environments` lists `claude-review`
    alongside `reformat-commit`.

### Task 4: Import ai-responder.yml, Claude-only

**Files:** Create: `.github/workflows/ai-responder.yml`

- [x] Add the preflight job with the owner gate set to `plume-works`, the fork
  gate, and the write-access gate kept verbatim from upstream
  - **Evidence:** `.github/workflows/ai-responder.yml` `preflight` job —
    `github.repository_owner == 'plume-works'`, the `Determine checkout ref`
    step's `isFork` computation, and the `Authorize responder requester` step
    carried over unchanged from upstream.
- [x] Drop `AI_RESPONDERS` entirely — the env var, the validation step, the
  `enabled()` helper — and reduce the trigger conditions and prompt builder to
  Claude only
  - **Evidence:** no `AI_RESPONDERS`, no `Validate AI_RESPONDERS` step, and no
    `enabled()` in the new workflow; the preflight `if:` tests only `@claude`,
    the `codex-respond` job and every codex output are gone, and
    `claudeRequested` is now just `mentions('claude')`.
- [x] Drop the `scripts/with-ros-env.sh` preflight step and the ROS line in the
  prompt, replacing neither
  - **Evidence:** the `Verify ROS command wrapper` step is absent and the prompt
    array ends at the "Do not push…" line;
    `grep -c 'AI_RESPONDERS\|enabled(\|codex'` and a grep for `ROS` over
    `ai-responder.yml` both return 0.
- [x] Add the `claude-respond` job in
  `container: ghcr.io/plume-works/agent-desktop:edge` with no `credentials:`
  (the package is public), keeping the artifact upload and the usage-limit check
  - **Evidence:** the `claude-respond` job declares that `container:` image with
    no `credentials:` key, and both the `Attach responder output file` upload
    and the `Fail on Claude usage limit` jq check are carried over.
- [x] Run `postCreateCommand.sh`, `postStartCommand.sh`, and
  `postAttachCommand.sh` as a job step after checkout and before the Claude
  action, with `AGENTDEV_SKIP_PRE_COMMIT` and `AGENTDEV_SKIP_XPRA` set —
  postAttach is what installs the catalog from this checkout and indexes CBM
  - **Evidence:** the `Run devcontainer lifecycle scripts` step sits between
    checkout and the Claude action, runs all three hooks in order with both
    `AGENTDEV_SKIP_*` set and `DEV_WORKSPACE_FOLDER` pointed at the checkout.
    Upstream's separate safe.directory step is dropped because
    `postStartCommand.sh` now calls `setup-git-safe-directory.sh` (Task 1); no
    script in the postCreate chain touches a git repository before it runs.
- [x] Keep upstream's `timeout-minutes: 30`; a cold CBM index is ~3.5s in this
  repo, so the lifecycle setup is not a meaningful share of the budget
  - **Evidence:** `claude-respond` carries `timeout-minutes: 30`, unchanged from
    upstream.
- [x] Confirm `actionlint` and `zizmor` pass on the new workflow
  - **Evidence:**
    `pre-commit run actionlint --files .github/workflows/ai-responder.yml` —
    Passed; `pre-commit run zizmor --files .github/workflows/ai-responder.yml` —
    Passed.

### Task 5: Import require-ai-review.yml verbatim

**Files:** Create: `.github/workflows/require-ai-review.yml`

- [x] Copy the upstream workflow unchanged, including both the Claude and Codex
  acceptance paths
  - **Evidence:** `diff` against the fetched upstream copy shows exactly one
    changed line — `actions/checkout` repinned from `v6.0.3` to this repo's
    `v7.0.1`, per the pin-everywhere constraint in `data/product.md`. Both
    `claudeLogins`/`codexLogins` sets, all three accepted review states, and the
    `+1`-reaction path are byte-identical to upstream.
- [x] Confirm `.github/actions/log-debug-stats` resolves for its final step
  - **Evidence:** `.github/actions/log-debug-stats/action.yml` exists and
    declares the `github-token` input the workflow's final step passes;
    actionlint resolves the local `./.github/actions/log-debug-stats` reference
    without error.
- [x] Confirm `actionlint` and `zizmor` pass on the new workflow
  - **Evidence:**
    `pre-commit run actionlint --files .github/workflows/require-ai-review.yml`
    — Passed;
    `pre-commit run zizmor --files .github/workflows/require-ai-review.yml` —
    Passed.

### Task 7: Chown only the mount points that exist

**Files:** Modify: `.devcontainer/scripts/postCreateCommand.sh`

`postCreateCommand.sh:35-37` chowns `$workspace/.cache` and `/uv`. Both exist in
a devcontainer only because `devcontainer.json:52-60` mounts them, so `set -e`
kills the script wherever they are absent.

Chowning only what exists keeps the devcontainer path identical in effect (every
target is a mount and always present there) while letting a mountless caller
proceed. Task 6 is blocked until this lands.

- [x] Make the `.cache` / `/uv` chown skip targets that do not exist, leaving
  ownership of present targets exactly as today
  - **Evidence:** `postCreateCommand.sh` now loops over both mount points and
    runs the identical `sudo chown -R root:root` only when `[[ -e ]]`, logging a
    skip otherwise.
- [x] Confirm `shellcheck` passes
  - **Evidence:** `shellcheck .devcontainer/scripts/postCreateCommand.sh` — exit
    0, no output.
- [x] Confirm the devcontainer path is unaffected: with both targets present,
  the same `chown` still runs against both
  - **Evidence:** the loop exercised against a temp workspace — with both
    targets created it selects both for chown (the devcontainer case); with
    neither created it skips both and continues instead of exiting 1.

### Task 8: Supply the devcontainer contract the hooks need

**Files:** Modify: `.github/workflows/ai-responder.yml`

The job supplies only `DEV_WORKSPACE_FOLDER`; the hooks also need
`CBM_CACHE_DIR` and `UV_PROJECT_ENVIRONMENT`, and two directories a volume
normally provides. The minimal contract and how it was derived are in
[CI agent plugin availability](../architecture/ci-agent-plugin-availability.md).

This changes the *workflow*, not the lifecycle scripts, so it stays inside the
Out of scope boundary. Whether the scripts should default these values
themselves is a separate question, deliberately not decided here.

- [x] Set `CBM_CACHE_DIR` and `UV_PROJECT_ENVIRONMENT` on the lifecycle step,
  alongside the existing `DEV_WORKSPACE_FOLDER` and the two `AGENTDEV_SKIP_*`
  guards
  - **Evidence:** both added to the step's `env:` in `ai-responder.yml`, with a
    comment recording why only these two of the eleven `containerEnv` variables
    are needed and which one fails silently.
- [x] Create `/root/.claude` and `/root/.codex` before running the hooks
  - **Evidence:** `mkdir -p /root/.claude /root/.codex` added as the step's
    first command; without it `postCreateCommand.sh:67` fails with
    `/root/.claude/claude.json: No such file or directory`, reproduced locally.
- [x] Confirm the whole sequence passes locally through
  `.devcontainer/scripts/ci-hooks-repro.sh` with no volumes and no `.venv` leak
  - **Evidence:** harness added and run against
    `ghcr.io/plume-works/agent-desktop:pr-41` — exit 0 with all three hooks OK
    and `ok: no .venv in the checkout`. `BARE=1` (contract withheld) exits 1 on
    `CBM_CACHE_DIR: unbound variable`, so the harness reproduces the failure and
    the fix in both directions.
- [x] Confirm `actionlint` and `zizmor` still pass
  - **Evidence:**
    `pre-commit run actionlint --files .github/workflows/ai-responder.yml` —
    Passed; same for `zizmor`.

### Task 6: Prove the responder runs green, then require the gate

**Files:** none — CI and repository settings

Stands alone: its evidence is a CI run on a real PR plus a branch-protection
change, neither of which the session writing Tasks 4-5 can produce.

How to trigger a run matters here. The `pull_request` triggers are `opened`,
`reopened`, `assigned`, and `ready_for_review` — deliberately not `synchronize`
— so pushing does not re-run the responder; reopen the PR or toggle draft/ready.
Commenting `@claude review` will not work until these files are on the default
branch, because GitHub resolves `issue_comment` against the workflow file there.
Comment-driven behavior is therefore only testable after merge.

- [x] Trigger the responder on a real PR and confirm it posts a review, with the
  job log showing `agentdev:pr-review` resolved rather than improvised
  - **Evidence:** run `31994816348` on PR #65 (commit `1bb8c62`) posted a
    `COMMENTED` review as `github-actions[bot]` at 2026-08-17T04:46:04Z with
    three inline comments; its body opens "Automated review via
    `agentdev:pr-review`. Four independent passes…", and the review dropped two
    candidates as refuted — improvised output does not validate and discard its
    own findings. Took two attempts: run `31992249608` went green having posted
    nothing because the prompt asked for "the pr-review skill" unqualified,
    which resolved to Claude Code's built-in `code-review` skill
    (`Skill(skill: "code-review")` in that log) whose `ReportFindings` reporting
    is a no-op in a headless action; commit `e385672` names `agentdev:pr-review`
    explicitly.
- [x] Confirm `ai-review-present` passes on that PR
  - **Evidence:** `ai-review-present` passes on PR #65 (run `32010195815`),
    satisfied by the responder's own review. Two reviews from
    `github-actions[bot]` back it: the original at 2026-08-17T04:46:04Z
    (`pull_request` event, run `31994816348`) and a second at
    2026-08-17T08:44:25Z from run `32009898440` on a `pull_request_review`
    event. The second exercises the `isReview` fix in commit `4aa9835`: its job
    log records `EVENT TYPE: pull_request_review` with the qualified
    `agentdev:pr-review` prompt, which before the fix would have been the
    freeform review body. Both review bodies carry the `agentdev:pr-review`
    signature — independent passes, deduplication, and candidates refuted during
    validation.
- [x] Only then add `ai-review-present` to the branch protection required checks
  - **Evidence:** `ai-review-present` is an active required status check in the
    `main` branch ruleset (`gh api repos/:owner/:repo/rulesets/20021618` lists
    it alongside `CI/CD / CI finished` and `Agent files validation finished`);
    the ruleset's `enforcement` is `active`.

## Spec changes

[Catalog lifecycle](../spec/catalog-lifecycle.md) is **unchanged**. An earlier
revision of this plan would have reversed its first requirement by installing
the catalog at image build time; using the checkout instead leaves every
requirement in that spec exactly as written, including the attach-time workspace
override this plan now depends on.

The lifecycle scripts do gain skip guards, but they default to today's behavior
and change nothing observable in a devcontainer — no requirement in that spec
describes them.

New behavior for the workflows themselves goes in a new spec,
[AI review gate](../spec/ai-review-gate.md), created at ship time:

``` markdown
## ADDED Requirements

### Requirement: PRs are blocked until an AI review exists

A pull request SHALL NOT be mergeable until either Claude or Codex has reviewed
it. The `ai-review-present` check SHALL accept a review from `claude[bot]` or
`github-actions[bot]`, a review from `chatgpt-codex-connector[bot]`, or a `+1`
reaction from `chatgpt-codex-connector[bot]`, in state `approved`,
`changes_requested`, or `commented`.

The check SHALL NOT require that the review name the pull request's current head
commit. It asserts that the pull request has been reviewed, not that each pushed
commit has been: reviewing every commit is prohibitively expensive, and neither
AI nor human reviewers work that way. Refreshing a review is the author's call,
requested with an `@claude review` comment the way a human re-review is
re-requested.

#### Scenario: a reviewed PR receives a further push

- **WHEN** an accepted AI review exists on the pull request and the author
  pushes a commit after it
- **THEN** `ai-review-present` still passes, and the review is refreshed only
  when the author asks for one.

#### Scenario: Claude reviews a PR through the responder workflow

- **WHEN** `ai-responder.yml` posts a review on a pull request
- **THEN** `ai-review-present` passes.

#### Scenario: Codex reviews a PR through Codex web

- **WHEN** a maintainer runs a Codex review outside GitHub Actions and it posts
  as `chatgpt-codex-connector[bot]`
- **THEN** `ai-review-present` passes.

#### Scenario: no AI has reviewed within the polling window

- **WHEN** neither a Claude nor a Codex review appears within 8 minutes
- **THEN** `ai-review-present` fails, blocking merge.

### Requirement: the responder only acts for authorized same-repository requests

The responder SHALL NOT check out or execute code for a pull request originating
from a fork, and SHALL NOT act on a request from an actor without write access.

#### Scenario: a fork PR triggers the responder

- **WHEN** the pull request head repository differs from the workflow repository
- **THEN** preflight records the fork and every responder job is skipped before
  any checkout.

#### Scenario: a user without write access mentions @claude

- **WHEN** the requesting actor's permission is not `admin`, `maintain`, or
  `write`
- **THEN** preflight fails and no responder job runs.
```

## Depends on

None — no active plan touches CI workflows or the devcontainer lifecycle
scripts.

## Verification

- `shellcheck` passes on every modified script, via the pre-commit hooks or
  `/agentdev:local-reformat` (Tasks 1-2).
- A devcontainer starts unchanged with neither guard set: pre-commit hooks are
  installed and Xpra runs, exactly as today (Task 2).
- `actionlint` and `zizmor` pass on both new workflows.
- `.devcontainer/scripts/ci-hooks-repro.sh` exits 0 — all three hooks pass in a
  bare `container:`-shaped run with no volumes, and no `.venv` is written into
  the checkout. `BARE=1` exits 1, confirming the harness still detects the
  regression it was built for (Tasks 7-8).
- The responder posts a review on a real PR, its log showing the `pr-review`
  skill resolved from **this checkout** rather than improvised, and CBM indexed
  (Task 6).
- `ai-review-present` passes on that PR before it is made a required check (Task
  6).

## Out of scope

- **Loosening the gate's acceptance rules.** The `+1`-reaction path and the
  `commented` state are weak — nearly any bot comment satisfies the check. That
  is upstream's design; changing it during an import would conflate two
  decisions.
- **Requiring the review to name the current head SHA.** Filed as a backlog item
  on 2026-08-17 and withdrawn on maintainer review the same day: it mistook what
  the gate is for. Accepting an earlier review is the intended behavior, not a
  defect — see the requirement above.
- **A Codex responder job in CI.** Codex reviews come from Codex web.
- **Installing the catalog into the image.** Considered and rejected: the
  responder checks out the branch, so the checkout's catalog is both available
  and more correct than the image's.
- **Changing what the lifecycle scripts do when unguarded** — with one exception
  added after the first CI run (Task 7): `postCreateCommand.sh` may skip a
  `chown` whose target does not exist. In a devcontainer every such target is a
  mount and always exists, so the devcontainer path stays byte-identical in
  effect; only an environment that never had the mount behaves differently, and
  there the current behavior is an unconditional failure. No other change to
  unguarded behavior is in scope.
- **Renovate, branch-protection automation, or importing any other Dr-QP
  workflow.**

## Key references

Verified anchor points (line numbers as of 2026-08-17):

- `.devcontainer/scripts/postAttachCommand.sh:8` —
  `codebase-memory-mcp-index.sh`; a cold index measures ~3.5s in this repository
- `.devcontainer/scripts/postAttachCommand.sh:14-15` — the checkout-scoped
  catalog reinstall; this, not postCreate, is what gives the responder the
  branch's own skills
- `.devcontainer/scripts/postStartCommand.sh:9` —
  `codebase-memory-mcp-start.sh`, which starts CBM but does not index
- `.devcontainer/scripts/postStartCommand.sh:11` —
  `setup-git-safe-directory.sh`, the split-out call added by Task 1
- `.devcontainer/scripts/postStartCommand.sh:12` — `setup-pre-commit.sh`, the
  call site the `AGENTDEV_SKIP_PRE_COMMIT` guard protects
- `.devcontainer/scripts/postStartCommand.sh:16-21` — the `AGENTDEV_SKIP_XPRA`
  guard around `/start-xpra.sh --background`
- `.devcontainer/scripts/setup-git-safe-directory.sh:11` —
  `git config --global --add safe.directory`, the call a CI checkout needs and
  the pre-commit guard must not skip
- `.devcontainer/scripts/setup-pre-commit.sh:11-14` — the
  `AGENTDEV_SKIP_PRE_COMMIT` early exit
- `.devcontainer/scripts/setup-pre-commit.sh:20` —
  `pre-commit install --install-hooks`, the minutes-long step
- `.devcontainer/scripts/setup-keyring.sh:99-105` — the graceful skip that makes
  a keyring guard unnecessary
- `.devcontainer/scripts/reinstall-agentdev-claude.sh:14-15` — the no-argument
  default that resolves the catalog root to this checkout
- `.github/workflows/ci.yml:31` — `DESKTOP_IMAGE_NAME: agent-desktop`, the image
  the responder job runs in
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:22` — the
  `CBM_CACHE_DIR` dereference that fails under `set -u` when unset
- `.devcontainer/scripts/postCreateCommand.sh:63-69` — the `claude.json` write
  that assumes `/root/.claude` exists
- `.devcontainer/scripts/uv-sync.sh:32` — `uv sync`, which silently creates an
  in-tree `.venv` when `UV_PROJECT_ENVIRONMENT` is unset
- `.devcontainer/devcontainer.json:33` — `CBM_CACHE_DIR` in `containerEnv`, the
  devcontainer-only source of the contract a `container:` job must supply itself
- `.devcontainer/scripts/ci-hooks-repro.sh` — the local `container:`
  reproduction
- `.github/workflows/ai-responder.yml` — the imported Claude-only responder
- `.github/workflows/require-ai-review.yml` — the imported `ai-review-present`
  gate
