---
name: pr-merge-stack
description: 'Merge a GitHub native stack of pull requests: bring every unmerged layer through CI and AI review bottom-up, keep the layers above in sync after any change below, then land the stack with one gh stack merge. Use when asked to merge a PR stack, a stacked PR that has unmerged PRs below it, or a stack by its number. Keywords: merge stack, stacked pull requests, gh stack merge, merge PR stack, pr-merge-stack.'
---

# Merge a Pull-Request Stack

Drive every unmerged layer of a GitHub stack through the
[pr-merge](../pr-merge/SKILL.md) monitoring loop, from the bottom up, without
merging any of them, then land the whole stack with one all-or-nothing
`gh stack merge`. Drive `gh stack` through [gh-stack](../gh-stack/SKILL.md):
its non-interactive forms and exit-code recovery apply to every command here.

## Input and Safety Boundaries

Accept one input: a PR number or URL from the stack, or a stack number.

- Require `gh auth status` to succeed.
- Preserve the caller's working tree. Create a detached worktree under
  `./.tmp/` and run `gh stack checkout <input>` inside it; run every command
  from that worktree.
- Branches of the stack are updated only by `gh stack rebase`, `gh stack sync`,
  and `gh stack push`. Never force-push otherwise, and never update a ref
  through a GitHub API or MCP tool, including the server-side **Rebase stack**
  button.
- Never enable auto-merge; GitHub rejects it for stacks anyway.

## Read the Stack

```bash
gh stack view --json
```

The layers in `branches` are listed bottom-up. Record, for every entry whose
`isMerged` is `false`, its branch, `head`, and `pr.number`. Stop and report
when an unmerged layer has no open PR, or when a layer is a draft and the user
has not asked to mark it ready: `gh stack merge` merges only open, ready PRs.

## Bring Each Layer to Green

For each unmerged layer, bottom first, run [pr-merge](../pr-merge/SKILL.md)'s
**Monitoring Loop** steps 1–7 against its PR in this skill's worktree, and stop
where step 7 would start the final squash merge. A layer is green when every
pr-merge completion criterion except the merge holds for its current head.

Each layer is reviewed as its own PR. A body still holding the repository's PR
template fails the AI review's metadata gate, so give every layer a real
description before its review.

## Keep the Layers Above in Sync

Any new commit on a layer — a remediation, a conflict resolution, or a
`reformat.yml` commit — leaves every layer above it without the new tip. From
that layer's branch, bring them up to date and push the stack:

```bash
gh stack rebase --upstack
gh stack push
```

Every layer above now has a new head SHA, so its CI re-runs. The AI review does
not: the gate keeps accepting the layer's earlier review, and a
`CHANGES_REQUESTED` verdict on it stays sticky until a fresh review replaces it.
Re-enter the loop for each layer above before treating it as green again.

## Land the Stack

When every unmerged layer is green for its current head, merge the top PR, which
merges it and every unmerged layer below it in one operation:

```bash
gh stack merge <top-pr> --yes --squash
```

Confirm with `gh stack view --json` that every layer reports `isMerged: true`,
and with `gh pr view <pr> --json state` that each PR is `MERGED`.

## A Merge That Stops Partway

- **Rejected, nothing merged.** The merge is all-or-nothing, and the reason is
  reported for the PR that blocked it. Return to that layer's loop, fix the
  blocker, and merge again.
- **Some layers merged.** A merge queue on the trunk lands queued PRs in
  separate groups, and a layer can change after the merge started. Run
  `gh stack sync` to rebase the remaining layers past the merged ones, re-read
  the stack, and repeat **Bring Each Layer to Green** for the layers still
  unmerged before merging the new top.
- **Rebase conflict** (exit 3) from `sync` or `rebase`: follow the gh-stack
  skill's exit-3 recovery, then push and re-enter the loop for that layer.

## Final Report

Report the stack number, every PR with its final state and merged SHA, the
merge method, each remediation and resync performed, and any blocker that is
still open. Say the stack was merged only after every layer's merged state is
evidenced.

## Related Skills

- [pr-merge](../pr-merge/SKILL.md) — the per-PR monitoring and remediation loop,
  and the merge of a single lowest unmerged layer.
- [gh-stack](../gh-stack/SKILL.md) — non-interactive `gh stack` usage and
  exit-code recovery.
- [pr-feedback-resolution](../pr-feedback-resolution/SKILL.md) — conflict and
  feedback resolution for a layer.
