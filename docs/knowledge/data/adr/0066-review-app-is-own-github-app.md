---
type: adr
stage: accepted
description: The AI review and the trusted-bot approval post as the plume-works-quill GitHub App, with a token that has no contents write and no GITHUB_TOKEN fallback.
---

# The AI review posts as a GitHub App of the organization

The approval that the `main` ruleset requires must come from an identity that no
other workflow can use. For this reason, the review responder and the
trusted-bot approval post as `plume-works-quill[bot]`, with a token of that App.
Each job makes its own token, which has no contents write.

## Considered Options

- Post with `GITHUB_TOKEN` and let GitHub Actions approve pull requests.
  Rejected: each workflow of the organization can then approve as the reviewer.
- The App reviews and `GITHUB_TOKEN` approves trusted bots. Rejected: the
  organization setting must stay on, so the same gap stays open.
- The Claude GitHub App through OIDC (`claude[bot]`). Rejected: the organization
  does not control that identity, and other installations share it.
- Use `GITHUB_TOKEN` when the App secrets are empty. Rejected: this returns the
  shared identity without a warning. A job without the secrets fails.
- Push with `GITHUB_TOKEN` as a ruleset bypass actor. Rejected: a bypass list
  does not accept the GitHub Actions app that `GITHUB_TOKEN` acts as.

## Consequences

- The App installation has contents write, because the ruleset counts only an
  approval from a reviewer with write access. No job requests that permission
  for its token.
- The lifecycle commands run code of the pull request in the review job. The job
  makes the token after them, so their environment never holds it.
- The workflows write `plume-works-quill[bot]` as a literal. No input or
  variable can change the reviewer login to a different account.
