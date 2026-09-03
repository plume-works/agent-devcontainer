---
type: architecture
description: A bridged review runs as github-actions[bot], so requester authorization is carried in a forwarded input rather than read from github.actor; two separate bot gates must be opened for a comment-requested review to run.
generated:
  by: claude-code/opus-5
  at: 2026-09-03T16:05:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event
- resource: https://github.com/anthropics/claude-code-action
---

# Dispatched review identity

## Decision

A comment-requested review is dispatched onto the pull request head branch, so
the run that performs the review is a `workflow_dispatch` issued by this
repository's own `GITHUB_TOKEN`. Its `github.actor` is therefore
`github-actions[bot]`, never the person who asked.

Authorization is carried explicitly instead of inferred from the actor:

- the bridge forwards the commenter's login as the `requester` dispatch input;
- `Authorize responder requester` checks `inputs.requester || github.actor`, so
  a bridged run is judged on the human and a manual dispatch on its own actor;
- `anthropics/claude-code-action` is given `allowed_bots: github-actions[bot]`,
  scoped to that one login rather than `*`.

`github.actor` MUST NOT be treated as the requesting identity anywhere on the
dispatch path.

## Why the actor is not the requester

GitHub restricts the workflow-dispatch API to callers with write access, and to
`actions: write` for a fine-grained token. That check is satisfied by the bridge
job's token, so it proves the dispatch came from a workflow inside this
repository — and nothing about who asked for it.

The trust chain that does establish the requester runs entirely in a trusted
context, before any branch-controlled file executes:

1. the `issue_comment` event runs `main`'s copy of the workflow, which a pull
   request cannot alter;
2. preflight in that run resolves the commenter and requires `admin`,
   `maintain`, or `write`, and no dispatch is issued otherwise;
3. the dispatched run re-checks the forwarded login before doing any work.

## The two bot gates

A bridged review passes through two independent bot checks, and both must be
opened. They fail in sequence, so opening only the first moves the failure
rather than removing it.

| Gate                            | Reads                                | Opened by                        |
| ------------------------------- | ------------------------------------ | -------------------------------- |
| `Authorize responder requester` | `inputs.requester \|\| github.actor` | forwarding the commenter's login |
| `claude-code-action`            | `github.actor`                       | `allowed_bots`                   |

The action's check is a proxy for human intent that the bridge design
necessarily breaks; it cannot see preflight's verdict.

## Consequences

- The residual exposure of `allowed_bots` is any other workflow on `main` that
  could be induced to dispatch the responder. The setting rests on the
  trustworthiness of `main`'s workflows, not on the actor field.
- A fork pull request never reaches either gate, but where that is enforced
  depends on the event. On a `pull_request` event preflight's `if:` requires the
  head repository to equal the workflow repository, so the job never starts. On
  a comment event that clause is bypassed — it is guarded by
  `github.event_name != 'pull_request'` — so preflight runs,
  `Determine checkout ref` records the fork as `isFork` without emitting a
  checkout ref, and every downstream step and job is skipped by its
  `isFork != 'true'` guard, the bridge included. Either way no dispatch is
  issued and nothing is checked out. The gate job still runs and fails for want
  of a review, so an unreviewed fork pull request stays blocked rather than
  passing silently. GitHub's own first-time-contributor approval holds such runs
  at `action_required` before any of this executes.
- Adding a dispatch path for a new event means forwarding a `requester` for it
  too, or the write-access gate silently judges the wrong identity.

See [AI review gate](../spec/ai-review-gate.md) for what the gate accepts.
