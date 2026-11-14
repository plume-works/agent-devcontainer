---
type: adr
stage: accepted
description: Work that depends on an open pull request is a normal pull request based on the branch of its predecessor, and a restack uses only merges and plain pushes.
---

# Dependent pull requests stack with merges only

Work that depends on an open pull request is a normal pull request. Its base is
the branch of its predecessor, so its diff shows only its own work. Nobody
rewrites a branch. Each update is a merge, and each push is a plain push. As a
result, no copy of a branch in a different checkout becomes out of date.

## Considered Options

- GitHub native stacks through `gh stack`. Rejected: GitHub rebases the other
  pull requests on the server after a lower one merges, and each local copy
  becomes out of date.
- Each pull request has `main` as its base. Rejected: its diff includes each
  predecessor until they merge.
- Resolve the reconnect merge with `-s ours`. Rejected: it is correct but
  silent. A normal merge lets git report a conflict.
- Each owner restacks their own pull requests. Rejected: it needs more
  coordination than one restack from a detached worktree.

## Consequences

- After a squash merge, `pr_restack_all.py` reconnects the dependent pull
  request. It merges the squash commit into a detached copy of the last head of
  the predecessor. Then it merges that copy into the dependent pull request.
- A restack works in one detached worktree that it makes from remote refs, so it
  moves no local branch.
- `pr_restack_all.py` refuses a pull request whose head is in a fork.
