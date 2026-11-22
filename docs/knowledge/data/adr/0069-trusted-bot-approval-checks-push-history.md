---
type: adr
stage: accepted
---

# The trusted-bot approval checks the full push history

The `main` ruleset keeps an approval after a push. For this reason, the
`trusted-bot-approval` job approves only when each push since the latest
creation of the branch is from the trusted bot. Each commit must also have the
bot as author and a verified signature. A failed check dismisses the standing
approval.

## Considered Options

- Check only the actor of the `synchronize` run. Rejected: a push from a person,
  then a close and a reopen of the pull request, makes the approval valid again.
- A ruleset bypass for the Renovate App. Rejected: it removes the approval
  requirement for dependency updates and records no approval.

## Consequences

- The commits alone cannot show who pushed them. A different account can use the
  API to make a commit that names the bot as author and has a verified
  signature. For this reason, the job also examines the push history.
- The push history check stops at the latest `branch_creation`, so a branch name
  that a bot uses again, such as `renovate/<dep>`, starts with no history.
- The job runs the copy of the workflow in the pull request. A writer can change
  the job to remove the checks; the checks guard only against commits that leave
  the workflow unchanged. As a result, the approval is only as strong as the
  trust in the writers of the repository.
