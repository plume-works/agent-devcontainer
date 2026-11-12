---
type: architecture
description: The AI responder runs only on pull request, pull request review, and merge group events; the free-form @claude task responder, the comment bridge, and the @claude review rejection reply are removed, superseding dispatched-review identity.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: zizmor.yaml
- resource: data/plans/20261107-drop-claude-task-responder.md
---

# Pull-request-only AI responder

## Context

The maintainer decided on 2026-11-07 to:

- remove the free-form `@claude <prompt>` task responder;
- remove the `@claude review` rejection reply with it, so a comment opening with
  `@claude` starts no run.

Reviews are requested by assignment, as [Assignee-triggered AI
re-reviews](../../2.0.0/architecture/assignee-review-trigger.md) records, so a
comment no longer has anything to request.

## Decision

`ai-responder.yml` triggers only on `pull_request`, `pull_request_review`, and
`merge_group`. It has no `issue_comment`, `pull_request_review_comment`,
`issues`, or `workflow_dispatch` trigger, no job that bridges a comment to the
head branch, and no job with `contents: write`.

Consequences:

- Every run executes the pull request's own copy of the workflow, so no run is
  privileged by a default-branch trigger, and zizmor's `dangerous-triggers`
  needs no exception.
- Preflight authorizes `github.actor` of the `pull_request` event — the person
  who pushed, opened, or assigned. No identity is forwarded between runs, so
  `claude-code-action` needs no `allowed_bots`.
- No responder job pushes, so no ruleset needs the responder as a bypass actor.

This supersedes [Dispatched review
identity](../../1.0.0/architecture/dispatched-review-identity.md).

## Rejected alternatives

- **Keep the `@claude review` rejection reply**: it keeps a privileged comment
  trigger and a job on every `@claude` comment, only to redirect a request the
  assignee toggle already covers.
- **Keep the task responder, review-only by default**: the task path is what
  needs `contents: write`, the bridge, and requester forwarding; keeping it
  keeps all three.
