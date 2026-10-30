---
type: plan
created: 2026-10-30
description: Cache the last Verify report per plan in the iwe-verify skill, keyed by the clean commit it ran on and the active catalog digest, so the Shipper and every other caller reuse a verdict instead of re-running the plan's test and e2e commands.
release:
- features/verify-report-cache
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T12:30:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
---

# Verify report cache

## Context

[Verify report cache](../features/verify-report-cache.md) is the feature. The
regular flow is Implement → Verify → Ship → `pr-open` on one branch. A plan that
first needs a merge — images published from the default branch and checked in CI
— resumes Implement on a `ship/<slug>/iter-<N>` branch and ships from there, so
the Implement loop's last Verify and the Shipper's Verify always judge the same
commit. Both run the plan's `## Verification` commands, and those test and e2e
runs are the cost. [Fresh-context
Verify](../architecture/fresh-context-verify.md) requires the verdict to come
from a fresh context, and the Implement loop's dispatched `iwe-verifier` already
is one, so the Shipper's repeat adds nothing.

## Approach

The cache lives in the `/agentdev:iwe-verify` skill, which every Verify caller
goes through: a session's dispatch route and the Shipper's in-place route. A
bundled stdlib-only Python script, `agent-code/verify-cache.py`, does the
deterministic part:

- `lookup <plan-key|audit> [--fresh]` fails fast on a dirty worktree
  (`git status --porcelain` non-empty), and otherwise returns the saved report
  when its `commit` equals `HEAD`, its `catalog_digest` equals the active
  catalog's, and `--fresh` is absent. Any other state is a miss that prints the
  current commit and digest.
- `save <plan-key|audit> --commit <sha> --verdict <verdict>` reads the report on
  stdin and overwrites the one saved report for that plan. It refuses when
  `HEAD` moved off `--commit` or the worktree is dirty, and accepts only the
  verdicts `Ready to ship`, `Blocked`, and `Audit`, so `Needs decision` is never
  saved.

The saved report is `.tmp/verify/<YYYYMMDD>-<slug>.md`, named by the plan file,
or `.tmp/verify/audit.md` in audit mode — one file per plan, overwritten like a
build folder. Its frontmatter carries `plan`, `commit`, `catalog_digest`,
`verdict`, and `saved_at`, and the body is the report verbatim. The script
writes `.tmp/verify/.gitignore` containing `*`, so the cache never dirties the
worktree it checks, including in a consuming repository that does not ignore
`.tmp/`.

The catalog digest is `sha256:<hex>` over every regular file under the plugin
root the script runs from (`parents[3]`), in sorted relative-path order with
each path and its content hashed, skipping `__pycache__` directories. That root
is the catalog the harness loaded, so an installed catalog outside the
repository still keys the cache. `stale-map-docs.py`'s `source_digest_for_paths`
is not reused: it hashes Git-tracked files, and an installed plugin is not a Git
checkout.

The Implement loop stops dispatching `iwe-verifier` directly and runs Verify
through the skill, so its verdicts land in the same cache the Shipper reads. The
verifier rulebook gains one check: a worktree left dirty by the
`## Verification` commands is a CRITICAL. The skill's session route keeps its
rule against performing any Verify step, except running the cache script.

Rejected:

- **The verifier writes a handoff for the Shipper alone.** A cache in the skill
  serves every caller the same way.
- **The cache lookup in the `iwe-verifier` rulebook.** An agent body rendered
  into a Codex TOML cannot reach a skill's bundled script plugin-relatively, and
  a hit would still cost a dispatch.
- **A committed handoff file.** Committing it changes the commit it
  fingerprints, and committing project state contradicts report-only Verify.
- **A tree hash, or blob hashes of the plan's files, as the key.** Verify and
  Ship run on one commit, so the commit is exact and simpler; scoped hashes
  would miss changes outside their scope.
- **Re-running only the `## Verification` commands at Ship.** Those commands are
  the cost the cache exists to remove.
