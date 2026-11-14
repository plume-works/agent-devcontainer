---
type: adr
stage: accepted
description: Verify keeps one saved report for each plan, with the commit and a hash of the catalog files as its key, and uses it again on a match.
---

# The key of the saved Verify report is the commit and the catalog hash

Verify refuses a worktree that has uncommitted changes, so a commit names all
that Verify examined. Verify keeps one saved report for each plan, and one for
the `audit` argument, with that commit and a hash of the catalog files on disk
as its key. As a result, `iwe-shipper` uses the verdict of the Implement session
again, and does not run the tests again.

## Considered Options

- Use a tree hash, or hashes of the files of the plan, as the key of the report.
  Rejected: a hash of only the plan files misses a change in a different file
  that a verification command can use.
- Use only the commit as the key of the report. Rejected: an installed plugin is
  not a Git checkout, and a session can load a catalog that is different from
  the catalog in the commit.
- A handoff file that Implement commits for `iwe-shipper`. Rejected: the commit
  of the file changes the commit that the file identifies. Also, a commit of
  project state is not report-only, and Verify must be report-only.
- Do the search in the `iwe-verifier` rulebook. Rejected: a match then still
  starts one subagent.

## Consequences

- The approvals of the user are in the report but not in its key. A request that
  quotes an approval does not use the saved report.
- A verification command that leaves uncommitted changes is a CRITICAL, because
  a saved report must describe a clean commit.
- Only `verify-cache.py` writes `.tmp/verify/`. Only this rule makes a saved
  report safe to use.
