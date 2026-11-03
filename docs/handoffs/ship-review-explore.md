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
- `iwe-ship-reviewer` is one agent with two modes, both drawn from the steps
  of `iwe-shipper.agent.md`: plan mode, run by `/agentdev:iwe-plan-review` on a
  plan, and ship mode, run on what `iwe-shipper` committed.
- In ship mode `iwe-ship-reviewer` keeps a running checklist of Ship's
  obligations as it checks each one, and attaches it to the end of the shipped
  plan as a QA stamp. Ship mode therefore writes to the plan file; plan mode
  stays report-only.
- The QA stamp is a `## Ship review` section, the last section of the shipped
  plan, made of checkboxes. Its structure is fixed: the same items in the same
  order on every plan, and every item ticked with either `confirmed:` and its
  evidence or `N/A:` and the reason it does not apply.

- The fixed structure of `## Ship review`, which the pre-commit checker CLI also
  checks on a plan at `stage: done`: no commit SHAs, and no item for
  `iwe normalize` or `iwe schema validate`, which pre-commit already runs.

```markdown
## Ship review

Reviewed by `iwe-ship-reviewer` on <YYYY-MM-DD>.

- [x] Verify reported zero CRITICAL — confirmed: <Verify's verdict line>
- [x] Every `## Spec changes` operation is in its spec — confirmed: <spec keys> | N/A: `## Spec changes` is None
- [x] Every spec the plan created is linked from `data/spec.md` — confirmed: <keys> | N/A: no spec created
- [x] Every spec the plan retired was removed with `iwe delete` — confirmed: <keys> | N/A: no spec retired
- [x] The plan is `stage: done` with `completed` and no `rank` — confirmed: <completed date>
- [x] Every feature in `release` is `stage: implemented` — confirmed: <keys> | N/A: `release` lists no feature
- [x] Every bug in `release` is `stage: done` with no `rank` — confirmed: <keys> | N/A: `release` lists no bug
- [x] Every bug in `release` has a `## Fix` that links this plan — confirmed: <keys> | N/A: `release` lists no bug
- [x] Ship edited no hub, release page, or `data/log.md` — confirmed
```

- `/agentdev:iwe-ship` runs the review loop: it dispatches `iwe-shipper`,
  which commits, then dispatches `iwe-ship-reviewer` in ship mode. When
  `iwe-ship-reviewer` reports a gap, `/agentdev:iwe-ship` re-dispatches
  `iwe-shipper` to fix it in a follow-up commit and dispatches
  `iwe-ship-reviewer` again, up to 3 repeats. A fix pass never re-runs Verify
  in full. `iwe-shipper` does not dispatch `iwe-ship-reviewer`.

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

- `.agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py` keys
  a saved Verify report by the exact commit Verify ran on and the catalog
  digest. Ship's own commit moves `HEAD`, so a re-dispatched `iwe-shipper` that
  starts at its step 3 misses the saved report and runs Verify in full.

## Current question

How does a fix pass skip Verify: `iwe-shipper` gains a fix operation that takes
`iwe-ship-reviewer`'s gap list and performs only those missing operations, or
the saved Verify report stays valid across commits that change only
`docs/knowledge/data/`?

## Queued

- Recording the reversal of the "no schema rule, CI check, or refusal gate"
  decision in `data/plans/20261102-bug-lifecycle-and-sections`.