- **Keeping one report per commit.** Only the latest is ever looked up; the
  ancestor reuse that would read older ones is a separate task.

## Implementation Steps

### Task 1: Write the cache script with its tests

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py`,
`.agents/plugins/agentdev/tests/test_verify_cache.py`

Follow `/agentdev:skill-scripts` for the `RESULT=` line, exit codes, and
`--help`, with `result_codes.py` imported the way `iwe-branch-name.py` does.
`lookup` results: `HIT` (prints `REPORT` and `COMMIT`), `MISS` (prints `COMMIT`
and `CATALOG_DIGEST`), `DIRTY_WORKTREE`. `save` results: `SUCCESS`,
`HEAD_MOVED`, `DIRTY_WORKTREE`. Bad arguments and a disallowed verdict are
`PREFLIGHT_ERROR`.

- [x] Tests through the `plugin_root` fixture in a temporary Git repository
  cover: a dirty worktree (tracked change, untracked file) fails `lookup` and
  `save`; a saved report for `HEAD` and the current digest is a `HIT`; a new
  commit, a changed catalog file, and `--fresh` are each a `MISS`; `save`
  overwrites the previous report; `save` refuses `HEAD_MOVED` and the verdict
  `Needs decision`; audit mode uses `audit.md`; the cache's own `.gitignore`
  keeps a saved report from dirtying the worktree.
  - **Evidence:** commit 45fff92 adds
    `.agents/plugins/agentdev/tests/test_verify_cache.py`, covering each listed
    case.
- [ ] `verify-cache.py` implemented; the tests pass.

### Task 2: Route the iwe-verify skill through the cache

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md`

- [ ] Both routes run `agent-code/verify-cache.py lookup` first with a decision
  table: `DIRTY_WORKTREE` stops and reports; `HIT` returns the saved report led
  by a line naming it as saved from `<commit>`; `MISS` runs Verify — the
  dispatch or the in-place rulebook — then pipes the report to `save` with the
  `MISS` commit unless the verdict is `Needs decision`. `save` refusing returns
  the report unsaved and says why. `--fresh` is passed only when the user's own
  request carries it and is never forwarded to the verifier. The frontmatter
  gains `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`, and the session
  route's no-Verify-step rule names the cache script as its one exception.

### Task 3: Fail Verify on a worktree its commands dirtied

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-verifier.agent.md`

- [ ] After the `## Verification` commands run, a non-empty
  `git status --porcelain` is a CRITICAL naming the dirty paths, with the
  recommendation to make the command leave the worktree clean.

### Task 4: Run the Implement loop's Verify through the skill

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`,
`.agents/plugins/agentdev/skills/iwe-implement/SKILL.md`

- [ ] `## Running the loop` steps 1, 3, and 4 run Verify through
  `/agentdev:iwe-verify` with the plan key and the user's approvals instead of
  dispatching `iwe-verifier` directly, and the `iwe-implement` skill's summary
  of the loop says the same. No agent the loop dispatches dispatches another.

### Task 5: Name a reused report in the Shipper's report

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`

- [ ] Step 3 states that the skill may return a saved report, which counts as
  the Verify report for every later step, and the `## Report` Verify verdict
  line names a reused report as saved from `<commit>`.

### Task 6: Record the cache in Fresh-context Verify

**Files:** Modify: `docs/knowledge/data/architecture/fresh-context-verify.md`

- [ ] `## Decision` gains the cache: a saved report is a fresh-context verdict
  keyed by commit and catalog digest, the lookup sits in the skill, and trust in
  `.tmp/verify/` rests on the rule that only the skill's script writes it.
  `## Rejected alternatives` gains the rulebook lookup, the committed handoff,
  and the tree or blob-hash key from `## Approach`.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md):

