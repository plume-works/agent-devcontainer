---
type: plan
created: 2026-11-22
release: internal
description: Build quill-as-a-service, a GitHub App service that reviews the pull requests of the repositories it lists in reviewer containers, and onboard plume-works/images.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/review-gate.js
- resource: .agents/plugins/agentdev/skills/pr-review/agent-code/post-review.py
- resource: docker/deploy/README.md
---

# Build quill-as-a-service

## Context

The AI review runs today as `.github/workflows/ai-responder.yml` with two
actions. Each repository that wants it keeps a copy of the workflow, its
actions, an environment, secrets, and labels, and each review replays the Dev
Container lifecycle from the pull request's checkout. The user decided to
replace the workflow with a deployed service that reviews the pull requests of
repositories where its GitHub App is installed. The service is a review service
in its own right; it does not carry over the workflow's per-repository copies,
environments, or Dev Container lifecycle replay.

The service lives in a new repository, `plume-works/quill-as-a-service`. Its
code cannot be anchored or tested from this checkout, so this plan names the
files it creates there, and its `## Verification` clones that repository and
runs its tests. Its first user is `plume-works/images`. [Switch this
repository's AI review to
quill-as-a-service](20261122-switch-agentdev-review-to-quill.md) follows once
this plan ships.

## Approach

The repository builds two images.

- The **reviewer image**, `FROM ghcr.io/plume-works/core`, installs the
  `agentdev` plugin of `plume-works/agent-devcontainer` at a pinned commit, and
  the reviewer settings. Its entry command checks out one head commit and runs
  Claude Code headless with the review prompt; the review posts through
  `pr-review`'s `post-review.py`. It exits non-zero when Claude fails or hits
  the spend limit.
- The **service image**, `FROM ghcr.io/plume-works/core-systemd`, runs under
  sysbox behind the reverse proxy of `docker/deploy/README.md`. A Bun server
  verifies each webhook of the Quill App, keeps only `pull_request` events of
  repositories in its configuration, decides, and runs reviewer containers on
  its nested engine through a queue.

The configuration holds the repositories to review, the trusted bots, a pause
switch, and the maximum number of concurrent reviews (default 5). Secrets — the
App private key, the webhook secret, and the Claude OAuth token — sit in an env
file on the host. Each reviewer container gets an installation token limited to
its one repository and the Claude token, never the App key.

