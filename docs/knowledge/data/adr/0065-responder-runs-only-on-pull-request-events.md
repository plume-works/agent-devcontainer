---
type: adr
stage: accepted
description: The review responder workflow has no comment or dispatch trigger, so each run executes the workflow from the pull request and no job needs contents write.
---

# The review responder workflow runs only on pull request events

The review responder workflow starts only on `pull_request`,
`pull_request_review`, and `merge_group` events. Each run then executes the copy
of the workflow in the pull request. No trigger gives a run the privileges of
the default branch, and no job needs contents write.

## Considered Options

- A free-form `@claude <prompt>` responder. Rejected: it needs contents write, a
  dispatch onto the head branch, and a path to send the identity of the
  requester between runs.
- A review that a comment requests, dispatched onto the head branch. Rejected:
  the `main` ruleset does not count the checks of a `workflow_dispatch` run, and
  the actor of that run is `github-actions[bot]`, not the requester.
- A reply that refuses `@claude review` comments. Rejected: it keeps a
  privileged comment trigger only to send a request to the label, which already
  does the same work.
- Keep the task responder, with reviews only as the default. Rejected: the task
  path is the part that needs contents write, the dispatch, and the identity of
  the requester between runs.

## Consequences

- Preflight checks the write access of `github.actor` of the event, which is the
  person who pushed, opened the pull request, or changed a label. No run sends
  an identity to a different run, so `claude-code-action` needs no
  `allowed_bots`.
- No responder job pushes, so no ruleset needs the responder as a bypass actor.
- No run gets the privileges of the default branch, so the `dangerous-triggers`
  audit of zizmor needs no exception.
