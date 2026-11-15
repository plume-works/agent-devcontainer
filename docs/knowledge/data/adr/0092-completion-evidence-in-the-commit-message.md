---
type: adr
stage: proposed
description: The commit that ticks a plan task carries the evidence for the task in its message, in a completion evidence block, and the plan carries no evidence line.
supersedes:
- adr/0086-plan-ticks-need-evidence-lines
---

# The commit that ticks a plan task carries its evidence

The evidence for a ticked plan task is a completion evidence block in the
message of the commit that ticks the box. The diff of that commit shows which
box it ticks, so the block names no task. A commit ticks one box at most, and a
`commit-msg` hook and a CI check on each pull request enforce the two rules. The
plan carries no `- **Evidence:**` line.

## Considered Options

- The evidence line in the plan. Rejected: the line is in the squash commit, but
  the line does not connect to the code change of its task. The commit message
  connects to that change, and `git log` and `git blame` find it.
- One block that names a task number. Rejected: the diff already shows the box,
  and a number can be incorrect.
- Many ticks in one commit. Rejected: one block cannot tell which text belongs
  to which box, and a find-and-replace can tick each box in a file.

## Consequences

- After the squash merge, the commits of a pull request with their blocks are
  only at `refs/pull/<N>/head` on GitHub. `scripts/completion-evidence.py show`
  reads them from there.
- A commit that skips the hooks with `--no-verify` still fails the CI check of
  its pull request.
