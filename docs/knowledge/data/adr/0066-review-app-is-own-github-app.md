---
type: adr
stage: accepted
description: The AI review and the trusted-bot approval post as the plume-works-quill GitHub App, with a token that has no contents write, and never with GITHUB_TOKEN.
---

# The AI review posts as a GitHub App of the organization

The approval that the `main` ruleset requires must come from an identity that no
other workflow can use. For this reason, the review responder and the
trusted-bot approval post as `plume-works-quill[bot]`, with a token of that App.
Each job makes its own token, which has no contents write.

## Considered Options

- Post with `GITHUB_TOKEN` and let GitHub Actions approve pull requests.
  Rejected: any workflow of the organization could then approve as the reviewer
  and satisfy the required review.
- The App reviews and `GITHUB_TOKEN` approves trusted bots. Rejected: the
  organization setting must stay on, so the same gap stays open.
- The Claude GitHub App through OIDC (`claude[bot]`). Rejected: the organization
  does not control that identity, and other installations share it.
- Use `GITHUB_TOKEN` when the App secrets are empty. Rejected: this silently
  brings back the shared identity that the gate no longer accepts. A job without
  the secrets fails.
- Push with `GITHUB_TOKEN` as a ruleset bypass actor. Rejected: a bypass list
  accepts only repository roles, teams, and GitHub Apps installed on the owner
  of the repository. The built-in GitHub Actions app that `GITHUB_TOKEN` acts as
  is none of these, so such a push can never bypass.

## Consequences

- The App installation has contents write, because the ruleset counts only an
  approval from a reviewer with write access. No job requests that permission
  for its token.
- The lifecycle commands run code of the pull request in the review job. The job
  makes the token after them, so their environment never holds it. A process
  that they start and do not stop can still get it. The fork and write-access
  checks of the preflight job limit that exposure to writers.
- The organization setting "Allow GitHub Actions to create and approve pull
  requests" stays off.
- The `permissions:` block of a job limits only `GITHUB_TOKEN`. The
  `permission-*` inputs of `actions/create-github-app-token` limit the App
  token.
- The App opens no pull request and pushes nothing. As a result, no event from
  the App starts a review, and the App needs no ruleset bypass.
- Only an approval from the same reviewer replaces its earlier change request.
  Each review posts as the same App, so a clean review replaces the change
  request of an earlier review.
