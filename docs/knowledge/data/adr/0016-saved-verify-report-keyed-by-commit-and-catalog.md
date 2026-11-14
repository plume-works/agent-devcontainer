---
type: adr
stage: accepted
description: Verify keeps one saved report for each plan, keyed by the commit and by a hash of the catalog files, and uses it again on a match.
---

# The saved Verify report is keyed by commit and catalog hash

Verify refuses a worktree that has uncommitted changes, so a commit names all
that Verify examined. `verify-cache.py` keeps one saved Verify report for each
plan, keyed by that commit and by a hash of the catalog files on disk. As a
result, `iwe-shipper` uses the verdict of the Implement loop again, and does not
run the tests again.

## Considered Options

- Key the report by a tree hash, or by hashes of the files of the plan.
  Rejected: a hash of only the plan files misses a change in a different file
  that a verification command can use.
- Key the report by the commit only. Rejected: an installed plugin is not a Git
  checkout, and a session can load a catalog that is different from the catalog
  in the commit.
- A handoff file that Implement commits for `iwe-shipper`. Rejected: the commit
  of the file changes the commit that the file identifies.
- Do the search in the `iwe-verifier` rulebook. Rejected: a match then still
  needs one dispatch.

## Consequences

- The approvals of the user are in the report but not in its key. A request that
  quotes an approval does not use the saved report.
- `verify-cache.py` writes a `.gitignore` that holds `*` into `.tmp/verify/`, so
  a save does not add uncommitted changes to the worktree.
- Verify does not use a saved report again after a rebase, after a squash merge,
  or in a new container.
