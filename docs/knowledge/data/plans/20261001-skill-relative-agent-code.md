---
type: plan
created: 2026-10-01
description: Rename every bundled scripts/ directory in the agentdev and self-improve plugins to agent-code/, reference skill scripts by a path relative to the skill directory instead of ${CLAUDE_SKILL_DIR}, and keep the variable only in Claude's allowed-tools field.
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
stage: done
completed: 2026-10-02
released: 2.0.0
---

# Reference bundled skill code by skill-relative agent-code paths

## Context

[Codex leaves ${CLAUDE_SKILL_DIR} unresolved in agentdev
skills](../bugs/codex-skill-dir-unresolved.md): the catalog tells the agent to
run bundled scripts as `${CLAUDE_SKILL_DIR}/scripts/<script>`, a text
substitution only Claude Code performs. OpenCode, the next host for these skill
bodies, does not substitute it either.

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
`Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`. The one other place the variable
appears is `create-skill`'s documentation of that field.

self-improve keeps `${CLAUDE_PLUGIN_ROOT}/agent-code/si`. Its executable sits at
the plugin root, not in a skill, so no skill-relative form exists for it.
self-improve is published only to Claude Code, which substitutes the variable,
and its hooks receive it from the host's environment.

Rejected alternatives:

- **Keep `${CLAUDE_SKILL_DIR}` and substitute it per host.** Codex shows skill
  text verbatim and defines no such variable
  (`codex-rs/ext/skills/src/fragments.rs` at `444da31`), so the Codex defect
  would remain without a Codex-side change.
- **Relative paths while keeping the name `scripts/`.** This matches the Agent
  Skills convention and the "scripts/" example in Codex and OpenCode prompts.
  But a misresolved path can then run a consuming repository's own script of the
  same name instead of failing.

Accepted costs:

- Codex counts a command as an implicit skill invocation only when it runs
  something under `<skill>/scripts/` (`codex-rs/ext/skills/src/host_outcome.rs`
  at `444da31`), so `agent-code/` steps go uncounted.
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
  `agent-code/<x>` (30 lines across 16 files). `create-skill`'s `allowed-tools`
  example becomes `Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`; its path rule
  changes in Task 3
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

- [x] `.agents/AGENTS.md`: a skill references its own bundled code as
  `agent-code/<file>` relative to the skill directory. `${CLAUDE_SKILL_DIR}`
  appears only in `allowed-tools`. A sibling skill is still reached by its
  namespaced invocation.
  - **Evidence:** commit "Document the agent-code/ path convention": the
    catalog-locations rule now names `agent-code/<file>`, the namespaced sibling
    invocation, and `${CLAUDE_SKILL_DIR}` only in `allowed-tools`
- [x] `skill-scripts`: the description and body name `agent-code/` as the
  bundled-code directory, and the test-path guidance becomes
  `plugin_root / 'skills/<name>/agent-code/<script>.sh'`
  - **Evidence:** commit "Document the agent-code/ path convention";
    validate_agent_files: 56/56 skills valid, 0 errors
- [x] `create-skill`: the `allowed-tools` example and the path rule match
  `.agents/AGENTS.md`
  - **Evidence:** commit "Document the agent-code/ path convention" (path rule)
    and commit "Move agentdev skill scripts to agent-code/" (example
    `Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`)
- [x] Plugin README: the test-suite paragraph names `agent-code/`
  - **Evidence:** commit "Document the agent-code/ path convention"

### Task 4: Point the validator's remediation at skill-relative paths

**Files:** Modify:
`py_packages/validate_agent_files/validate_agent_files/validators/catalog_paths.py`,
`py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py`,
`py_packages/validate_agent_files/tests/test_plugin_layout.py`,
`py_packages/validate_agent_files/pyproject.toml`,
`docker/desktop/agent-desktop.Dockerfile`, `.codex/setup-codex-cloud.sh`

- [x] Both remediation messages and the `catalog_paths` module docstring
  recommend a path relative to the skill directory instead of
  `${CLAUDE_SKILL_DIR}/...`. The wording stays repository-neutral: it does not
  name `agent-code/`, because the package is released independently.
  - **Evidence:** commit "Recommend skill-relative paths in validator
    remediation": `REMEDIATION`, `ESCAPE_REMEDIATION`, and the docstring say
    "relative to the skill directory" and name no directory
