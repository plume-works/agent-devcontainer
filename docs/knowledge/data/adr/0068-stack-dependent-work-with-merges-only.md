---
type: adr
stage: accepted
description: Work that depends on an open pull request is a normal pull request based on the branch of its predecessor, and a restack uses only merges and plain pushes.
---

# Dependent pull requests stack with merges only

Work that depends on an open pull request is a normal pull request. Its base is
the branch of its predecessor, so its diff shows only its own work. Nobody
rewrites a branch. Each update is a merge, and each push is a plain push. As a
result, no copy of a branch in a different checkout is left with rewritten
history: a session whose branch a restack advanced sees an ordinary
non-fast-forward rejection and merges.

## Considered Options

- GitHub native stacks through `gh stack`. Rejected: GitHub rebases the other
  pull requests on the server after a lower one merges, and `gh stack rebase`
  rewrites them again locally before a force-push. A lease protects commits that
  only the remote holds, not the consumers of a rewritten branch, and each local
  copy goes stale.
- Each pull request has `main` as its base. Rejected: its diff includes each
  predecessor until they merge.
- Resolve the reconnect merge with `-s ours`. Rejected: it is correct by
  construction but silent. A normal merge lets git report a conflict.
- A required `base-is-main` check with no bypass actor. Rejected: it also
  refuses a push or a new branch from an owner.

## Consequences

- A pull request has one base, so a branch can wait for only one unmerged
  predecessor. `pr-open` refuses a branch with two.
- A ruleset on `refs/heads/iwe/**` requires the `base-is-main` check, which no
  workflow reports. The Write, Maintain, and Admin repository roles are bypass
  actors. As a result, GitHub refuses to merge a pull request into an `iwe/`
  branch, but it accepts a push by an owner.
