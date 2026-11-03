# Handoff: a reviewer agent for Ship's obligations (exploration in progress)

Temporary. This file tracks an open `/agentdev:iwe-explore` thread so its
decisions show up as diffs. It is deleted when `/agentdev:iwe-plan` takes the
thread into a plan, which becomes its durable home.

## Trigger

On pull request #657, the `iwe-shipper` agent set
`data/bugs/eval-skips-rereview-after-changes-requested` to `stage: done` without
writing its `## Fix` section, which step 6 of
`.agents/plugins/agentdev/agents/iwe-shipper.agent.md` requires, and its own
step 7 re-check missed the gap. Nothing enforces a done bug's `## Fix`: the plan
`data/plans/20261102-bug-lifecycle-and-sections` decided "no schema rule, CI
check, or refusal gate".

## Decided

- The `iwe-shipper` agent writes and enforces the `## Fix` section of every bug
  its plan's `release` list names.
- A new catalog agent, not yet named, reviews a plan against Ship's
  obligations. It has one rubric built from what `iwe-shipper.agent.md` requires,
  and runs both when `/agentdev:iwe-plan` files or revises a plan and on the
  result `iwe-shipper` commits.
- On the Ship side the new agent runs after the commit: `/agentdev:iwe-ship`
  dispatches `iwe-shipper`, which commits, then dispatches the new agent from a
  fresh context. A gap it finds is fixed in a follow-up commit.
- Verify moves out of `iwe-shipper`'s context: `/agentdev:iwe-ship` dispatches
  `iwe-verifier` itself, filed as `data/backlog/ship-verifies-before-dispatch`.
- A checker CLI, run by a pre-commit hook over `docs/knowledge/data/bugs/*.md`,
  fails any bug at `stage: done` with no `## Fix` heading. It is a CLI, not a
  pytest file; pytest tests cover the CLI on made-up bug files. CI enforces it
  through the pre-commit runs in `.github/workflows/primary-checks.yml` and
  `.github/workflows/ci.yml`.

## Findings

- `iwe` 0.29.3 accepts conditionals in a document schema only inside
  `frontmatter`. A document-level `if`/`then` or `anyOf` in
  `.iwe/schemas/bug.yaml` fails with "unknown keyword", so the bug schema cannot
  require `## Fix` only when `stage: done`.
- The pre-commit hooks `plan-checkboxes` and `no-status-field` in
  `.pre-commit-config.yaml` already gate the graph by running a pytest file over
  a whole directory. CI runs pre-commit over the pull request's commit range in
  `primary-checks.yml` and over all files in `ci.yml`.
- Every bug at `stage: done` has a `## Fix` section as of commit `12ab309f`, so
  the checker CLI starts green over the whole graph.

## Current question

When `/agentdev:iwe-plan` files or revises a plan, does it dispatch the new
agent alongside the `Durable Knowledge Auditor` agent, or does the `Durable
Knowledge Auditor` agent's rubric grow to cover Ship's obligations?

## Queued

- Whether one rubric covers both the plan-time run and the post-Ship run, or
  the new agent has a plan mode and a ship mode.
- Who writes the follow-up commit when the new agent finds a gap after
  `iwe-shipper` commits: a re-dispatched `iwe-shipper`, or `/agentdev:iwe-ship`.
- Recording the reversal of the "no schema rule, CI check, or refusal gate"
  decision in `data/plans/20261102-bug-lifecycle-and-sections`.