- [x] `test_plugin_layout.py`: the literal-path test asserts the new
  remediation, and the accepted-path test uses a skill-relative path
  - **Evidence:** commit "Recommend skill-relative paths in validator
    remediation": `test_literal_catalog_path_in_skill_body_fails` asserts the
    imported `REMEDIATION`; `test_skill_relative_path_is_accepted` passes
- [x] Bump the package version 1.0.0 → 1.0.1, with the
  `VALIDATE_AGENT_FILES_VERSION` pins in the Dockerfile and the Codex Cloud
  setup script that provisioning verifies against it
  - **Evidence:** commit "Recommend skill-relative paths in validator
    remediation"; `importlib.metadata.version('validate_agent_files')` reports
    1.0.1 after `uv sync`
- [x] `uv run pytest py_packages/validate_agent_files/tests` passes
  - **Evidence:** commit "Recommend skill-relative paths in validator
    remediation": 167 passed

### Task 5: Repoint knowledge-graph documents at the moved paths

**Files:** Modify: `docs/knowledge/data/spec/git-new-branch.md`,
`docs/knowledge/data/spec/iwe-workflow-skills.md`,
`docs/knowledge/data/archive/2.0.0/architecture/self-improve-runtime.md`,
`docs/knowledge/data/archive/1.0.0/architecture/agent-metadata-files.md`,
`docs/knowledge/data/bugs/pin-bumps-invalidate-map-docs.md`, and whichever
`docs/knowledge/data/codebase/` documents `stale-map-docs.py` reports

- [x] Update the `sources:` resources in the two specs, and the `sources:`
  resources and body anchors in the two architecture documents. For the closed
  bug, update only its `sources:` resource; its body records past evidence.
  - **Evidence:** commit "Repoint knowledge-graph documents at agent-code/
    paths": the two specs, two architecture documents, and the closed bug's
    `sources:` name `agent-code/` paths
- [x] Refresh every codebase-map document that
  `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py` reports
  stale, through `/agentdev:iwe-map`
  - **Evidence:** commit "Repoint knowledge-graph documents at agent-code/
    paths": 15 docs refreshed through `/agentdev:iwe-map`; `stale-map-docs.py`
    reports 27/27 FRESH, `RESULT=SUCCESS`
- [x] `iwe normalize` and `iwe schema validate` pass
  - **Evidence:** commit "Repoint knowledge-graph documents at agent-code/
    paths": both exit 0

### Task 6: Release the catalogs

