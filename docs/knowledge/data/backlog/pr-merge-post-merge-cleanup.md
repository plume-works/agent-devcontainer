---
type: task
created: 2026-10-20
stage: planned
priority: medium
description: After pr-merge squash-merges a PR from its own head branch, release that branch and move the checkout to main or to the plan's next work branch, named by iwe-branch-name.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-25T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-new-branch/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
---

# Clean up the local checkout after pr-merge

A merged PR leaves the checkout on a branch whose remote is gone, and the next
step of the plan it served starts from a fresh branch off the default branch.
pr-merge knows the merge landed, so it is the place to make that move.

Depends on the `iwe-branch-name` skill, which owns branch names of the form
`<impl|ship>/<plan-slug>/iter-<N>` and the lookup of a plan's state at the
remote default branch.

## Scope

Runs only when pr-merge worked in place on the PR head branch. In worktree mode
the caller's checkout is elsewhere and is left alone; the skill removes only its
own worktree, as it does today.

```
merge confirmed, pr-merge ran in place on the PR head branch
  ├─ fetch the remote
  ├─ release the merged branch
  │     detach at the remote default branch (carry local changes or stop)
  │     local tip == merged headRefOid → delete it with -D
  │     otherwise keep it and report it
  │     drop refs/remotes/<remote>/<head> once the remote no longer has it
  └─ next branch, from iwe-branch-name on the head branch's plan
        done | cancelled | no plan  → switch to the default branch, fast-forward
        every task ticked           → git-new-branch ship/<slug>/iter-N
        unticked tasks remain       → git-new-branch impl/<slug>/iter-N
```

## Constraints

- The repository squash-merges only, so `git branch -d` always refuses a merged
  head; deletion is `-D`, guarded by the tip matching the merged `headRefOid` so
  no unpushed commit is lost.
- The release happens before the next branch is created. Git cannot hold
  `ship/<slug>/iter-1` beside a branch it would nest under, and a stale
  remote-tracking ref blocks the push's tracking update the same way.
- Prune only the merged head's remote-tracking ref, never the whole remote.
- The decision logic ships as a script under the skill's `agent-code/`,
  following the skill-scripts output contract; branch creation stays with
  `/agentdev:git-new-branch`.
- A kept branch that the next name would nest under is a stop, not a forced
  delete.

Stacked PRs are out of scope here; see [Clean up the local checkout after
pr-merge-stack](pr-merge-stack-post-merge-cleanup.md).