Reviewer containers run without `--rm`: a finished container is the review's
log, transcript included. core-systemd's daily cleanup removes it once it has
been stopped for a week, at the ages the service image sets
([plume-works/images#79](https://github.com/plume-works/images/pull/79)).

Review rules ([ADR-0103](../adr/0103-review-starts-on-open-or-request.md)): a
same-repository pull request that opens, is reopened, or leaves draft, or gets
`request-ai-review` from a person with write access, is reviewed, unless it is a
draft, is from a bot, carries `block-ai-reviews`, or the service is paused. A
push while the label is on cancels the running review of that pull request and
queues one for the new head. A pull request has at most one review at a time: a
new one cancels the earlier one first. Each review creates a `Quill Review`
check run on its head when it is queued, sets it in progress when its container
starts, and completes it with the container's outcome. On start the review
dismisses Quill's earlier approval and leaves an earlier change request. After a
successful or failed review, the service removes `request-ai-review`; a
cancelled review leaves it.

Bypass auto-approvals
([ADR-0102](../adr/0102-required-approval-is-the-only-ai-review-gate.md)) port
`review-gate.js::botApprovalFailure`: a pull request from a configured trusted
bot whose every push and commit is the bot's is approved without a review, and
an earlier approval is dismissed when that stops holding.

Assumptions: the check run is named `Quill Review`; a review container is
stopped after 30 minutes, as the workflow's `timeout-minutes: 30`; the review
prompt is the one `.github/workflows/ai-responder.yml#jobs.preflight` builds in
its "Determine agent prompts" step.

## Implementation Steps

### Task 1: Create the repository

**Closed by:** a maintainer of the `plume-works` organization.

- [x] `plume-works/quill-as-a-service` exists.
- [x] Renovate is enabled on `plume-works/quill-as-a-service`.

### Task 2: Configure the Quill App

**Closed by:** a maintainer of the `plume-works` organization.

- [ ] The Quill App has the Checks: write permission.
- [ ] The Quill App is subscribed to `pull_request` events and sends them to the
  service's URL with a webhook secret.

### Task 3: Build the reviewer image

**Files:** Create: `reviewer/Dockerfile`, `reviewer/settings.json`,
`reviewer/review.sh`, `test/reviewer.test.ts`

- [x] `reviewer/Dockerfile` builds `FROM ghcr.io/plume-works/core` by tag and
  digest and installs the `agentdev` plugin from
  `plume-works/agent-devcontainer` at a pinned commit SHA.
- [x] `reviewer/settings.json` enables the `agentdev` plugin and denies the
  tools that
  `.github/workflows/ai-responder.yml#env.CLAUDE_PR_REVIEW_DISALLOWED_TOOLS`
  denies.
- [x] `reviewer/review.sh` checks out the given head SHA and runs Claude Code
  headless with the review prompt; `bun test test/reviewer.test.ts` passes with
  a stubbed `claude`.
- [x] With a stubbed `claude` that exits non-zero, `reviewer/review.sh` exits
  non-zero; `bun test test/reviewer.test.ts` passes.
- [ ] With a stubbed `claude` that exits 0 and prints the spend-limit message,
  `reviewer/review.sh` exits non-zero; `bun test test/reviewer.test.ts` passes.
- [ ] With a stubbed `claude` whose plugin list has no `agentdev` plugin,
  `reviewer/review.sh` exits non-zero before it starts a review;
  `bun test test/reviewer.test.ts` passes.

### Task 4: Load the configuration

**Files:** Create: `src/config.ts`, `test/config.test.ts`

- [ ] `src/config.ts` reads the repositories, trusted bots, pause switch, and
  maximum concurrent reviews, with 5 as the default maximum;
  `bun test test/config.test.ts` passes.

### Task 5: Take signed webhooks

**Files:** Create: `src/server.ts`, `src/webhook.ts`, `test/webhook.test.ts`

- [ ] A delivery whose signature does not match the webhook secret gets 401;
  `bun test test/webhook.test.ts` passes.
- [ ] An event other than `pull_request` is ignored;
  `bun test test/webhook.test.ts` passes.
- [ ] A `pull_request` event from a repository not in the configuration is
  ignored; `bun test test/webhook.test.ts` passes.

### Task 6: Decide whether to review

**Files:** Create: `src/decide.ts`, `test/decide.test.ts`

- [ ] A same-repository pull request that opens is reviewed;
  `bun test test/decide.test.ts` passes.
- [ ] A same-repository pull request that is reopened is reviewed;
  `bun test test/decide.test.ts` passes.
- [ ] A same-repository pull request that leaves draft is reviewed;
  `bun test test/decide.test.ts` passes.
- [ ] `request-ai-review` added by a person with write, maintain, or admin
  access is reviewed; `bun test test/decide.test.ts` passes.
- [ ] `request-ai-review` added by a person without that access is not reviewed;
  `bun test test/decide.test.ts` passes.
- [ ] A pull request from a fork is not reviewed; `bun test test/decide.test.ts`
  passes.
- [ ] A draft pull request is not reviewed; `bun test test/decide.test.ts`
  passes.
- [ ] A pull request from a bot author is not reviewed;
  `bun test test/decide.test.ts` passes.
- [ ] A pull request carrying `block-ai-reviews` is not reviewed;
  `bun test test/decide.test.ts` passes.
- [ ] No pull request is reviewed while the configuration pauses the service;
  `bun test test/decide.test.ts` passes.

### Task 7: Run reviews through a queue

**Files:** Create: `src/queue.ts`, `src/reviewer.ts`, `test/queue.test.ts`

- [ ] `src/queue.ts` runs at most the configured number of reviews at once;
  `bun test test/queue.test.ts` passes.
- [ ] When a review ends, the oldest waiting review starts;
  `bun test test/queue.test.ts` passes.
- [ ] A push while `request-ai-review` is on cancels the running review of that
  pull request; `bun test test/queue.test.ts` passes.
- [ ] A push while `request-ai-review` is on cancels the waiting review of that
  pull request; `bun test test/queue.test.ts` passes.
- [ ] That push queues a review of the new head; `bun test test/queue.test.ts`
  passes.
- [ ] A review queued for a pull request that already has a running or waiting
  review, provoked by opening the pull request and then adding
  `request-ai-review`, cancels the earlier review before it is queued;
  `bun test test/queue.test.ts` passes.
- [ ] `src/reviewer.ts` asks for an installation token limited to the one
  repository; `bun test test/queue.test.ts` passes.
- [ ] A reviewer container still running after 30 minutes is stopped, provoked
  in the test with a fake clock and a container that never exits;
  `bun test test/queue.test.ts` passes.
- [ ] `src/reviewer.ts` starts each reviewer container without `--rm`, so it
  stays after it ends; `bun test test/queue.test.ts` passes.

### Task 8: Report each review as a check run

**Files:** Create: `src/review.ts`, `test/review.test.ts`

- [ ] A queued review creates a queued `Quill Review` check run on its head;
  `bun test test/review.test.ts` passes.
- [ ] The check run turns in progress when the container starts;
  `bun test test/review.test.ts` passes.
- [ ] A container that exits 0 completes the check run as success;
  `bun test test/review.test.ts` passes.
- [ ] A container that exits non-zero completes the check run as failure;
  `bun test test/review.test.ts` passes.
- [ ] A container stopped at the timeout, provoked in the test with a fake clock
  and a container that never exits, completes the check run as failure;
  `bun test test/review.test.ts` passes.
- [ ] A review cancelled by a push completes the check run as cancelled;
  `bun test test/review.test.ts` passes.
- [ ] A starting review dismisses Quill's earlier approval and leaves an earlier
  change request; `bun test test/review.test.ts` passes.
- [ ] A review that ends with success removes `request-ai-review`;
  `bun test test/review.test.ts` passes.
- [ ] A review that ends with failure removes `request-ai-review`;
  `bun test test/review.test.ts` passes.
- [ ] A review cancelled by a push leaves `request-ai-review`;
  `bun test test/review.test.ts` passes.

### Task 9: Approve trusted-bot pull requests

**Files:** Create: `src/approve.ts`, `test/approve.test.ts`

- [ ] A pull request from a configured trusted bot whose every push and commit
  satisfies `review-gate.js::botApprovalFailure`'s rule is approved once by
  Quill; `bun test test/approve.test.ts` passes.
- [ ] A push from anyone other than the bot dismisses Quill's approval;
  `bun test test/approve.test.ts` passes.
- [ ] A commit authored by anyone other than the bot dismisses Quill's approval;
  `bun test test/approve.test.ts` passes.
- [ ] `test/approve.test.ts` carries the cases of
  `.github/actions/ai-review-status/review-gate.test.js` that cover
  `botApprovalFailure`.

### Task 10: Build the service image

**Files:** Create: `service/Dockerfile`

- [ ] `service/Dockerfile` builds `FROM ghcr.io/plume-works/core-systemd` by tag
  and digest and runs the Bun server as a systemd unit.
- [ ] `service/Dockerfile` pins a `core-systemd` that has the configurable
  cleanup of
  [plume-works/images#79](https://github.com/plume-works/images/pull/79) and
  installs a `docker-prune.service.d` drop-in that sets every `PRUNE_*` setting:
  `168h` for stopped containers, anonymous volumes, images and build cache,
  `off` for named volumes.

### Task 11: Write the deployment

**Files:** Create: `compose.yml`, `service.env.example`, `docs/deploy.md`

- [ ] `compose.yml` runs the service image under the sysbox runtime on the proxy
  network and publishes no host port.
- [ ] `docs/deploy.md` gives the steps from an empty host to a running service.

### Task 12: Build and test in CI

**Files:** Create: `.github/workflows/ci.yml`

- [ ] `.github/workflows/ci.yml` runs `bun test` on pull requests.
- [ ] `.github/workflows/ci.yml` builds both images on pull requests.
- [ ] `.github/workflows/ci.yml` publishes both images to `ghcr.io/plume-works`
  only from `main`.

### Task 13: Keep the pins current

**Files:** Create: `renovate.json`

- [ ] `renovate.json` has rules that match the `core` and `core-systemd` digests
  and the `agent-devcontainer` commit pin.

### Task 14: Publish the images

**Closed by:** the first CI run on `main` of `plume-works/quill-as-a-service`.

- [ ] The service image and the reviewer image are on `ghcr.io/plume-works`.

### Task 15: Deploy the service

**Closed by:** a maintainer deploying the service on a sysbox host.

- [ ] The service answers the Quill App's webhook deliveries with success.

### Task 16: Onboard plume-works/images

**Closed by:** a maintainer adding `plume-works/images` to the configuration and
installing the Quill App on it, then watching its pull requests.

- [ ] A pull request opened on `plume-works/images` gets a review by
  `plume-works-quill[bot]`.
- [ ] That pull request gets a completed `Quill Review` check on its head.
- [ ] Adding `request-ai-review` starts a review.
- [ ] The label is gone when that review ends.
- [ ] A push while `request-ai-review` is on cancels the running review.
- [ ] A review of the new head follows that push.
- [ ] After Quill approves a pull request, adding `request-ai-review` starts a
  review that dismisses that approval.
- [ ] A Renovate pull request is approved by Quill without a review.

## Acceptance

### Scenario: An unsigned delivery is refused

- **WHEN** a webhook delivery's signature does not match the webhook secret
- **THEN** the service answers 401 and acts on nothing
- **Test:** `test/webhook.test.ts::rejects a delivery with a bad signature`

### Scenario: A repository outside the configuration is ignored

- **WHEN** a `pull_request` event comes from a repository that has the App
  installed but is not in the configuration
- **THEN** no review is queued and no check run is created
- **Test:**
  `test/webhook.test.ts::ignores a repository outside the configuration`

### Scenario: Opening a pull request starts a review

- **WHEN** a same-repository pull request that is not a draft opens, is
  reopened, or leaves draft
- **THEN** a review of its head is queued
- **Test:**
  `test/decide.test.ts::reviews on opened, reopened, and ready_for_review`

### Scenario: The request label from a writer starts a review

- **WHEN** a person with write, maintain, or admin access adds
  `request-ai-review`
- **THEN** a review of the head is queued, and a person without that access
  adding the label queues nothing
- **Test:**
  `test/decide.test.ts::reviews on the request label from a writer only`

### Scenario: Forks, drafts, and bots get no review

- **WHEN** a pull request comes from a fork, is a draft, or is authored by a bot
- **THEN** no review is queued
- **Test:** `test/decide.test.ts::skips forks, drafts, and bot authors`

### Scenario: The block label and the pause switch stop reviews

- **WHEN** the pull request carries `block-ai-reviews`, or the configuration
  pauses the service
- **THEN** no review is queued
- **Test:**
  `test/decide.test.ts::skips blocked pull requests and a paused service`

### Scenario: A pull request has at most one review at a time

- **WHEN** a review is queued for a pull request that already has a running or
  waiting review
- **THEN** the earlier review is cancelled first, so it leaves
  `request-ai-review` on and only the newest review removes it
- **Test:**
  `test/queue.test.ts::a new review of a pull request cancels its earlier review`

### Scenario: A finished reviewer container is kept

- **WHEN** a review ends with success or failure, is stopped at the timeout, or
  is cancelled
- **THEN** its reviewer container stays on the service's engine, transcript
  included, until core-systemd's cleanup removes it
- **Test:** `test/queue.test.ts::a reviewer container is started without --rm`

### Scenario: A push during a requested review restarts it

- **WHEN** a push arrives while `request-ai-review` is on the pull request
- **THEN** the running or waiting review of that pull request is cancelled and a
  review of the new head is queued
- **Test:**
  `test/queue.test.ts::a push with the label on restarts the review on the new head`

### Scenario: Reviews beyond the limit wait

- **WHEN** more reviews are queued than the configured maximum, 5 by default
- **THEN** only the maximum run at once, the others wait with a queued check
  run, and the oldest waiting one starts when a running one ends
- **Test:**
  `test/queue.test.ts::runs at most the maximum and starts the oldest waiting`

### Scenario: Each review reports a check run on its head

- **WHEN** a review is queued, starts, and ends
- **THEN** its `Quill Review` check run on the reviewed head goes queued, in
  progress, and completes as success for exit 0, failure for a non-zero exit or
  the 30-minute timeout, and cancelled when it was cancelled
- **Test:** `test/review.test.ts::the check run follows the review`

### Scenario: A new review dismisses Quill's earlier approval

- **WHEN** a review starts on a pull request where Quill's latest review
  approved, or requested changes
- **THEN** the approval is dismissed, and the change request stays
- **Test:**
  `test/review.test.ts::a starting review dismisses the earlier approval only`

### Scenario: The request label is taken when the review ends

- **WHEN** a review ends with success or failure, or is cancelled
- **THEN** the service removes `request-ai-review` after success or failure, and
  leaves it after a cancel
- **Test:**
  `test/review.test.ts::the label is removed after success or failure only`

### Scenario: A trusted bot's pull request is approved without a review

- **WHEN** a pull request from a configured trusted bot has only the bot's
  pushes and the bot's verified commits, or gains a push or commit from anyone
  else
- **THEN** Quill approves it once without a review, and in the second case
  dismisses that approval
- **Test:**
  `test/approve.test.ts::approves a trusted bot and withdraws on a foreign push`

### Scenario: The reviewer fails on the spend limit

- **WHEN** Claude reports the organization's spend limit during a review
- **THEN** `reviewer/review.sh` exits non-zero, so the check run fails
- **Test:** `test/reviewer.test.ts::exits non-zero on the spend limit`

### Scenario: The reviewer refuses to review without its catalog

- **WHEN** the `agentdev` plugin, and with it `agentdev:pr-review`, is not
  available in the reviewer container
- **THEN** `reviewer/review.sh` exits non-zero before Claude reviews, so no
  review or approval posts and the check run fails
- **Test:**
  `test/reviewer.test.ts::exits non-zero when the agentdev plugin is missing`

### Scenario: The reviewer posts a review of the head

- **WHEN** the reviewer image runs for a pull request on `plume-works/images`
- **THEN** a review by `plume-works-quill[bot]` names the head commit
- **Checked at ship:**
  `docs/knowledge/data/plans/20261122-quill-as-a-service.md#task-16-onboard-plume-worksimages`

## Verification

The code lives in `plume-works/quill-as-a-service`, outside this checkout. The
verifier clones it into `./.tmp` and runs every test that `## Acceptance` names:

``` bash
git clone --depth 1 https://github.com/plume-works/quill-as-a-service ./.tmp/quill-as-a-service
cd ./.tmp/quill-as-a-service && bun install --frozen-lockfile && bun test
```

## Out of scope

- Switching this repository from the workflow to the service; [Switch this
  repository's AI review to
  quill-as-a-service](20261122-switch-agentdev-review-to-quill.md) holds it.
- `merge_group` events; the service checks pull request heads only.
- Comment and mention triggers, and reviews on each push.
- Keeping review transcripts beyond the container's lifetime.
- Pull requests from forks.

## Key references

- `.github/actions/ai-review-status/review-gate.js::botApprovalFailure` — the
  bypass auto-approval rule that Task 9 ports.
- `.github/actions/ai-review-status/review-gate.js::wantsReview` — today's label
  decision, background for Task 6.
- `.github/actions/ai-review-status/review-gate.test.js` — the cases Task 9
  keeps.
- `.github/workflows/ai-responder.yml#jobs.trusted-bot-approval` › "Approve on
  behalf of the trusted bot" — how the approval reads the push history and
  commits.
- `.github/workflows/ai-responder.yml#jobs.preflight` › "Determine agent
  prompts" — the review prompt.
- `.github/workflows/ai-responder.yml#env.CLAUDE_PR_REVIEW_DISALLOWED_TOOLS` —
  the tools the reviewer settings deny.
- `.github/actions/run-claude-responder/action.yml` › "Fail on Claude usage
  limit" — the spend-limit message the reviewer detects.
- `.agents/plugins/agentdev/skills/pr-review/agent-code/post-review.py` — how
  the review posts without `claude-code-action`.
- `docker/deploy/README.md#1-create-the-proxy-network` — the reverse-proxy
  pattern the deployment follows.