**Files:** Modify: `.agents/plugins/agentdev/.claude-plugin/plugin.json`,
`.agents/plugins/agentdev/.codex-plugin/plugin.json`,
`.agents/plugins/self-improve/.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `docker/desktop/agent-desktop.Dockerfile`,
`.agents/plugins/self-improve/selfimprove/__init__.py`, `README.md`, and the
`docs/knowledge/data/codebase/` documents `stale-map-docs.py` reports

- [x] agentdev 4.0.0 → 4.1.0 in both manifests, the Claude marketplace entry,
  the Dockerfile's `AGENTDEV_PLUGIN_VERSION` pin that provisioning verifies
  against the marketplace, and the root README
  - **Evidence:** commit "Release agentdev 4.1.0 and self-improve 0.1.1": both
    manifests, marketplace entry, `AGENTDEV_PLUGIN_VERSION`, and README read
    4.1.0
- [x] self-improve 0.1.0 → 0.1.1 in its manifest, marketplace entry, package
  `__version__`, and the root README
  - **Evidence:** commit "Release agentdev 4.1.0 and self-improve 0.1.1":
    manifest, marketplace entry, `__version__`, and README read 0.1.1
- [x] Refresh the codebase-map documents the version bumps make stale, through
  `/agentdev:iwe-map`; `stale-map-docs.py` ends at `RESULT=SUCCESS`
  - **Evidence:** commit "Release agentdev 4.1.0 and self-improve 0.1.1": five
    docs re-stamped; `stale-map-docs.py` 27/27 FRESH, `RESULT=SUCCESS`
- [x] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes
  - **Evidence:** commit "Release agentdev 4.1.0 and self-improve 0.1.1": 56/56
    skills valid, 0 errors, 0 warnings

### Task 7: Confirm Claude Code resolves `agent-code/` against the skill directory

- [x] After `reinstall-agentdev-claude.sh`, invoke
  `/agentdev:pr-gen-description` in a Claude Code session in this repository,
  whose working directory has its own `scripts/`. Its script runs from the
  skill's `agent-code/`, with no "not found" retry.
  - **Evidence:** Claude Code 2.1.280, agentdev 4.1.0 reinstalled at local scope
    from this checkout, `claude -p /agentdev:pr-gen-description` on 2026-10-02:
    the skill's base directory was
    `<repo>/.agents/plugins/agentdev/skills/pr-gen-description`; the first Bash
    call ran `<base>/agent-code/review-git-changes.sh` (exit 0) with no retry;
    ticked in commit "Confirm Claude Code resolves agent-code/ against the skill
    directory"

### Task 8: Confirm Codex runs a bundled script from a live session

- [x] With Codex logged in and agentdev installed through
  `reinstall-agentdev-codex.sh`, invoke `$agentdev:pr-gen-description`. The
  first shell command that runs a bundled script runs the skill's
  `agent-code/review-git-changes.sh` by a path that exists. Then set the bug
  document to `stage: done`.
  - **Evidence:** codex-cli 0.156.1, agentdev 4.1.0 installed by
    `reinstall-agentdev-codex.sh` into
    `~/.codex/plugins/cache/agent-devcontainer/agentdev/4.1.0`,
    `codex exec '$agentdev:pr-gen-description'` on 2026-10-02: the first shell
    command read the sibling `code-review-standards/SKILL.md`, and the first
    script command ran
    `<plugin cache>/skills/pr-gen-description/agent-code/review-git-changes.sh --stat-only`
    (exit 0) with no failed attempt; the bug document is at `stage: done`;
    ticked in commit "Confirm Codex runs agent-code/ scripts and close the Codex
    bug"

### Task 9: CI passes on the branch

- [x] The `validate-agent-files` workflow passes on the pull request
  - **Evidence:** Agent files validation run 36999212113 on PR #245 at
    `cfe2939`: success, with every step run, including the plugin, self-improve,
    and validator test suites and the `agent-code/stale-map-docs.py` map check

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
  `allowed-tools` lines and `create-skill`'s documentation of the
  `allowed-tools` field (its example and its path rule)
- Tasks 7–9: the live Claude Code and Codex checks and the CI run

## Out of scope

- OpenCode support: [Load the agentdev catalog into OpenCode through a bridge
  plugin](20261001-opencode-catalog-bridge.md) builds on this plan.
- Publishing self-improve to Codex.
- `references/` and `assets/` directories: no plugin ships an `assets/`, and
  `references/` pages are read rather than executed, so the name collision does
  not apply.
- Past plans, which keep the paths that were true when they were written.

## Key references

- `.agents/AGENTS.md#validation-and-test-ownership › "Plugin tests must pass from a consumer's plugin cache."`
  — plugin tests resolve scripts through `plugin_root`
- `.agents/AGENTS.md#catalog-locations-and-portability › "Never write a repository-relative catalog path inside the"`
  — rule: own bundled code as `agent-code/<file>`, `${CLAUDE_SKILL_DIR}` only in
  `allowed-tools`
- `.agents/plugins/agentdev/skills/git-commit/SKILL.md › "allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)"`
  — representative `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`
- `.agents/plugins/agentdev/skills/git-commit/SKILL.md#create-the-commit-through-the-script › "${CLAUDE_SKILL_DIR}/scripts/git-commit.sh -- -m"`
  — representative skill-relative body steps
- `.agents/plugins/agentdev/skills/remote-codespace-session/SKILL.md#workflow › "${CLAUDE_SKILL_DIR}/scripts/codespace-ensure.sh --dry-run"`
  — the skill with the most body uses (7)
- `.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.sh::usage`
  — representative usage text printing `agent-code/...`
- `.agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.sh` —
  path to the sibling `git-merge-resolve` script
- `.agents/plugins/agentdev/skills/skill-scripts/SKILL.md › "Write and document a skill's bundled scripts so their"`
  — `agent-code/` convention and test-path guidance