``` markdown
## MODIFIED Requirements

### Requirement: Implement verifies its own work and acts on the report

When a plan's last task closes, the Implement orchestrator — the user's session
for `/agentdev:iwe-implement`, and the `iwe-implement-all` coordinator for each
plan it runs — SHALL run Verify through `/agentdev:iwe-verify` and SHALL act on
every CRITICAL finding and every WARNING that names a concrete route, reporting
SUGGESTIONs only. A code or evidence finding SHALL be fixed under the Implement
rules and verified again, and a finding about the plan's intent SHALL go through
an evaluated revision. The orchestrator SHALL stop when a finding recurs after a
fix attempt, after three Verify rounds, or after one approved revision in the
run. No agent the loop dispatches SHALL dispatch another.

#### Scenario: Verify finds nothing to act on

- **WHEN** the plan's tasks are closed and Verify reports zero CRITICAL
  findings and no WARNING with a concrete route
- **THEN** the run ends with its rollup and the Verify verdict, and suggests
  `/agentdev:iwe-ship`

#### Scenario: Verify finds a code defect

- **WHEN** the Verify report carries a CRITICAL whose route is code or evidence
- **THEN** the orchestrator fixes it under the Implement rules, closes it with
  evidence, and runs Verify again through `/agentdev:iwe-verify`

#### Scenario: A finding recurs

- **WHEN** a finding the orchestrator already tried to fix appears in the next
  Verify report
- **THEN** the run stops and reports the finding, the fix it attempted, and the
  Verify report

#### Scenario: Verify needs an approval

- **WHEN** Verify reports `Needs decision` for a command with effects beyond the
  working tree
- **THEN** the run stops and names the approval, which the user grants by
  re-running the skill

#### Scenario: The coordinator implements every active plan

- **WHEN** the user runs `/agentdev:iwe-implement-all`
- **THEN** the coordinator dispatches `iwe-implementer` once per plan in
  dependency order, runs the same loop for that plan before the next, and
  re-posts each rollup with its Verify and evaluator verdicts

### Requirement: Normal shipping requires a clean independent verification

The Ship skill SHALL run the report-only Verify workflow before normal shipping
state changes and SHALL refuse to ship while Verify reports any CRITICAL
finding. Verify SHALL remain independently invocable and SHALL not edit code or
project state. Verify's rulebook SHALL be defined once, as the catalog agent
`iwe-verifier`, and every Verify run SHALL start from a fresh context:
`/agentdev:iwe-verify` SHALL dispatch `iwe-verifier` with a prompt carrying only
the plan key or audit mode and the user's approvals quoted verbatim, and
`iwe-shipper` SHALL follow that rulebook in its own context without dispatching
an agent. Verify SHALL run a verification command whose effects reach beyond the
working tree only under a quoted approval that names it, and otherwise SHALL
stop before it and report the approval it needs.

`/agentdev:iwe-verify` SHALL refuse to run on a dirty worktree, SHALL save each
report whose verdict is `Ready to ship`, `Blocked`, or `Audit` as the one saved
report for its plan or for audit mode, keyed by the commit it ran on and the
digest of the active agentdev catalog, and SHALL never save a `Needs decision`
report. On both routes it SHALL return the saved report, marked as saved and
without running any check or verification command, when that report's commit is
`HEAD` and its catalog digest is the active catalog's, unless the user's request
carries `--fresh`. A verification command that leaves the worktree dirty SHALL be
a CRITICAL finding.

#### Scenario: Verification reports no critical findings

- **WHEN** Ship invokes Verify for a completed plan and Verify returns zero
  CRITICAL findings
- **THEN** Ship may proceed to spec synchronization and later durable state
  transitions

#### Scenario: Verification reports a critical finding

- **WHEN** Ship invokes Verify and Verify reports one or more CRITICAL findings
- **THEN** Ship makes no shipping state transition and reports the blockers

#### Scenario: A plan is cancelled rather than shipped

- **WHEN** the user explicitly cancels an active plan
- **THEN** Ship records cancellation without requiring implementation
  verification or spec synchronization and performs no release or
  implemented-feature transition

#### Scenario: Verify is invoked outside Ship

- **WHEN** the user requests a mid-implementation check or a workspace audit
- **THEN** the skill dispatches `iwe-verifier`, which produces its
  evidence-backed report and stops without invoking Ship or mutating the graph

#### Scenario: The user verifies a plan without an approval

- **WHEN** the user runs `/agentdev:iwe-verify <plan>` and a `## Verification`
  command reaches beyond the working tree
