---
type: spec
description: How the required AI review gate accepts a review and when the responder is allowed to act on a pull request.
generated:
  by: claude-code/opus-4-8
  at: 2026-08-31T00:00:00Z
sources:
- resource: .github/workflows/require-ai-review.yml
- resource: .github/workflows/ai-responder.yml
---

# AI review gate

## Requirement: PRs are blocked until an AI review exists

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

### Scenario: a reviewed PR receives a further push

- **WHEN** an accepted AI review exists on the pull request and the author
  pushes a commit after it
- **THEN** `ai-review-present` still passes, and the review is refreshed only
  when the author asks for one.

### Scenario: Claude reviews a PR through the responder workflow

- **WHEN** `ai-responder.yml` posts a review on a pull request
- **THEN** `ai-review-present` passes.

### Scenario: Codex reviews a PR through Codex web

- **WHEN** a maintainer runs a Codex review outside GitHub Actions and it posts
  as `chatgpt-codex-connector[bot]`
- **THEN** `ai-review-present` passes.

### Scenario: no AI has reviewed within the polling window

- **WHEN** neither a Claude nor a Codex review appears within 8 minutes
- **THEN** `ai-review-present` fails, blocking merge.

## Requirement: the responder only acts for authorized same-repository requests

The responder SHALL NOT check out or execute code for a pull request originating
from a fork, and SHALL NOT act on a request from an actor without write access.

### Scenario: a fork PR triggers the responder

- **WHEN** the pull request head repository differs from the workflow repository
- **THEN** preflight records the fork and every responder job is skipped before
  any checkout.

### Scenario: a user without write access mentions @claude

- **WHEN** the requesting actor's permission is not `admin`, `maintain`, or
  `write`
- **THEN** preflight fails and no responder job runs.
