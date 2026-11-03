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
- A new catalog agent, `iwe-ship-reviewer`, reviews a plan against Ship's
  obligations. It has one rubric built from what `iwe-shipper.agent.md` requires,
  and runs both when `/agentdev:iwe-plan` files or revises a plan and on the
  result `iwe-shipper` commits.
- On the Ship side `iwe-ship-reviewer` runs after the commit: `/agentdev:iwe-ship`
  dispatches `iwe-shipper`, which commits, then dispatches `iwe-ship-reviewer` from a
  fresh context. A gap it finds is fixed in a follow-up commit.
- A checker CLI, run by a pre-commit hook over `docs/knowledge/data/bugs/*.md`,
  fails any bug at `stage: done` with no `## Fix` heading. It is a CLI, not a
  pytest file; pytest tests cover the CLI on made-up bug files. CI enforces it
  through the pre-commit runs in `.github/workflows/primary-checks.yml` and
  `.github/workflows/ci.yml`.
- A new skill, `/agentdev:iwe-plan-review`, fans out to two catalog agents on
  one plan and returns their reports together: the `Durable Knowledge Auditor`
  agent, unchanged, and the new `iwe-ship-reviewer`.
- Nesting depth is 5 on both harnesses. Claude Code gets
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=5` in the `env` block of
  `~/.claude/settings.json`, the file the `agentic_tools` Ansible role already
  merges `cc-filter` hooks into. The devcontainer's OpenCode config sets
  `experimental.subagent_depth` to `5`; the writer is
  `py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py`, under the
  spec `data/spec/devcontainer-opencode-policy`. Catalog agents stop being
  leaves by design; this promotes `data/someday/nested-catalog-agent-dispatch`
  and reverses the leaf rule that `data/architecture/fresh-context-verify` and
  `data/architecture/autonomous-implement-loop` rest on.
- `iwe-shipper` gains the `Agent` tool and dispatches `iwe-verifier` itself
  from a fresh context, so only `iwe-verifier`'s report enters `iwe-shipper`'s
  context. `data/backlog/ship-verifies-before-dispatch` proposed
  `/agentdev:iwe-ship` dispatching `iwe-verifier` instead; its intent changes
  to match.

## Out of scope

- Refactoring `/agentdev:iwe-audit` and the `Durable Knowledge Auditor` agent
  into the shape `/agentdev:iwe-verify` and `iwe-verifier` have, and renaming
  the agent `iwe-auditor`. `/agentdev:iwe-audit` edits the audited file after
  approval in its default scope (`SKILL.md` lines 105–115), so the refactor has
  to settle where that edit lives first.

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

- Two callers of the durable-knowledge audit run inside a dispatched subagent,
  where a further dispatch is nested: `/agentdev:pr-review` runs
  `/agentdev:iwe-audit` in diff scope inside a `general-purpose` pass it
  dispatched, and `iwe-implementer`, when `/agentdev:iwe-implement-all`
  dispatches it, follows the `iwe-planner` rulebook in place, whose step 7
  dispatches the `Durable Knowledge Auditor` agent. OpenCode refuses a nested
  dispatch at its default `experimental.subagent_depth` of 1
  (`data/architecture/nested-subagent-dispatch`).
- `/agentdev:iwe-audit` also has an apply mode that edits the audited files
  after the user approves the report table. The `Durable Knowledge Auditor`
  agent has no `Edit` or `Write` tool.

- Claude Code 2.1.316 nests to depth 3 by default: the agent at the limit is
  not offered the `Agent` tool, even when its `tools:` lists it, and nothing
  errors. The environment variable `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` sets
  the limit; a server-side feature flag can also change the default. With the
  variable at `5` a chain reached depth 5 and the depth-5 agent had no `Agent`
  tool; at `6` it reached depth 6. Evidence: each subagent's `.meta.json`
  `spawnDepth` and the `result` event's `subagent_stats.max_depth`. OpenCode
  depths above 2 are unverified.
- On Claude Code an agent can dispatch only when its `tools:` list includes
  `Agent` or is omitted. `iwe-shipper`, `iwe-implementer`, and the `Durable
Knowledge Auditor` agent list tools without `Agent`.

## Current question

Does one rubric cover both the run `/agentdev:iwe-plan-review` makes on a plan
and the run after `iwe-shipper` commits, or does `iwe-ship-reviewer` have a plan
mode and a ship mode?

## Queued

- Who writes the follow-up commit when `iwe-ship-reviewer` finds a gap after
  `iwe-shipper` commits: a re-dispatched `iwe-shipper`, or `/agentdev:iwe-ship`.
- Recording the reversal of the "no schema rule, CI check, or refusal gate"
  decision in `data/plans/20261102-bug-lifecycle-and-sections`.
