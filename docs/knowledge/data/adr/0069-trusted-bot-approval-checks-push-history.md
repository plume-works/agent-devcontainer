---
type: adr
stage: accepted
description: The trusted-bot approval checks each commit and each push since the latest creation of the branch, and removes its earlier approval when a check fails.
---

# The trusted-bot approval checks the full push history

The `main` ruleset keeps an approval after a push. For this reason, the
`trusted-bot-approval` job approves only when each push since the latest
creation of the branch is from the trusted bot. Each commit must also have the
bot as author and a verified signature.

## Considered Options

- Check only the actor of the `synchronize` run. Rejected: a push from a person,
  then a close and a reopen of the pull request, makes the approval valid again.
- A ruleset bypass for the Renovate App. Rejected: it removes the approval
  requirement for dependency updates and records no approval.

## Consequences

- When a check fails, the job dismisses its earlier approval.
- The job runs the copy of the workflow in the pull request. A writer can change
  the job to remove the checks. As a result, the approval is only as strong as
  the trust in the writers of the repository.
- The checks are in
  `.github/workflows/ai-responder.yml#jobs.trusted-bot-approval`.
