---
type: plan
created: 2026-11-22
release: internal
description: Drop the iwe- prefix from the skills and agents of the agentdev-iwe plugin, which its namespace already identifies.
sources:
- resource: .agents/plugins/agentdev/skills/
- resource: .agents/plugins/agentdev/agents/
- resource: scripts/check-ship-records.py
---

# Drop the iwe- prefix from the agentdev-iwe skills and agents

## Context

ADR-0011 kept the `iwe-` prefix on the IWE skills because they shared one
directory with the `pr-*` skills. The split into the `agentdev-iwe` plugin
removes that reason: the namespace `agentdev-iwe:` already says which workflow a
skill belongs to. The maintainer decided to drop the prefix from all 12 skills
and all 8 agents.

## Approach

Each skill and agent loses its `iwe-` prefix, in its directory or file name, its
frontmatter `name`, and every reference to it:

| Skill                    | New name             | Agent                      | New name               |
| ------------------------ | -------------------- | -------------------------- | ---------------------- |
| `iwe-adversarial-review` | `adversarial-review` | `iwe-adversarial-reviewer` | `adversarial-reviewer` |
| `iwe-bootstrap`          | `bootstrap`          | `iwe-implementer`          | `implementer`          |
| `iwe-branch-name`        | `branch-name`        | `iwe-planner`              | `planner`              |
| `iwe-capture`            | `capture`            | `iwe-plan-reviewer`        | `plan-reviewer`        |
| `iwe-explore`            | `explore`            | `iwe-revision-evaluator`   | `revision-evaluator`   |
| `iwe-implement`          | `implement`          | `iwe-shipper`              | `shipper`              |
| `iwe-plan`               | `plan`               | `iwe-ship-reviewer`        | `ship-reviewer`        |
| `iwe-plan-review`        | `plan-review`        | `iwe-verifier`             | `verifier`             |
| `iwe-setup`              | `setup`              |                            |                        |
| `iwe-ship`               | `ship`               |                            |                        |
| `iwe-verify`             | `verify`             |                            |                        |
| `iwe-weekly`             | `weekly`             |                            |                        |

The script of the branch-name skill becomes `branch-name.py`. The scaffold moves
with the bootstrap skill, so every path into `skills/iwe-bootstrap/assets/`
follows it.

`iwe-ship-reviewer` stamps each shipped plan with a `## Ship review` that names
it. The archived plans keep the old stamp, so `scripts/check-ship-records.py`
accepts the stamp with the old name and the new one.

Archived documents, release pages, findings, and accepted ADRs keep the old
names: they record what existed when they were written.

In OpenCode the bridge registers skills by their bare names, so a user's own
`plan`, `explore`, `setup`, or `verify` skill collides with the one from
`agentdev-iwe`.

## Implementation Steps

### Task 1: Rename the skills

**Files:** Move: the 12 `.agents/plugins/agentdev-iwe/skills/iwe-*/` to their
new names, and `branch-name/agent-code/iwe-branch-name.py` to
`branch-name/agent-code/branch-name.py`. Modify: the `SKILL.md` of each.

- [ ] Each skill directory has the new name, and the frontmatter `name` of its
  `SKILL.md` is the same name.
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.

### Task 2: Rename the agents

**Files:** Move: the 8 `.agents/plugins/agentdev-iwe/agents/iwe-*.agent.md` to
their new names. Modify: each agent file.

- [ ] Each agent file has the new name, and its frontmatter `name` is the same
  name.

### Task 3: Point every path into the scaffold at the bootstrap skill

**Files:** Modify: the support links in `docs/knowledge/`,
`scripts/link-knowledge-support.py`, `.pre-commit-config.yaml`,
`.prettierignore`, `.github/renovate.json`,
`.github/workflows/validate-knowledge-base.yml`,
`docs/knowledge/tests/test_banned_frontmatter_keys.py`,
`docs/knowledge/tests/test_plan_release_schema.py`,
`docs/knowledge/tests/test_rank_and_base_schemas.py`.

- [ ] Each support link in `docs/knowledge/` resolves into
  `.agents/plugins/agentdev-iwe/skills/bootstrap/assets/`.
- [ ] `uv run pre-commit run link-knowledge-support --all-files` passes.
- [ ] `uv run pytest docs/knowledge/tests` passes.

### Task 4: Accept the new Ship review stamp

**Files:** Modify: `scripts/check-ship-records.py`,
`scripts/tests/test_check_ship_records.py`.

- [ ] A plan whose `## Ship review` opens with "`ship-reviewer` did this review
  on" passes the check.
- [ ] A plan whose `## Ship review` opens with "`iwe-ship-reviewer` did this
  review on" passes the check.

### Task 5: Name the skills and agents by their new names everywhere

**Files:** Modify: each file under `.agents/` that names an old name,
`AGENTS.md`, `scripts/tests/test_configure_opencode.py`,
`.github/workflows/validate-agent-files.yml`, `docs/knowledge/data/backlog.md`,
`docs/knowledge/data/backlog/exercise-removed-delta-blocks.md`,
`docs/knowledge/data/backlog/implement-opens-pr.md`,
`docs/knowledge/data/backlog/incremental-re-verify.md`,
`docs/knowledge/data/backlog/migrate-earlier-iwe-scaffold.md`,
`docs/knowledge/data/backlog/observe-adversarial-review-depth-on-opencode.md`,
`docs/knowledge/data/backlog/observe-planned-adversarial-review.md`,
`docs/knowledge/data/backlog/pr-merge-post-merge-cleanup.md`,
`docs/knowledge/data/backlog/verification-command-fix-is-tactical.md`,
`docs/knowledge/data/someday/rename-plan-document.md`,
`docs/knowledge/data/someday/revision-evaluator-calibration.md`.

