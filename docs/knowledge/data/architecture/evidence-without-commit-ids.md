---
type: architecture
description: Plan task evidence names a check Verify can repeat — a test id or command, a file and anchor, or a CI run or PR — never a commit id alone, so a task's tick lands in the same commit as its code.
sources:
- resource: docs/knowledge/data/plans/20261109-evidence-without-commit-ids.md
- resource: docs/knowledge/data/backlog/resilient-task-evidence.md
---

# Evidence without commit ids

## Decision

A ticked plan task's `- **Evidence:**` line names a check Verify can repeat in
the current tree, by kind:

- Code: a test id (its path and test name) or a command, which Verify re-runs
  against the current tree.
- Docs or config with no test: the file and anchor that changed.
- External work: the CI run or the PR that closes it, which must stand alone.

A commit id on its own is not evidence. Verify re-runs a named test or command
and treats one that fails or no longer exists as an unsupported tick. The
residue rule stands: raw command stdout, an ephemeral identifier, and an
uncommitted `.tmp/` harness are not evidence. The `plan-checkboxes` gate checks
shape only.

## Why

Every reader of evidence — the `plan-checkboxes` gate, Verify, and the Ship run
that repeats Verify — runs before merge; nothing reads a shipped plan's evidence
after merge. A commit id buys nothing those readers need, while rebase, squash
merge, and amend rewrite it, and a check Verify can re-run is what lets Verify
judge a tick the same way every time.

## Same-commit rule

With nothing left that must name a commit, a task's code, its checkbox flip, and
its evidence line land in one commit. One edit still ticks one box, and one task
still makes one commit.

## Alternatives rejected

- **Keep commit ids.** Nothing reads evidence after merge, and the rule costs a
  second commit per task and a revision round whenever the named hash is wrong.
- **The PR number.** It survives squash, but it points at the whole change, so
  Verify still has nothing per task to repeat.
- **A test id only.** Docs, config, and external work have no test; each needs
  its own kind of evidence anyway.
- **Free text checked for shape only.** Verify's judgment flips between runs
  when a line names nothing it can repeat.
