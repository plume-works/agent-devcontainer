---
type: feature
stage: implemented
description: The PR skills merge a GitHub native stack of pull requests as one all-or-nothing operation through gh stack, route every stack branch update through gh stack, and merge every pull request explicitly instead of through auto-merge.
generated:
  by: claude-code/opus-5-5
  at: 2026-10-05T21:30:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
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
`gh-stack` extension, and the vendored `/agentdev:gh-stack` skill, kept on the
same release by a test, teaches agents its non-interactive commands.

**`/agentdev:pr-merge-stack`** brings every unmerged layer of a stack through CI
and AI review bottom-up, re-syncs the layers above after any change below with
`gh stack rebase --upstack` and `gh stack push`, and lands the stack with one
`gh stack merge <top> --yes --squash`.

**`/agentdev:pr-merge`** never enables auto-merge and disables an existing
request. A stacked PR it is asked to merge is merged with `gh stack merge` only
when it is the lowest unmerged layer; a higher layer is handed to
`pr-merge-stack`.

**Stack branches are updated only through `gh stack`.** `pr-open` pushes them
with `gh stack push`, `pr-feedback-resolution` resolves a conflicted stacked PR
with `gh stack rebase`, and `update-branch` refuses them. `AGENTS.md` allows a
force-push only as `gh stack`'s `--force-with-lease` update of a stack branch.

The contracts are [Stacked PRs](../spec/stacked-prs.md) and [PR merge
conflicts](../spec/pr-merge-conflicts.md); the GitHub behavior they rest on is
[Stacked pull requests](../architecture/stacked-prs.md).

## Edge cases

- **A layer was approved before a lower layer changed.** GitHub's post-merge
  rebase and `gh stack rebase --upstack` re-run CI on every layer above, but not
  the AI review; a sticky `CHANGES_REQUESTED` stays until a fresh review.
- **A layer still holds the PR template body.** The AI review's metadata gate
  blocks it, so every layer needs a real description before review.
- **A stack merge stops partway.** `pr-merge-stack` re-syncs the remaining
  layers with `gh stack sync` and brings them to green again before merging the
  new top.
- **A stack branch is pushed.** `gh stack push` runs no codebase-map check; CI
  still reports a stale map.

## Open questions

None — GitHub refuses auto-merge on a stacked PR and does not support cross-fork
stacks, both recorded in [Stacked pull
requests](../architecture/stacked-prs.md).

## References

- Plan: [Adopt GitHub native stacked pull
  requests](../plans/20261002-native-stacked-prs.md)