- `.agents/plugins/agentdev/skills/create-skill/SKILL.md#frontmatter-follows-the-agent-skills-spec-and-there-is-no-agentsopenaiyaml › "Bash(${CLAUDE_SKILL_DIR}/agent-code/*)"`
  — `allowed-tools` example and path rule
- `.agents/plugins/agentdev/README.md#tests › "bundled with individual skills"`
  — test-suite paragraph naming `agent-code/`
- `.agents/plugins/agentdev/tests/conftest.py::plugin_root` — `plugin_root`
  fixture
- `.agents/plugins/agentdev/tests/test_close_issue.py::SCRIPT_PATH` —
  representative `SCRIPT_PATH = 'skills/.../agent-code/...'`
- `.claude/settings.json › "Bash(.agents/plugins/agentdev/skills/*/agent-code/*)"`
  — workspace Bash permission for bundled skill code
- `.agents/plugins/self-improve/hooks/hooks.json › "${CLAUDE_PLUGIN_ROOT}/scripts/si"`
  — `${CLAUDE_PLUGIN_ROOT}/agent-code/si` hook commands
- `.agents/plugins/self-improve/skills/improve/SKILL.md › "allowed-tools: Read, Grep, Glob"`
  — `si` invocations; also
  `.agents/plugins/self-improve/skills/apply/SKILL.md › "allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/si:*)"`,
  `.agents/plugins/self-improve/skills/reject/SKILL.md › "allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/si:*)"`,
  `.agents/plugins/self-improve/skills/rollback/SKILL.md › "allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/si:*)"`
- `.agents/plugins/self-improve/selfimprove/commands.py::capture_expansion` —
  authorization message naming `${CLAUDE_PLUGIN_ROOT}/agent-code/si`
- `.agents/plugins/self-improve/selfimprove/commands.py::self_test` — self-test
  required-file list
- `.agents/plugins/self-improve/tests/conftest.py::SI` — `SI` path constant
- `py_packages/validate_agent_files/validate_agent_files/validators/catalog_paths.py › "self-reference) or as a"`
  — docstring and `REMEDIATION`
- `py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py::ESCAPE_REMEDIATION`
  — `ESCAPE_REMEDIATION`
- `py_packages/validate_agent_files/tests/test_plugin_layout.py::test_literal_catalog_path_in_skill_body_fails`
  — remediation and accepted-path tests
- `py_packages/validate_agent_files/pyproject.toml › "version ="` — package
  version
- `.github/workflows/validate-agent-files.yml#jobs.validate-agent-files.steps.Check codebase map docs against their sources.run`
  — `stale-map-docs.py` CI step
- `docs/knowledge/tests/test_pin_metadata_masks.py::SCRIPT`,
  `docs/knowledge/tests/test_devcontainer_metadata_mask.py::SCRIPT`,
  `docs/knowledge/tests/test_pre_commit_rev_mask.py::SCRIPT` — `SCRIPT` path
  constants
- `docs/knowledge/data/spec/git-new-branch.md › "resource"`,
  `docs/knowledge/data/spec/iwe-workflow-skills.md › "resource"` — `sources:`
  script paths
- `docs/knowledge/data/archive/2.0.0/architecture/self-improve-runtime.md › "resource: .agents/plugins/self-improve/scripts/si"`,
  `docs/knowledge/data/archive/1.0.0/architecture/agent-metadata-files.md › "resource"`
  — script paths
- `.claude-plugin/marketplace.json › "version"`,
  `.agents/plugins/agentdev/.claude-plugin/plugin.json › "version"`,
  `.agents/plugins/agentdev/.codex-plugin/plugin.json › "version"`,
  `.agents/plugins/self-improve/.claude-plugin/plugin.json › "version"` —
  versions
- `docker/desktop/agent-desktop.Dockerfile › "ARG AGENTDEV_PLUGIN_VERSION=4.1.0"`
  — `AGENTDEV_PLUGIN_VERSION` and `VALIDATE_AGENT_FILES_VERSION` pins
- `.codex/setup-codex-cloud.sh › "AGENTDEV_PLUGIN_VERSION=4.1.0"` — the same two
  pins for Codex Cloud
