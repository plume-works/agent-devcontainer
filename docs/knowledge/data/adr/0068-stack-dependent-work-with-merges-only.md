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
- A required `base-is-main` check with no bypass actor. Rejected: it also
  refuses a push or a new branch from an owner.

## Consequences

- After a squash merge, `pr_restack_all.py` reconnects the dependent pull
  request. It merges the squash commit into a detached copy of the last head of
  the predecessor. Then it merges that copy into the dependent pull request. The
  copy holds `main` only up to the squash commit, so a later change on `main`
  comes only from an update of the branch.
- The reconnect reads the last head and the squash commit of the predecessor
  from the data of its pull request, not from a branch, and requires
  `refs/pull/<P>/head` to agree. A branch that holds both commits is already
  reconnected, so a second run changes nothing.
- A dependent branch records each predecessor in three places: its parent
  commits, an empty commit with a Depends-on trailer, and the `## Depends on`
  section of the pull request body. `.agents/plugins/agentdev/bin/depends_on.py`
  is the one parser of the section and the trailers. `check_depends_on.py`
  checks each body that `pr-open` or `pr-gen-description` writes, so a new body
  cannot remove a merge record.
- A pull request has one base, so a branch can wait for only one unmerged
  predecessor. `pr-open` refuses a branch with two.
- `pr-merge` merges only a pull request whose base is `main`. `pr-merge-stack`
  merges the bottom through `pr-merge`, and then restacks the remaining chain
  with one `pr_restack_all.py` run from its top.
- A ruleset on `refs/heads/iwe/**` requires the `base-is-main` check, which no
  workflow reports. The Write, Maintain, and Admin repository roles are bypass
  actors. As a result, GitHub refuses a merge into a dependent branch, but it
  accepts a push by an owner.
- A restack works in one detached worktree that it makes from remote refs, so it
  moves no local branch.
- `pr_restack_all.py` refuses a pull request whose head is in a fork.
