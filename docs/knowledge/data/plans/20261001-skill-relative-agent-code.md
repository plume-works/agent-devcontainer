---
type: plan
created: 2026-10-01
description: Rename every bundled scripts/ directory in the agentdev and self-improve plugins to agent-code/, reference skill scripts by a path relative to the skill directory instead of ${CLAUDE_SKILL_DIR}, and keep the variable only in Claude's allowed-tools field.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-01T12:00:00Z
sources:
- resource: .agents/AGENTS.md
- resource: .agents/plugins/agentdev/skills
- resource: .agents/plugins/self-improve
- resource: py_packages/validate_agent_files/validate_agent_files/validators/catalog_paths.py
- resource: py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py
- resource: https://github.com/openai/codex/blob/444da31/codex-rs/ext/skills/src/catalog_prompt.rs
- resource: https://github.com/anomalyco/opencode/blob/0112a92/packages/opencode/src/tool/skill.ts
- resource: https://github.com/openai/codex/blob/444da31/codex-rs/ext/skills/src/fragments.rs
- resource: https://github.com/openai/codex/blob/444da31/codex-rs/ext/skills/src/host_outcome.rs
---

# Reference bundled skill code by skill-relative agent-code paths

## Context

[Codex leaves ${CLAUDE_SKILL_DIR} unresolved in agentdev skills](../bugs/codex-skill-dir-unresolved.md):
the catalog tells the agent to run bundled scripts as
`${CLAUDE_SKILL_DIR}/scripts/<script>`, a text substitution only Claude Code
performs. OpenCode, the next host for these skill bodies, does not substitute it
either.

All three hosts already tell the model that a relative path in a `SKILL.md`
resolves against the skill's directory: Claude Code prints
`Base directory for this skill: <dir>`, Codex's skill instructions say so
explicitly, and OpenCode appends "Relative paths in this skill (e.g., scripts/,
reference/) are relative to this base directory." A relative path therefore
works everywhere without host-specific substitution.

A relative `scripts/<script>` is ambiguous when the agent resolves it against
its working directory instead: a consuming repository can have its own top-level
`scripts/` — this one does. Naming the bundled directory `agent-code/` removes
that collision.

## Approach

Rename each bundled `scripts/` directory to `agent-code/` — the 15 under
agentdev skills and `self-improve/scripts`. In skill bodies, reference a bundled
script as `agent-code/<script>`, relative to the skill directory. Keep
`${CLAUDE_SKILL_DIR}` only in `allowed-tools`, which only Claude Code reads and
whose permission patterns need an absolute path:
`Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`.

self-improve keeps `${CLAUDE_PLUGIN_ROOT}/agent-code/si`. Its executable sits at
the plugin root, not in a skill, so no skill-relative form exists for it.
self-improve is published only to Claude Code, which substitutes the variable,
and its hooks receive it from the host's environment.

Rejected alternatives:

- **Keep `${CLAUDE_SKILL_DIR}` and substitute it per host.** Codex shows skill
  text verbatim and defines no such variable
  (`codex-rs/ext/skills/src/fragments.rs:92-107` at `444da31`), so the Codex
  defect would remain without a Codex-side change.
- **Relative paths while keeping the name `scripts/`.** This matches the Agent
  Skills convention and the "scripts/" example in Codex and OpenCode prompts.
  But a misresolved path can then run a consuming repository's own script of the
  same name instead of failing.

Accepted costs:

- Codex counts a command as an implicit skill invocation only when it runs
  something under `<skill>/scripts/`
  (`codex-rs/ext/skills/src/host_outcome.rs:75` at `444da31`), so `agent-code/`
  steps go uncounted.
- Claude Code's guaranteed substitution in skill bodies becomes resolution by
  the model; Task 7 checks that it holds.

Scripts locate their own helpers through `BASH_SOURCE` or `__file__`, and the
skill directory depth does not change, so no script's sourcing logic moves.

## Implementation Steps

### Task 1: Move agentdev skill scripts to `agent-code/`

**Files:** Modify: the 15 `.agents/plugins/agentdev/skills/*/scripts/`
directories (moved to `agent-code/` with `git mv`), their `SKILL.md` files, the
usage text inside the moved scripts, `.agents/plugins/agentdev/tests/test_*.py`,
`docs/knowledge/tests/test_*_mask*.py`,
`.github/workflows/validate-agent-files.yml`, `.claude/settings.json`,
`.agents/plugins/agentdev/bin/result-codes.sh`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [x] `git mv` every `skills/<name>/scripts` to `skills/<name>/agent-code`
  - **Evidence:** commit "Move agentdev skill scripts to agent-code/": 15
    renames; `ls -d .agents/plugins/agentdev/skills/*/scripts` finds none
