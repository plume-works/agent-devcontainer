---
type: feature
stage: implemented
description: The PR skills merge a GitHub native stack of pull requests as one all-or-nothing operation through gh stack, route every stack branch update through gh stack, and merge every pull request explicitly instead of through auto-merge.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T16:40:07Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
- resource: .agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.py
- resource: ansible/roles/github_cli/defaults/main.yml
---

# Native stacked pull requests

## Purpose

A chain of dependent pull requests is a GitHub stack: each PR targets the branch
below it, and the stack lands bottom-up in one operation. The PR skills drive
stacks through the `gh stack` extension instead of emulating them with a chain
of `main`-targeted drafts, and every PR — stacked or not — is merged explicitly
once its checks and reviews are green.

## Behaviour

**The image ships `gh stack`.** The `github_cli` role installs the pinned
`gh-stack` extension. The repository-owned `/agentdev:gh-stack` skill teaches
agents its non-interactive commands over GitHub's own reference pages for that
release, and publishes every stack branch through its guard.

**`/agentdev:pr-merge-stack`** brings every unmerged layer of a stack through CI
and AI review bottom-up, re-syncs the layers above after any change below with
`gh stack rebase --upstack` and the guard's `publish`, and lands the stack with
one `gh stack merge <top> --yes --squash`.

**`/agentdev:pr-merge`** never enables auto-merge and disables an existing
request. A stacked PR it is asked to merge is merged with `gh stack merge` only
when it is the lowest unmerged layer; a higher layer is handed to
`pr-merge-stack`.

**Stack branches are updated only through the gh-stack skill's guard.**
`stack-guard.py begin` runs before a stack is rewritten: it fast-forwards a
layer its remote is ahead of and stops on commits that exist only on a layer's
remote. `stack-guard.py publish` replaces `gh stack push` and `submit`, and
refuses to push over a remote that moved since `begin`. `pr-open` publishes
stack branches through it, `pr-feedback-resolution` resolves a conflicted
stacked PR with `begin`, `gh stack rebase`, and `publish`, and `update-branch`
refuses them. `AGENTS.md` allows a force-push only as `gh stack rebase` or the
guarded `publish` of a stack branch; a bare `gh stack push`, `submit`, or `sync`
is never run.

The contracts are [Stacked PRs](../spec/stacked-prs.md) and [PR merge
conflicts](../spec/pr-merge-conflicts.md); the GitHub behavior they rest on is
[Stacked pull requests](../architecture/stacked-prs.md).

## Edge cases

- **A layer was approved before a lower layer changed.** GitHub's post-merge
  rebase and `gh stack rebase --upstack` re-run CI on every layer above, but not
  the AI review; a sticky `CHANGES_REQUESTED` stays until a fresh review.
- **A layer still holds the PR template body.** The AI review's metadata gate
  blocks it, so every layer needs a real description before review.
- **A stack merge stops partway.** `pr-merge-stack` refreshes the remaining
  layers with `begin`, `gh stack rebase`, and `publish` and brings them to green
  again before merging the new top.
- **Someone else pushed to a layer.** `begin` takes the new commits in when the
  local layer is behind, and stops for the user's decision when both sides
  moved; `publish` stops when the remote moved during the edit.

## Open questions

None — GitHub refuses auto-merge on a stacked PR and does not support cross-fork
stacks, both recorded in [Stacked pull
requests](../architecture/stacked-prs.md).

## References

- Plan: [Adopt GitHub native stacked pull
  requests](../plans/20261002-native-stacked-prs.md)
