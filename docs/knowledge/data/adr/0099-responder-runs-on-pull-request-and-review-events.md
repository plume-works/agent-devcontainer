---
type: adr
stage: accepted
supersedes:
- adr/0065-responder-runs-only-on-pull-request-events
---

# The review responder workflow runs only on pull request and review events

The review responder workflow starts only on `pull_request` and
`pull_request_review` events. The repository uses no merge queue, so the
workflow has no `merge_group` trigger. Each run then runs the copy of the
workflow in the pull request. No trigger gives a run the privileges of the
default branch, and no job needs contents write.

## Considered Options

- A free-form `@claude <prompt>` responder. Rejected: it needs contents write, a
  dispatch onto the head branch, and a path to send the identity of the
  requester between runs.
- A review that a comment requests and that `workflow_dispatch` starts on the
  head branch. Rejected: neither the `main` ruleset nor the status rollup counts
  the checks of a `workflow_dispatch` run, the actor of that run is
  `github-actions[bot]`, not the requester, and it needs `allowed_bots` opened
  on `claude-code-action`.

## Consequences

- The preflight job checks the write access of `github.actor` of the event,
  which is the person who pushed, opened the pull request, or changed a label.
  No run sends an identity to a different run, so `claude-code-action` needs no
  `allowed_bots`.
- No responder job pushes, so no ruleset needs the responder as a bypass actor.
- No run gets the privileges of the default branch, so the `dangerous-triggers`
  audit of zizmor needs no exception.
