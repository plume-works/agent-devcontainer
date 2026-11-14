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

- The commits alone cannot show who pushed them. A different account can use the
  API to make a commit that names the bot as author and has a verified
  signature. For this reason, the job also examines the push history.
- The committer of each commit must be the bot or `web-flow`, which is the
  committer of a commit that an App makes through the API.
- The push history check stops at the latest `branch_creation`, so a branch name
  that a bot uses again, such as `renovate/<dep>`, starts with no history.
- `GITHUB_TOKEN` reads the push history with `contents: read`. The job posts or
  dismisses its approval with an App token that has only pull requests write.
- When a check fails, the job dismisses its earlier approval and posts a notice
  that names the push or commit that failed.
- The job runs the copy of the workflow in the pull request. A writer can change
  the job to remove the checks. As a result, the approval is only as strong as
  the trust in the writers of the repository.
- The checks are in
  `.github/workflows/ai-responder.yml#jobs.trusted-bot-approval`.