- [ ] The leftover search in `## Verification` prints nothing.
- [ ] `uv run pytest .agents/plugins/agentdev-iwe/tests .agents/plugins/agentdev/tests`
  passes.
- [ ] `bun test ./.agents/opencode-bridge/tests` passes.
- [ ] `uv run scripts/check-anchors.py` exits 0.

### Task 6: Release agentdev-iwe 2.0.0

**Files:** Modify: `.claude-plugin/marketplace.json`,
`.agents/plugins/agentdev-iwe/.claude-plugin/plugin.json`.

- [ ] `agentdev-iwe` is at `2.0.0` in `.claude-plugin/marketplace.json` and in
  its `plugin.json`.

### Task 7: Observe the new names in live sessions

**Closed by:** the maintainer, in a container from the image that CI builds
after the merge.

- [ ] A Claude Code session lists `/agentdev-iwe:plan`.
- [ ] `/agentdev-iwe:branch-name` in a Claude Code session runs its script.
- [ ] An OpenCode session lists `agentdev-iwe:plan`.

## Acceptance

### Scenario: A user starts an IWE skill by its plain name

- **WHEN** a user types `/agentdev-iwe:plan`
- **THEN** the plan skill starts; `/agentdev-iwe:iwe-plan` no longer exists
- **Checked at ship:** `.agents/plugins/agentdev-iwe/skills/plan/SKILL.md`

### Scenario: A workflow skill dispatches a renamed agent

- **WHEN** a skill of `agentdev-iwe` dispatches one of its agents
- **THEN** it names the agent without the `iwe-` prefix
- **Checked at ship:** `.agents/plugins/agentdev-iwe/skills/` and
  `.agents/plugins/agentdev-iwe/agents/`

### Scenario: Plans shipped before the rename still pass the Ship records check

- **WHEN** an archived plan's `## Ship review` opens with "`iwe-ship-reviewer`
  did this review on"
- **THEN** `scripts/check-ship-records.py` accepts it
- **Test:**
  `scripts/tests/test_check_ship_records.py::test_review_by_former_agent_name_passes`

### Scenario: A plan shipped after the rename passes the Ship records check

- **WHEN** a plan's `## Ship review` opens with "`ship-reviewer` did this review
  on"
- **THEN** `scripts/check-ship-records.py` accepts it
- **Test:**
  `scripts/tests/test_check_ship_records.py::test_review_by_ship_reviewer_passes`

## Depends on

[Split the IWE workflow into the agentdev-iwe
plugin](20261122-split-agentdev-iwe-plugin.md)

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `uv run pytest .agents/plugins/agentdev-iwe/tests .agents/plugins/agentdev/tests docs/knowledge/tests scripts/tests/test_check_ship_records.py scripts/tests/test_configure_opencode.py`
- `bun test ./.agents/opencode-bridge/tests`
- `uv run scripts/check-anchors.py`
- Leftover search:
  `git grep -nE '\biwe-(adversarial-reviewer|adversarial-review|bootstrap|branch-name|capture|explore|implementer|implement|plan-reviewer|plan-review|planner|plan|revision-evaluator|setup|ship-reviewer|shipper|ship|verifier|verify|weekly)\b' -- .agents AGENTS.md scripts/tests/test_configure_opencode.py .github/workflows/validate-agent-files.yml docs/knowledge/data/backlog.md docs/knowledge/data/backlog/exercise-removed-delta-blocks.md docs/knowledge/data/backlog/implement-opens-pr.md docs/knowledge/data/backlog/incremental-re-verify.md docs/knowledge/data/backlog/migrate-earlier-iwe-scaffold.md docs/knowledge/data/backlog/observe-adversarial-review-depth-on-opencode.md docs/knowledge/data/backlog/observe-planned-adversarial-review.md docs/knowledge/data/backlog/pr-merge-post-merge-cleanup.md docs/knowledge/data/backlog/verification-command-fix-is-tactical.md docs/knowledge/data/someday/rename-plan-document.md docs/knowledge/data/someday/revision-evaluator-calibration.md`
  prints nothing.

## Out of scope

- The names in archived documents, release pages, findings, and accepted ADRs.
- The `iwe/<slug>/iter-<N>-<phase>` branch names.
- The `iwe` CLI and the `.iwe/` workspace.

## Key references

- `scripts/check-ship-records.py` › "OLD_OPENING = " — the earlier stamp that
  the check already accepts.
- `scripts/check-ship-records.py` › "did this review on <YYYY-MM-DD>." — the
  stamp that names the agent.
- `scripts/link-knowledge-support.py` › "SCAFFOLD = Path(" — the scaffold path
  that the support links follow.
- `scripts/tests/test_configure_opencode.py` › "'iwe-ship': 'deny'" — the
  explicit-only skill named in an OpenCode permission.
- `.pre-commit-config.yaml` › "id: link-knowledge-support" — the hook whose file
  pattern names the scaffold path.