- [x] In every `SKILL.md` body, replace `${CLAUDE_SKILL_DIR}/scripts/<x>` with
  `agent-code/<x>` (30 lines across 16 files, including `create-skill`'s
  `allowed-tools` example; its path rule changes in Task 3)
  - **Evidence:** commit "Move agentdev skill scripts to agent-code/";
    `grep -rn 'CLAUDE_SKILL_DIR' .agents/plugins/agentdev --include=SKILL.md`
    matches only `allowed-tools` lines, the `create-skill` example of one, and
    the `create-skill` path rule left for Task 3
- [x] Change every agentdev `allowed-tools` line to
  `Bash(${CLAUDE_SKILL_DIR}/agent-code/*)` (14 skills)
  - **Evidence:** commit "Move agentdev skill scripts to agent-code/": all 14
    lines read `Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`
- [x] Repoint the `SKILL.md` links to bundled scripts (`](scripts/<x>)`), the
  workspace permission `Bash(.agents/plugins/agentdev/skills/*/scripts/*)` in
  `.claude/settings.json` and the consumption guide's mention of it, the
  `result-codes.sh` header comment, and `update-branch.sh`'s path to the sibling
  `git-merge-resolve` script
  - **Evidence:** commit "Move agentdev skill scripts to agent-code/";
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`:
    56/56 skills valid, 0 errors
- [x] Update usage and help text inside the moved scripts that prints
  `${CLAUDE_SKILL_DIR}/scripts/...` to print `agent-code/...`
  - **Evidence:** commit "Move agentdev skill scripts to agent-code/"; no
    `${CLAUDE_SKILL_DIR}/scripts` remains under `skills/*/agent-code`
- [x] Repoint the plugin tests' `skills/<name>/scripts/` paths and the three
  `docs/knowledge/tests` `SCRIPT` constants to `agent-code/`
  - **Evidence:** commit "Move agentdev skill scripts to agent-code/"; the full
    run below exercises every repointed path
- [x] Repoint the `stale-map-docs.py` step in `validate-agent-files.yml`
  - **Evidence:** commit "Move agentdev skill scripts to agent-code/"
- [x] `uv run pytest .agents/plugins/agentdev/tests docs/knowledge/tests` passes
  - **Evidence:** commit "Move agentdev skill scripts to agent-code/": 148
    passed

### Task 2: Move the self-improve dispatcher to `agent-code/`

**Files:** Modify: `.agents/plugins/self-improve/scripts/` (moved to
`agent-code/`), `.agents/plugins/self-improve/hooks/hooks.json`,
`.agents/plugins/self-improve/skills/{apply,improve,reject,rollback}/SKILL.md`,
`.agents/plugins/self-improve/selfimprove/commands.py`,
`.agents/plugins/self-improve/tests/**`

- [x] `git mv .agents/plugins/self-improve/scripts .agents/plugins/self-improve/agent-code`
  - **Evidence:** commit "Move the self-improve dispatcher to agent-code/":
    `scripts/si` and `scripts/si.py` renamed
- [x] Replace `${CLAUDE_PLUGIN_ROOT}/scripts/si` with
  `${CLAUDE_PLUGIN_ROOT}/agent-code/si` in all 7 hook commands, the four skills
  (bodies and `allowed-tools`), and the authorization message in `commands.py`
  - **Evidence:** commit "Move the self-improve dispatcher to agent-code/";
    `grep -rn 'scripts/si' .agents/plugins/self-improve` prints nothing
- [x] Repoint the self-test's required-file entry `scripts/si` in `commands.py`
  - **Evidence:** commit "Move the self-improve dispatcher to agent-code/";
    `test_dispatcher.py::test_self_test_reports_ok` passes
- [x] Repoint `SI` in `tests/conftest.py` and every other test that names
  `scripts/si`
  - **Evidence:** commit "Move the self-improve dispatcher to agent-code/";
    every integration test runs the dispatcher through `SI`
- [x] `uv run pytest .agents/plugins/self-improve/tests` passes
  - **Evidence:** commit "Move the self-improve dispatcher to agent-code/": 574
    passed, 14 skipped (13 live tests gated on `SELF_IMPROVE_RUN_LIVE`, one
    unwritable-root test that root bypasses)

### Task 3: Update the catalog's path convention

**Files:** Modify: `.agents/AGENTS.md`,
`.agents/plugins/agentdev/skills/skill-scripts/SKILL.md`,
`.agents/plugins/agentdev/skills/create-skill/SKILL.md`,
`.agents/plugins/agentdev/README.md`

- [ ] `.agents/AGENTS.md`: a skill references its own bundled code as
  `agent-code/<file>` relative to the skill directory. `${CLAUDE_SKILL_DIR}`
  appears only in `allowed-tools`. A sibling skill is still reached by its
  namespaced invocation.
- [ ] `skill-scripts`: the description and body name `agent-code/` as the
  bundled-code directory, and the test-path guidance becomes
  `plugin_root / 'skills/<name>/agent-code/<script>.sh'`
- [ ] `create-skill`: the `allowed-tools` example and the path rule match
  `.agents/AGENTS.md`
- [ ] Plugin README: the test-suite paragraph names `agent-code/`

### Task 4: Point the validator's remediation at skill-relative paths

**Files:** Modify:
`py_packages/validate_agent_files/validate_agent_files/validators/catalog_paths.py`,
`py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py`,
`py_packages/validate_agent_files/tests/test_plugin_layout.py`,
`py_packages/validate_agent_files/pyproject.toml`

- [ ] Both remediation messages and the `catalog_paths` module docstring
  recommend a path relative to the skill directory instead of
  `${CLAUDE_SKILL_DIR}/...`. The wording stays repository-neutral: it does not
  name `agent-code/`, because the package is released independently.
- [ ] `test_plugin_layout.py`: the literal-path test asserts the new
  remediation, and the accepted-path test uses a skill-relative path
- [ ] Bump the package version 1.0.0 → 1.0.1
- [ ] `uv run pytest py_packages/validate_agent_files/tests` passes

### Task 5: Repoint knowledge-graph documents at the moved paths

**Files:** Modify: `docs/knowledge/data/spec/git-new-branch.md`,
`docs/knowledge/data/spec/iwe-workflow-skills.md`,
`docs/knowledge/data/architecture/self-improve-runtime.md`,
`docs/knowledge/data/architecture/agent-metadata-files.md`,
`docs/knowledge/data/bugs/pin-bumps-invalidate-map-docs.md`, and whichever
`docs/knowledge/data/codebase/` documents `stale-map-docs.py` reports

- [ ] Update `sources:` resources and body anchors in the two specs and two
  architecture documents. For the closed bug, update only its `sources:`
  resource; its body records past evidence.
- [ ] Refresh every codebase-map document that
  `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py` reports
  stale, through `/agentdev:iwe-map`
- [ ] `iwe normalize` and `iwe schema validate` pass

### Task 6: Release the catalogs

**Files:** Modify: `.agents/plugins/agentdev/.claude-plugin/plugin.json`,
`.agents/plugins/agentdev/.codex-plugin/plugin.json`,
`.agents/plugins/self-improve/.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`

- [ ] agentdev 4.0.0 → 4.1.0 in both manifests and the Claude marketplace entry
- [ ] self-improve 0.1.0 → 0.1.1 in its manifest and marketplace entry
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes

### Task 7: Confirm Claude Code resolves `agent-code/` against the skill directory

- [ ] After `reinstall-agentdev-claude.sh`, invoke
  `/agentdev:pr-gen-description` in a Claude Code session in this repository,
  whose working directory has its own `scripts/`. Its script runs from the
  skill's `agent-code/`, with no "not found" retry.

### Task 8: Confirm Codex runs a bundled script from a live session

- [ ] With Codex logged in and agentdev installed through
  `reinstall-agentdev-codex.sh`, invoke `$agentdev:pr-gen-description`. The
  first shell command runs the skill's `agent-code/review-git-changes.sh` by a
  path that exists. Then set the bug document to `stage: done`.

### Task 9: CI passes on the branch

- [ ] The `validate-agent-files` workflow passes on the pull request

## Spec changes

None — no behavioral change to a spec contract. The bundled-code path convention
lives in `.agents/AGENTS.md` and the validator's remediation, both updated by
this plan. The specs it touches change only their `sources:` paths.

## Verification

- `uv run pytest .agents/plugins/agentdev/tests .agents/plugins/self-improve/tests py_packages/validate_agent_files/tests docs/knowledge/tests`
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py` reports
  no stale document
- `grep -rnE '\$\{CLAUDE_SKILL_DIR\}/scripts|/scripts/si|skills/[a-z-]+/scripts' .agents docs/knowledge/data/spec docs/knowledge/data/architecture py_packages .github`
  prints nothing
- `grep -rn 'CLAUDE_SKILL_DIR' .agents/plugins --include=SKILL.md` matches only
  `allowed-tools` lines
- Tasks 7–9: the live Claude Code and Codex checks and the CI run

## Out of scope

- OpenCode support:
  [Load the agentdev catalog into OpenCode through a bridge plugin](20261001-opencode-catalog-bridge.md)
  builds on this plan.
- Publishing self-improve to Codex.
- `references/` and `assets/` directories: no plugin ships an `assets/`, and
  `references/` pages are read rather than executed, so the name collision does
  not apply.
- Past plans, which keep the paths that were true when they were written.

## Key references

Verified anchor points (line numbers as of 2026-10-02):

- `.agents/AGENTS.md:16-17` — plugin tests resolve scripts through `plugin_root`
- `.agents/AGENTS.md:33-35` — rule requiring `${CLAUDE_SKILL_DIR}/...` inside a
  skill
- `.agents/plugins/agentdev/skills/git-commit/SKILL.md:4` — representative
  `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)`
- `.agents/plugins/agentdev/skills/git-commit/SKILL.md:33-34` — representative
  body steps using the variable
- `.agents/plugins/agentdev/skills/remote-codespace-session/SKILL.md:40-123` —
  the skill with the most body uses (7)
- `.agents/plugins/agentdev/skills/git-new-branch/scripts/git-new-branch.sh:77-79`
  — representative usage text printing `${CLAUDE_SKILL_DIR}/scripts/...`
- `.agents/plugins/agentdev/skills/skill-scripts/SKILL.md:3,13,96,104,325` —
  `scripts/` convention and test-path guidance
- `.agents/plugins/agentdev/skills/create-skill/SKILL.md:42,63` —
  `allowed-tools` example and path rule
- `.agents/plugins/agentdev/README.md:142` — test-suite paragraph naming
  `scripts/`
- `.agents/plugins/agentdev/tests/conftest.py:22-24` — `plugin_root` fixture
- `.agents/plugins/agentdev/tests/test_close_issue.py:15` — representative
  `SCRIPT_PATH = 'skills/.../scripts/...'`
- `.agents/plugins/self-improve/hooks/hooks.json:9,22,35,48,60,73,85` —
  `${CLAUDE_PLUGIN_ROOT}/scripts/si` hook commands
- `.agents/plugins/self-improve/skills/improve/SKILL.md:4,21,27,35,50,84` — `si`
  invocations; also `apply/SKILL.md:4,19`, `reject/SKILL.md:4,14,27`,
  `rollback/SKILL.md:4,14,31`
- `.agents/plugins/self-improve/selfimprove/commands.py:159` — authorization
  message naming `${CLAUDE_PLUGIN_ROOT}/scripts/si`
- `.agents/plugins/self-improve/tests/conftest.py:18` — `SI` path constant
- `py_packages/validate_agent_files/validate_agent_files/validators/catalog_paths.py:9,24-27`
  — docstring and `REMEDIATION`
- `py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py:23-26`
  — `ESCAPE_REMEDIATION`
- `py_packages/validate_agent_files/tests/test_plugin_layout.py:134-155` —
  remediation and accepted-path tests
- `py_packages/validate_agent_files/pyproject.toml:9` — package version
- `.github/workflows/validate-agent-files.yml:93` — `stale-map-docs.py` CI step
- `docs/knowledge/tests/test_pin_metadata_masks.py:19`,
  `test_devcontainer_metadata_mask.py:19`, `test_pre_commit_rev_mask.py:19` —
  `SCRIPT` path constants
- `docs/knowledge/data/spec/git-new-branch.md:9,12`,
  `docs/knowledge/data/spec/iwe-workflow-skills.md:10,14,15,17` — `sources:`
  script paths
- `docs/knowledge/data/architecture/self-improve-runtime.md:8,53`,
  `docs/knowledge/data/architecture/agent-metadata-files.md:8,154,156` — script
  paths
- `.claude-plugin/marketplace.json:13,19`,
  `.agents/plugins/agentdev/.claude-plugin/plugin.json:3`,
  `.agents/plugins/agentdev/.codex-plugin/plugin.json:3`,
  `.agents/plugins/self-improve/.claude-plugin/plugin.json:3` — versions
