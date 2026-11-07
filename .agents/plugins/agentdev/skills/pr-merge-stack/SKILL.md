---
name: pr-merge-stack
description: 'Merge a chain of manual stacked pull requests from its top: merge the bottom pull request through pr-merge, restack the rest with one pr-restack-all run, and repeat until the top has merged. Use when asked to merge a PR stack or chain, or a dependent pull request that has unmerged pull requests below it. Keywords: merge stack, stacked pull requests, dependent PRs, merge chain, pr-merge-stack.'
---

# Merge a Chain of Stacked Pull Requests

A manual stacked pull request is based on its predecessor's branch and lists
it under `## Depends on`. Only a pull request based on `main` can merge, so a
chain merges one pull request at a time, bottom first, and the rest are
restacked after each merge.

## Input and Safety Boundaries

Accept one input: the top pull request of the chain, as a number or URL.

- Require `gh auth status` to succeed.
- Branches are updated only by plain pushes: never force-push, rebase, or
  reset, and never update a ref through a GitHub API or MCP tool.
- Never enable auto-merge, and never pass `--admin`.

## The Loop

```text
input: top PR
loop:
  1. walk the chain from GitHub PRs        → bottom = the PR whose base is main
  2. pr-merge bottom                        → CI, AI review, squash merge
  3. GitHub retargets the next PR to main
  4. pr-restack-all top                     → restacks every PR still in the chain
  5. bottom was the top PR → done; else back to 1
```

1. **Walk the chain.** From the top pull request, follow each base branch to
   the open pull request whose head it is, down to the one based on `main`: the
   bottom. Each link's last `## Depends on` entry must be the pull request below
   it; stop and report the link when it is not. Restacking in step 4 walks the
   chain the same way.
2. **Merge the bottom** through [pr-merge](../pr-merge/SKILL.md): CI, AI
   review, feedback, then its squash merge. pr-merge refuses a base other than
   `main`, so it can never merge a link above the bottom. This skill runs
   pr-merge itself.
3. **GitHub retargets** the next pull request to `main`. Confirm with
   `gh pr view <next> --json baseRefName` before continuing.
4. **Restack** with one run of this skill's own
   [pr-restack-all](../pr-restack-all/SKILL.md), on the top pull request, following
   its result table. The merged pull request is
   reconnected into the one above, and every link above that merges the new
   head of the link below it.
5. **Repeat** from step 1 until the top pull request itself has merged.

Every restack gives each remaining link a new head, so its CI re-runs and
pr-merge re-enters its monitoring loop for it when its turn comes.

## Final Report

Report every pull request with its final state and squash commit, each restack
with its `RECONNECTED` and `PUSHED` lines, every remediation, and any blocker
still open. Say the chain was merged only after each pull request's `MERGED`
state is evidenced.

## Related Skills

- [pr-merge](../pr-merge/SKILL.md) — the per-PR monitoring, remediation, and
  squash merge of the bottom pull request.
- [pr-restack-all](../pr-restack-all/SKILL.md) — restacking the chain after
  each merge.
- [pr-feedback-resolution](../pr-feedback-resolution/SKILL.md) — conflict and
  feedback resolution for a pull request.
