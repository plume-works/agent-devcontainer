---
type: bug
description: The gh-stack guard's publish force-pushes a stack layer back to a stale local copy after GitHub rebased that layer on the server, because the guard treats the rebased commits as already present and pushes layers adopted from other worktrees.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T13:30:00Z
sources:
- resource: .agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.py
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/602
rank: 350
---

# Bug: the stack guard reverts GitHub's post-merge rebase

## Symptom

After a lower layer of a GitHub native stack squash-merges, a later
`stack-guard.py publish` force-pushes the next layer back to an older local tip.
GitHub's server-side rebase onto `main` is undone, and the layer's pull request
again lists the lower layer's pre-squash commits. #602 records this as a
`head_ref_force_pushed` event from the guard's push.

## Reproduction

1. Build a native stack `main ← A ← B ← C` whose layers are checked out in
   different worktrees of one repository.
2. Squash-merge A. GitHub retargets B to `main` and rebases B on the server, so
   B's remote tip changes while every local copy of B keeps the old tip.
3. In C's worktree, run `gh stack unstack --local`, `gh stack init` over B and
   C, `stack-guard.py begin`, then `stack-guard.py publish`.
4. `begin` reports `SUCCESS`; `publish` force-pushes B to its stale local tip.

## Root cause

`begin` stops only on a remote commit whose patch the local branch lacks,
excluding the trunk. GitHub's rebase produces commits with the same patches as
the stale local ones, so `begin` finds nothing missing, records the rebased tip
as the lease, and `publish` replaces it. `publish` pushes every layer whose
remote differs from its local tip, so layers adopted from branches other
worktrees own are pushed with this worktree's stale view. A plain push of the
same branch is rejected as non-fast-forward.

## Fix

Planned by [Replace gh stack with manual stacked pull
requests](../plans/20261101-manual-stacked-prs.md): native stacks, `gh stack`,
and the guard are removed, and no branch is pushed with force.

## Key references

Verified anchor points (line numbers as of 2026-11-01):

- `.agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.py:215` —
  `side_patch_keys`, the verbatim patch-id comparison
- `.agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.py:242` —
  `remote_only_commits`, which excludes the trunk
- `.agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.py:369` —
  `push_layers`, the leased force-push of every differing layer
- `.agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.py:552` —
  `publish`
