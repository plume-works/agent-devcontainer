---
type: architecture
description: The AI review responder and the trusted-bot approval post with per-job installation tokens of the plume-works-quill GitHub App, the AI review gate accepts only that App's login, and GitHub Actions no longer needs to approve pull requests; supersedes Actions approval permission.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: data/plans/20261030-responder-quill-app-identity.md
---

# Responder App identity

## Context

The maintainer decided on 2026-10-30:

- the responder posts as a GitHub App named `plume-works-quill`, login
  `plume-works-quill[bot]`, for a recognizable reviewer and for an approval no
  other workflow can give;
- the App is the only automated approver: the review responder and the
  trusted-bot approval job both post with its installation token,
  `ai-review-present` accepts only its reviews, and the organization setting
  "Allow GitHub Actions to create and approve pull requests" is turned off once
  the App's approval is shown to count;
- reviews by the previous bot identities, `github-actions[bot]` and
  `claude[bot]`, are ignored, with no transition period and no dismissals;
- the `plume-works-review` environment replaces `claude-review` and holds
  `CLAUDE_CODE_OAUTH_TOKEN`, `QUILL_APP_CLIENT_ID`, and `QUILL_APP_PRIVATE_KEY`;
  a job whose App secrets are missing fails, with no `GITHUB_TOKEN` fallback;
- the App never opens pull requests.

The maintainer decided on 2026-11-07 that `plume-works-quill[bot]` is the only
AI reviewer login, with no variable or input to repoint it.

The responder runs only on pull request events and pushes nothing (see
[Pull-request-only AI
responder](../../2.1.0/architecture/pull-request-only-responder.md)), so the App
needs no ruleset bypass.

The maintainer decided on 2026-11-07 that the App's installation holds contents
write: the `main` ruleset counts an approval only from a reviewer with write
access, so a read-only App's approval leaves `reviewDecision` at
`REVIEW_REQUIRED`.

## Approach

```
 environment: plume-works-review
   claude-respond  lifecycle scripts → mint (contents:read)  → claude-code-action
   trusted-bot approval              → mint (pull-requests:write) → APPROVE

 ai-review-present ── accepts plume-works-quill[bot] only
```

- `plume-works-quill[bot]` is the only AI reviewer login, written as a literal
  in `ai-review-status`, the trusted-bot approval job, `pr-request-ai-review`,
  and `pr-eval-review-needed`; no variable or input repoints it. Preflight's
  review lookup and `ai-review-present` accept a review only from that login.
- `run-claude-responder` fails first when either App secret is empty, then mints
  the token with `actions/create-github-app-token` after the devcontainer
  lifecycle scripts and immediately before the Claude step, with contents read,
  pull requests write, issues write, and actions read. It hands
  `claude-code-action` that token and the `bot_id` and `bot_name` resolved from
  the token's `app-slug`.
- The trusted-bot approval job reads the pull request's reviews, commits, and
  push activity with `GITHUB_TOKEN`, which keeps `contents: read`, and posts or
  dismisses its approval with a token minted for pull requests write only. A run
  Dependabot triggers cannot read environment secrets, so the job skips the
  approval before it checks them.
- A job's `permissions:` block bounds only `GITHUB_TOKEN`; the minted token's
  `permission-*` inputs are what bound the App token.
- The App's installation holds contents read and write, pull requests read and
  write, issues read and write, actions read, and metadata read, and no
  workflows permission. Contents write makes its approval count; no job requests
  it when minting, so no workflow token can push, and only a holder of the App's
  private key could.
- The workflow runs only on pull request, pull request review, and merge group
  events, and the App opens no pull request and pushes nothing, so no App event
  can start a review.

## Residual exposure

The lifecycle scripts run code from the pull request head in the same job that
later holds the minted token. `GITHUB_TOKEN` carries the same exposure; the fork
and write-access gates bound it to writers, and minting after the scripts keeps
the token out of their environment though not out of a process they leave
running.

## Rejected alternatives

- **Keep `GITHUB_TOKEN` and the organization approval setting**: any workflow in
  the organization can approve as the reviewer and satisfy the required review.
- **The App reviews while `GITHUB_TOKEN` approves trusted bots**: the
  organization setting has to stay on, so the same gap stays open.
- **The Claude GitHub App through OIDC (`claude[bot]`)**: an identity this
  organization does not control, shared with every other installation.
- **Falling back to `GITHUB_TOKEN` when the App secrets are missing**: a silent
  fallback reintroduces the shared identity the gate no longer accepts.

This supersedes [Actions approval
permission](../../2.0.0/architecture/actions-approval-permission.md).
