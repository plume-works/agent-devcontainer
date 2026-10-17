---
type: bug
description: The gh-stack skill pushes every stack layer without first reconciling each local branch with its remote, so a layer whose remote gained commits is overwritten by the stale local branch under --force-with-lease.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T09:30:00Z
sources:
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.sh
- resource: https://github.com/github/gh-stack/issues/380
- resource: https://github.com/github/gh-stack/issues/472
- resource: https://github.com/github/gh-stack/issues/489
- resource: https://github.com/plume-works/agent-devcontainer/pull/355
---

# Bug: gh stack push overwrites a stack layer whose remote is ahead

## Symptom

A `gh stack push`, `gh stack submit`, or `gh stack sync` run by an agent
replaces a stack branch's remote tip with an older local tip. Commits pushed to
that branch from elsewhere disappear from the pull request, which records a
`head_ref_force_pushed` event.

## Reproduction

1. Adopt an existing pull request branch into a stack with `gh stack init`, so a
   local branch tracks it.
2. Push a new commit to that branch from another checkout.
3. In the stack checkout, `gh stack push`: the branch's remote is reset to the
   stale local tip, and the new commit is gone from the pull request.

## Root cause

In `gh-stack` v0.2.1, `push` and `submit` fetch every layer and only then take
each `--force-with-lease` value from the tracking ref they just updated, so the
lease always passes and the stale local branch wins (github/gh-stack#380).
`sync` fast-forwards only a layer whose local tip is an ancestor of its remote.
On a diverged layer it either rebases and force-pushes with the same fresh
lease, or has its plain push rejected while still reporting `Stack synced` and
exiting 0 (github/gh-stack#472), after which the `gh stack push` it suggests
drops the commits. `gh stack init` of a branch that exists only on the remote
creates the local branch at the trunk tip, so the next `submit` replaces the
real branch and closes its PR (github/gh-stack#489). The vendored skill's push
paths went straight to these commands, and `AGENTS.md` permitted the force-push
for stack branches without any check of each local layer against its remote.

## Fix

Fixed by [Guard every gh stack push against overwriting a layer's remote
commits](../plans/20261017-gh-stack-push-guard.md). The repository-owned
gh-stack skill's `stack-guard.sh begin` runs before a stack is rewritten,
fast-forwards layers that are behind, and stops on remote-only commits.
`publish` replaces `gh stack push` and `submit`, stops when a remote moved since
`begin`, and verifies every tip after the push. `gh stack sync` is no longer
run.

## Key references

Verified anchor points (line numbers as of 2026-10-17):

- `.agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.sh:296` —
  `run_begin`
- `.agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.sh:307` —
  `run_publish`
- `.agents/plugins/agentdev/skills/gh-stack/SKILL.md:29-62` — § The push guard
- `AGENTS.md:6` — the force-push exception naming the guard
