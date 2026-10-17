---
type: bug
description: The gh-stack skill pushes every stack layer without first reconciling each local branch with its remote, so a layer whose remote gained commits is overwritten by the stale local branch under --force-with-lease.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T01:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
- resource: AGENTS.md
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
3. In the stack checkout, `git fetch` — the remote-tracking ref moves to the new
   commit, the local branch does not.
4. `gh stack push`: the branch's remote is reset to the stale local tip, and the
   new commit is gone from the pull request.

## Root cause

`--force-with-lease` without an explicit expected value checks the remote
against the local remote-tracking ref. After a fetch that ref already names the
new commit, so the lease passes and the stale local branch wins. The skill's
push paths — the core loop and "Editing an existing stack" — go straight to
`gh stack push` or `gh stack submit` with no step that compares each local
branch with its remote, and `AGENTS.md` permits the force-push for stack
branches without that precondition.

## Fix

Unfixed. Before any `push`, `submit`, or `sync`, the skill fetches and, for each
stack branch, fast-forwards a local branch its remote is ahead of and stops on a
branch that has diverged — ideally as a bundled `agent-code/` script with a
`RESULT=` line, so the gate cannot be skipped as prose. Adopting an existing
branch with `gh stack init` pulls it first.

## Key references

Verified anchor points (line numbers as of 2026-10-17):

- `.agents/plugins/agentdev/skills/gh-stack/SKILL.md:73-83` — editing an
  existing stack, ending in `gh stack push`
- `.agents/plugins/agentdev/skills/gh-stack/SKILL.md:86-93` — core loop, ending
  in `gh stack submit --auto`
- `AGENTS.md:6` — the force-push exception for `gh stack push`, `rebase`, and
  `sync`
