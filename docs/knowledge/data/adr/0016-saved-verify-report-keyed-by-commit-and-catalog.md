---
type: adr
stage: accepted
description: Verify keeps one saved report for each plan, keyed by the commit and by a hash of the catalog files, and uses it again on a match.
---

# The saved Verify report is keyed by commit and catalog hash

Verify refuses a worktree that has uncommitted changes, so a commit names all
that Verify examined. Verify keeps one saved report for each plan, and one for
the `audit` argument, with that commit and a hash of the catalog files on disk
as its key. As a result, `iwe-shipper` uses the verdict of the Implement loop
again, and does not run the tests again.

## Considered Options

- Key the report by a tree hash, or by hashes of the files of the plan.
  Rejected: a hash of only the plan files misses a change in a different file
  that a verification command can use.
- Key the report by the commit only. Rejected: an installed plugin is not a Git
  checkout, and a session can load a catalog that is different from the catalog
  in the commit.
- A handoff file that Implement commits for `iwe-shipper`. Rejected: the commit
  of the file changes the commit that the file identifies. Also, a commit of
  project state is not report-only, and Verify must be report-only.
- Do the search in the `iwe-verifier` rulebook. Rejected: a match then still
  needs one dispatch.

## Consequences

- The approvals of the user are in the report but not in its key. A request that
  quotes an approval does not use the saved report.
- A verification command that leaves uncommitted changes is a CRITICAL, because
  a saved report must describe a clean commit.
- Only `verify-cache.py` writes `.tmp/verify/`. A saved report is reliable only
  because of this rule.
