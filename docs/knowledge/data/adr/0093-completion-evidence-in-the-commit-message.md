---
type: adr
stage: accepted
description: The message of the commit that ticks a plan task contains its completion evidence block, and the plan has no evidence line.
supersedes:
- adr/0086-plan-ticks-need-evidence-lines
---

# The commit that ticks a plan task contains its evidence

The evidence for a ticked plan task is a completion evidence block in the
message of the commit that ticks the plan task. The diff of that commit shows
which plan task it ticks, so the block names no task. A commit ticks one plan
task at most. A `commit-msg` hook enforces the two rules on a new commit, and a
`pre-push` hook enforces them on each pushed commit. A hook never reads the
command line of a Git command. The plan carries no `- **Evidence:**` line.

## Considered Options

- The evidence line in the plan. Rejected: the line is in the squash commit, but
  the line does not connect to the code change of its task. The commit message
  connects to that change, and `git log` and `git blame` find it.
- One block that names a task number. Rejected: the diff already shows the plan
  task, and a number can be incorrect.
- Many ticks in one commit. Rejected: one block cannot tell which text belongs
  to which plan task, and a find-and-replace can tick each plan task in a file.
- An amend check in the `commit-msg` hook from the command line of the `git`
  process. Rejected: Git gives a `commit-msg` hook no sign of an amend, and the
  command line has aliases, abbreviations, and a different form on each
  platform. The `pre-push` hook compares each pushed commit with its parent, so
  it also examines an amended commit.
- A CI check of each commit of a pull request. Rejected: the failure is on a
  pushed commit, and only an amend or a rebase can correct it. This repository
  does not permit a rewrite of pushed history.

## Consequences

- After the squash merge, the commits of a pull request with their blocks are
  only at `refs/pull/<N>/head` on GitHub. `scripts/completion-evidence.py show`
  reads them from there.
- The `commit-msg` hook sees only the change that an amend adds. The `pre-push`
  hook examines the amended commit before it leaves the checkout.
- The hooks do not stop a commit or a push that uses `--no-verify`. `show` then
  prints no evidence for its tick.
