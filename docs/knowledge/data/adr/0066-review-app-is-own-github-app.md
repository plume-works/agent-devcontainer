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
  makes the token after them, so their environment never holds it. A process
  that they start and do not stop can still get it.
- The workflows write `plume-works-quill[bot]` as a literal. No input or
  variable can change the reviewer login to a different account.
- Preflight and `ai-review-present` accept a review only from
  `plume-works-quill[bot]`. They ignore reviews from `github-actions[bot]` and
  `claude[bot]`.
- The organization setting "Allow GitHub Actions to create and approve pull
  requests" stays off.
- The `permissions:` block of a job limits only `GITHUB_TOKEN`. The
  `permission-*` inputs of `actions/create-github-app-token` limit the App
  token. The review token gets contents read, pull requests write, issues write,
  and actions read. The approval token gets only pull requests write.
- The jobs that use the App token run in the `plume-works-review` environment,
  which holds the App secrets.
- The App opens no pull request and pushes nothing. As a result, no event from
  the App starts a review, and the App needs no ruleset bypass.
- Only an approval from the same reviewer replaces its earlier change request.
  Each review posts as the same App, so a clean review replaces the change
  request of an earlier review.
