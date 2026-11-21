---
type: adr
stage: accepted
---

# The saved Verify report is keyed by commit and catalog hash

Verify refuses a dirty worktree, so a commit fully names what it judged. Verify
keeps one saved report for each plan, and one for the `audit` argument, keyed by
that commit and a hash of the catalog files on disk. `iwe-shipper` then reuses
the Implement session's verdict on the same commit instead of repeating its test
runs. Each report is overwritten, because only the latest one is ever looked up.

## Considered Options

- Key the report by a tree hash, or by hashes of the plan's files. Rejected:
  Verify and Ship run on one commit, so the commit is exact, and hashes scoped
  to the plan's files miss changes outside that scope that a verification
  command can still depend on.
- Key the report by the commit only. Rejected: an installed plugin is not a Git
  checkout, and a session can load a catalog that differs from the one the
  commit holds, so the catalog hash covers the files on disk.
- A handoff file that Implement commits for `iwe-shipper`. Rejected: committing
  it changes the commit that it fingerprints, and committing project state
  contradicts report-only Verify.
- Look up the saved report in the `iwe-verifier` rulebook. Rejected: a hit would
  still cost a dispatch.

## Consequences

- The user's approvals are recorded in the report but are not part of its key.
  An approval changes a verdict only by running a command that a saved report
  lists as `not run`, so a request that quotes an approval skips the look-up
  instead.
- A verification command that leaves uncommitted changes is a CRITICAL, because
  a saved report must describe a clean commit.
- Trust in `.tmp/verify/` rests on the rule that only `verify-cache.py` writes
  it, not on any protection against a hand-written file.