- **THEN** the dispatch prompt carries the plan key and nothing else from the
  conversation, and `iwe-verifier` stops before that command and reports the
  approval it needs

#### Scenario: The user verifies a plan with an approval

- **WHEN** the user re-runs `/agentdev:iwe-verify <plan>` granting the approval
  the verifier reported, alongside other claims about the work
- **THEN** the dispatch prompt quotes the approval verbatim and leaves the other
  claims out, and `iwe-verifier` runs the approved command

#### Scenario: Ship runs Verify in place

- **WHEN** `iwe-shipper` reaches its Verify step
- **THEN** it follows the `iwe-verifier` rulebook in its own context and
  dispatches no agent

#### Scenario: Ship reuses the Implement loop's report

- **WHEN** the Implement loop's Verify saved a report for the plan and
  `iwe-shipper` reaches its Verify step on the same clean commit with the same
  active catalog
- **THEN** the skill returns the saved report, marked as saved from that commit,
  without running any check or verification command, and Ship proceeds on its
  verdict

#### Scenario: The commit or the catalog changed

- **WHEN** `HEAD` or the active catalog digest differs from the saved report's
- **THEN** Verify runs in full and its report replaces the saved one

#### Scenario: The worktree is dirty

- **WHEN** `/agentdev:iwe-verify` is invoked with a tracked change or an
  untracked file Git does not ignore
- **THEN** it stops before any Verify step and reports the dirty worktree

#### Scenario: A report that needs a decision is not saved

- **WHEN** Verify reports `Needs decision` and the user re-runs it granting the
  approval
- **THEN** Verify runs again rather than returning the earlier report

#### Scenario: The user asks for a fresh run

- **WHEN** the user runs `/agentdev:iwe-verify <plan> --fresh` on a commit
  with a saved report
- **THEN** Verify runs in full and its report replaces the saved one

#### Scenario: A verification command dirties the worktree

- **WHEN** a `## Verification` command leaves a tracked change or an unignored
  file behind
- **THEN** Verify reports a CRITICAL naming the dirty paths
```

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_verify_cache.py`
- `uv run pytest .agents/plugins/agentdev/tests`
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- `iwe normalize` then `iwe schema validate`, from the repository root

## Out of scope

- Re-checking incrementally from a saved report on an ancestor commit —
  [Re-verify incrementally from a saved
  report](../backlog/incremental-re-verify.md).
- Protecting `.tmp/verify/` against a session that writes it by hand; the rule
  that only the skill's script writes it is the protection.
- Reusing a report across a rebase, a squash merge, or a fresh container.

## Key references

Verified anchor points (line numbers as of 2026-10-30):

- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:1` — frontmatter
  (`allowed-tools` added)
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:13` —
  `## From inside iwe-shipper`
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:21` — `## From a session`
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:40` — `## Rules`
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md:91` — run the plan's
  `## Verification` commands
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:130` —
  `## Running the loop`
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:138` — step 1,
  dispatch `iwe-verifier`
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:147` — step 3,
  dispatch `iwe-verifier` again
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:165` — step 4,
  Verify again
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:19` — loop summary
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:71` — step 3, Run Verify
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:166` — Verify verdict
  report line
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py:19`
  — `bin/` path insertion for `result_codes`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:369` —
  `source_digest_for_paths`, not reused
- `.agents/plugins/agentdev/tests/conftest.py:23` — `plugin_root` fixture
- `docs/knowledge/data/spec/iwe-workflow-skills.md:293` — Implement verifies its
  own work
- `docs/knowledge/data/spec/iwe-workflow-skills.md:419` — Normal shipping
  requires a clean independent verification
- `docs/knowledge/data/architecture/fresh-context-verify.md:15` — `## Decision`
