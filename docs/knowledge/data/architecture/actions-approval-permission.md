---
type: architecture
description: The AI reviewer submits APPROVE with the workflow's GITHUB_TOKEN, so "Allow GitHub Actions to create and approve pull requests" must be enabled at the organization level and inherited by the repository; the reviewer's approval is the one the main ruleset requires.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T18:30:00Z
sources:
- resource: .github/actions/run-claude-responder/action.yml
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: https://docs.github.com/en/organizations/managing-organization-settings/disabling-or-limiting-github-actions-for-your-organization#preventing-github-actions-from-creating-or-approving-pull-requests
- resource: https://docs.github.com/en/rest/actions/permissions#get-default-workflow-permissions-for-a-repository
---

# Actions approval permission

## Decision

The organization setting **Allow GitHub Actions to create and approve pull
requests** SHALL be enabled, and the repository SHALL inherit it. It is a
prerequisite of the AI review responder as configured, not an optional hardening
choice.

The responder posts its review with the workflow's `GITHUB_TOKEN`
(`run-claude-responder` passes `github_token`), so the reviewer identity is
`github-actions[bot]`. The `pr-review` skill submits `APPROVE` when no validated
finding survives (see [AI review event
selection](ai-review-event-selection.md)). GitHub refuses an approving review
from `GITHUB_TOKEN` unless this setting is on.

Verify it with:

``` bash
gh api repos/<owner>/<repo>/actions/permissions/workflow --jq .can_approve_pull_request_reviews
```

which must print `true`. A repository cannot enable the setting while its
organization disallows it.

## Consequences

- The `main` ruleset requires one approving review, and an `APPROVE` from
  `github-actions[bot]` satisfies it. The reviewer's approval is therefore what
  makes a pull request mergeable without ruleset bypass; with the setting off,
  no pull request can be approved by the AI reviewer at all.
- Only an `APPROVE` from the same reviewer replaces that reviewer's earlier
  `CHANGES_REQUESTED`. Without the setting, a clean re-review cannot lift the
  bot's own change request, which then needs a manual dismissal.
- The setting also lets any workflow's `GITHUB_TOKEN` in the organization
  approve and open pull requests as `github-actions[bot]`, and that approval
  counts toward the ruleset's required approval. The trust placed in the AI
  reviewer extends to every workflow on `main` that holds
  `pull-requests: write`.
- The prerequisite is tied to the `GITHUB_TOKEN` reviewer identity. A responder
  that posts with a GitHub App installation token does not depend on it.
