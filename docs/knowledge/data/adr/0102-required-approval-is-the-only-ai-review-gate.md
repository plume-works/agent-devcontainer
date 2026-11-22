---
type: adr
stage: proposed
supersedes:
- adr/0037-ai-review-trusts-named-bots
- adr/0069-trusted-bot-approval-checks-push-history
---

# The required approval is the only gate of the AI review

The `main` ruleset requires one approval, and an approval from
`plume-works-quill[bot]` counts like any other. No check requires that Quill
reviewed a pull request: each review posts a `Quill Review` check on the commit
it reviewed, and no ruleset requires it. A missing review shows as a missing
approval, never as a failed check. For a pull request whose every push since the
latest creation of its branch, and every commit, is from one bot that the
service configuration trusts, the service approves without a review. Each commit
must also name that bot as author and committer, or `web-flow` as committer, and
carry a verified signature. When the rule stops holding, the service dismisses
its approval.

## Considered Options

- A required check that passes once Quill has reviewed. Rejected: GitHub reads a
  required check on the head only, so each push would need a review or a
  carried-forward pass.
- A ruleset bypass for the Renovate App. Rejected: GitHub auto-merge ignores a
  bypass, so Renovate would merge only on its own runs, and every dependency
  update would merge without a recorded approval.
- Quill reviews the pull requests of bots like any other. Rejected: a model run
  for each digest bump, where the push-history rule already proves the author.

## Consequences

- A person with write access can merge with a human approval alone; the AI
  review is no longer mandatory.
- The commits alone cannot show who pushed them, so the approval also reads the
  push history of the branch.
