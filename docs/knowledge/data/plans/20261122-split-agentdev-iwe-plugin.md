---
type: plan
created: 2026-11-22
release: internal
description: Move the IWE workflow into its own plugin, agentdev-iwe, with catalog scripts on uv sharing the agentdev-lib package.
sources:
- resource: .claude-plugin/marketplace.json
- resource: .agents/plugins/agentdev/
- resource: ansible/roles/agent_catalog/
---

# Split the IWE workflow into the agentdev-iwe plugin

## Context

The maintainer approved this reason for the split:

``` text
`agentdev` has grown into a monolith. Its skills differ in how much they impose. The `pr-*` and git skills are generic enough for any repository. The IWE skills are heavy and prescriptive: they assume a knowledge graph and a fixed plan → implement → ship workflow. Most of them can be started by the model on their own, so they intrude on sessions that never asked for them. Users should be able to choose which skill sets they install. The IWE workflow moves to its own plugin, `agentdev-iwe`. This is the first of several splits.
```

Of the 12 `iwe-*` skills, only `iwe-plan`, `iwe-setup`, `iwe-ship`, and
`iwe-weekly` set `disable-model-invocation: true`.

The IWE scripts import modules from the `bin/` of `agentdev` through `sys.path`.
An installed plugin is a separate copy, so a script in `agentdev-iwe` cannot
reach the `bin/` of `agentdev`. This sets the order of the work: the shared code
becomes a package before the skills move.

## Approach

- **Shared code.** `py_packages/agentdev_lib/` becomes the `agentdev-lib`
  package. It holds the modules that scripts of both plugins import:
  `result_codes`, `skill_common`, and `git_default_branch`. `depends_on` and the
  executables stay in the `bin/` of `agentdev`.
- **Scripts on uv.** Each plugin is a uv project. Its `pyproject.toml` pins
  `agentdev-lib==X.Y` and names no source. Every script in `bin/` and
  `skills/*/agent-code/` starts with `#!/usr/bin/env -S uv run --quiet`. The
  root `pyproject.toml` makes each `.agents/plugins/*` a workspace member and
  points `agentdev-lib` at `py_packages/agentdev_lib` with `[tool.uv.sources]`.
  In a checkout, the scripts run the local package, and an edit applies at once.
  In a plugin cache, the first run downloads the package from PyPI and writes
  `uv.lock` and `.venv/` in the cache. `uv` is the parent of the script, so a
  script that a terminating signal ends still prints its `SIGNAL_*` result last,
  but its caller sees exit status 128 + the signal number, not a signal death.
  The maintainer accepted this.
- **Pins in step.** A pre-commit hook writes the version from
  `py_packages/agentdev_lib/pyproject.toml` into each plugin's pin. A PR check
  fails when `py_packages/agentdev_lib/` changed since the latest
  `agentdev-lib/*` tag and its version did not.
- **Publishing.** On a push to `main`, a workflow compares the package version
  with the `agentdev-lib/*` tags. For a new version it pushes `agentdev-lib/X.Y`
  with a `plume-works-renovate` app token and stops. A second workflow runs on
  that tag. It builds one wheel, publishes it to PyPI through trusted
  publishing, and creates a GitHub Release with the same wheel. A tag name never
  matches `v*`, which starts `primary-checks.yml`.
- **Image.** The image build stages every plugin in the marketplace and the
  OpenCode bridge. It builds a wheel of `agentdev-lib` from its own source and
  sets `UV_FIND_LINKS` to the wheel directory, so the bundled wheel wins over
  PyPI. It runs `uv sync` in each staged plugin before the catalog becomes
  read-only, because `uv run` cannot create `.venv/` in a read-only plugin.
  ADR-0081 rejects one `UV_PROJECT_ENVIRONMENT` for the whole container. Task 1
  proves this design before any other task starts.
- **The split.** `.agents/plugins/agentdev-iwe/` gets the 12 `iwe-*` skills, the
  8 `iwe-*` agents, and their tests. The marketplace publishes it. The skill
  names keep their `iwe-` prefix. Every `/agentdev:iwe-*` reference becomes
  `/agentdev-iwe:iwe-*`. `durable-knowledge-audit` and
  `durable-knowledge-auditor` stay in `agentdev`.
- **OpenCode.** The bridge moves to `.agents/opencode-bridge/`. It reads
  `.claude-plugin/marketplace.json` and loads every plugin that the marketplace
  lists. OpenCode runs only in the image, where every plugin is installed. The
  OpenCode install path for use outside the image is removed.
- **Installs.** `.claude/startup.py`, the image, and the plugin README install
  or enable every plugin that the marketplace publishes.

## Implementation Steps

### Task 1: Spike — staged plugins run read-only with a bundled wheel

**Files:** none committed. Results go to `## Verification results`.

Run this before every other task. In a scratch tree under `/tmp`, copy the
current `.claude-plugin/` and `.agents/plugins/agentdev/`. Add the plugin
`pyproject.toml` and an `agentdev-lib` wheel that Approach describes. Change one
skill script to import from `agentdev_lib`. Run `uv sync` in the plugin with
`UV_FIND_LINKS` set, then make the tree root-owned and read-only, as
`ansible/roles/agent_catalog/tasks/stage_catalog.yml` does. If a checkbox fails,
stop and take the result to `/agentdev:iwe-plan` as a revision.

- [x] The changed script runs from the read-only staged plugin as a non-root
  user, and prints its normal result.
- [x] A copy of the staged plugin, made as `claude plugin install` makes it in
  `~/.claude/plugins/cache/`, runs the same script.
- [x] The size of the staged `.venv/` (`du -sh`) is recorded in
  `## Verification results`.
- [x] The size of the image layer that the staged `.venv/` adds is recorded in
  `## Verification results`.

### Task 2: Create the agentdev-lib package

**Files:** Create: `py_packages/agentdev_lib/` (with `tests/`). Modify:
`pyproject.toml`. Move: `.agents/plugins/agentdev/tests/test_result_codes.py`,
`.agents/plugins/agentdev/tests/test_skill_common.py`, and
`.agents/plugins/agentdev/tests/test_git_default_branch.py` to
`py_packages/agentdev_lib/tests/`.

- [x] `py_packages/agentdev_lib/` builds with `uv build` into a wheel named
  `agentdev_lib-<version>-py3-none-any.whl` that contains `result_codes`,
  `skill_common`, and `git_default_branch`.
- [x] The tests of the three modules run from `py_packages/agentdev_lib/tests/`
  and pass.

### Task 3: Run the agentdev scripts through uv

**Files:** Create: `.agents/plugins/agentdev/pyproject.toml`. Modify:
`pyproject.toml`, `.gitignore`, every `.agents/plugins/agentdev/bin/*.py`
executable, every `.agents/plugins/agentdev/skills/*/agent-code/*.py`, the tests
under `.agents/plugins/agentdev/tests/` that run them,
`py_packages/agentdev_lib/tests/test_result_codes.py`,
`py_packages/agentdev_lib/agentdev_lib/result_codes.py`, and
`.agents/plugins/agentdev/skills/skill-scripts/SKILL.md`. Delete:
`.agents/plugins/agentdev/bin/result_codes.py`,
`.agents/plugins/agentdev/bin/skill_common.py`,
`.agents/plugins/agentdev/bin/git_default_branch.py`.

- [x] No script under `.agents/plugins/agentdev/bin/` or
  `.agents/plugins/agentdev/skills/*/agent-code/` inserts into `sys.path`.
- [x] Each script under `.agents/plugins/agentdev/bin/` and
  `.agents/plugins/agentdev/skills/*/agent-code/` starts with
  `#!/usr/bin/env -S uv run --quiet`.
- [ ] A plugin script that SIGTERM ends while it runs through its shebang prints
  `RESULT=SIGNAL_TERM` last and exits 143.
- [ ] `uv run pytest .agents/plugins/agentdev/tests` passes.
- [ ] `git status` shows no `.venv/` or `uv.lock` under `.agents/plugins/` after
  the tests run.

### Task 4: Keep the plugin pins in step with the package version

**Files:** Create: `scripts/sync-agentdev-lib-pins.py`,
`scripts/tests/test_sync_agentdev_lib_pins.py`. Modify:
`.pre-commit-config.yaml`.

- [ ] In a fixture tree, the hook rewrites a plugin pin that differs from the
  package version and exits non-zero, as a formatter hook does.
- [ ] In a fixture tree whose pins match, the hook changes nothing and exits 0.

### Task 5: Fail a pull request that changes agentdev-lib without a new version

**Files:** Create: `scripts/check-agentdev-lib-version.py`,
`scripts/tests/test_check_agentdev_lib_version.py`. Modify:
`.github/workflows/primary-checks.yml`.

- [ ] In a fixture repository, a commit that changes `py_packages/agentdev_lib/`
  after the latest `agentdev-lib/*` tag and keeps the version makes the check
  exit 1.
- [ ] In the same fixture, a commit that also changes the version makes the
  check exit 0.
- [ ] A pull request job in `.github/workflows/primary-checks.yml` runs the
  check.

### Task 6: Tag a new agentdev-lib version on main

**Files:** Create: `.github/workflows/tag-agentdev-lib.yml`.

- [ ] The workflow runs on a push to `main` and pushes the tag
  `agentdev-lib/<version>`, with `<version>` read from
  `py_packages/agentdev_lib/pyproject.toml`.
- [ ] A step skips the push when the tag `agentdev-lib/<version>` already
  exists.
- [ ] The push uses a token from `actions/create-github-app-token`
  (`RENOVATE_APP_CLIENT_ID`, `RENOVATE_APP_PRIVATE_KEY`,
  `permission-contents: write`).
- [ ] A comment of at most 3 lines at the push step gives the reason for the app
  token.

### Task 7: Release agentdev-lib from its tag

**Files:** Create: `.github/workflows/release-agentdev-lib.yml`.

- [ ] The workflow runs on a pushed `agentdev-lib/*` tag and builds one wheel
  with `uv build`.
- [ ] A step publishes that wheel with `pypa/gh-action-pypi-publish` through
  trusted publishing (`id-token: write`, no stored token).
- [ ] A step creates a GitHub Release for the tag with that wheel attached.

### Task 8: Set up the PyPI project

**Closed by:** the maintainer.

- [ ] The name `agentdev-lib` is free on PyPI, or the plan is revised with
  another name.
- [ ] The PyPI project trusts `.github/workflows/release-agentdev-lib.yml` of
  this repository as its publisher.

### Task 9: Stage and install every plugin in the image

**Files:** Modify: `ansible/roles/agent_catalog/defaults/main.yml`,
`ansible/roles/agent_catalog/tasks/stage_catalog.yml`,
`ansible/roles/agent_catalog/tasks/install_catalog.yml`,
`ansible/roles/agent_catalog/README.md`.

- [ ] Staging copies every plugin that the marketplace publishes.
- [ ] The `agent_catalog_plugin_version` pin checks the version of `agentdev`.
- [ ] The Claude install step installs every staged plugin at user scope.

### Task 10: Bundle agentdev-lib in the image

**Files:** Modify: `docker/base/agentdev-base.Dockerfile`,
`ansible/roles/agent_catalog/tasks/stage_catalog.yml`,
`ansible/roles/agent_catalog/README.md`.

- [ ] Staging builds the `agentdev-lib` wheel from `py_packages/agentdev_lib/`.
- [ ] The image sets `UV_FIND_LINKS` to the directory of that wheel.
- [ ] Staging runs `uv sync` in each staged plugin before the step "Make the
  staged catalog root-owned and read-only".

### Task 11: Move the IWE workflow into agentdev-iwe

**Files:** Create: `.agents/plugins/agentdev-iwe/`
(`.claude-plugin/plugin.json`, `pyproject.toml`, `README.md`, `tests/`). Modify:
`.claude-plugin/marketplace.json`,
`.agents/plugins/agentdev/.claude-plugin/plugin.json`,
`docker/base/agentdev-base.Dockerfile`, `pyproject.toml`. Move: the 12
`skills/iwe-*`, the 8 `agents/iwe-*.agent.md`, and their tests and fixtures.

- [ ] `.claude-plugin/marketplace.json` publishes `agentdev-iwe` at `1.0.0`.
- [ ] `agentdev` is at `6.0.0` in `.claude-plugin/marketplace.json`, in its
  `plugin.json`, and in the `AGENTDEV_PLUGIN_VERSION` default of the base
  Dockerfile.
- [ ] `uv run pytest .agents/plugins/agentdev-iwe/tests` passes.
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.

### Task 12: Point every reference to a moved file at its new path

**Files:** Modify: the support links in `docs/knowledge/`,
`scripts/link-knowledge-support.py`, `scripts/check-anchors.py`,
`.pre-commit-config.yaml`, `.prettierignore`, `.github/renovate.json`,
`.github/workflows/validate-knowledge-base.yml`,
`docs/knowledge/tests/test_banned_frontmatter_keys.py`,
`docs/knowledge/tests/test_plan_release_schema.py`,
`docs/knowledge/tests/test_rank_and_base_schemas.py`, and the anchors in
`docs/knowledge/data/backlog/exercise-removed-delta-blocks.md`,
`docs/knowledge/data/backlog/implement-opens-pr.md`,
`docs/knowledge/data/backlog/incremental-re-verify.md`,
`docs/knowledge/data/backlog/migrate-earlier-iwe-scaffold.md`,
`docs/knowledge/data/backlog/observe-adversarial-review-depth-on-opencode.md`,
`docs/knowledge/data/backlog/observe-planned-adversarial-review.md`,
`docs/knowledge/data/backlog/pr-merge-post-merge-cleanup.md`,
`docs/knowledge/data/backlog/verification-command-fix-is-tactical.md`, and the
`## Key references` of this plan.

- [ ] Each support link in `docs/knowledge/` resolves into
  `.agents/plugins/agentdev-iwe/skills/iwe-bootstrap/assets/`.
- [ ] `uv run pre-commit run link-knowledge-support --all-files` passes.
- [ ] `scripts/check-anchors.py` scans the skills and agents of every plugin
  under `.agents/plugins/`.
- [ ] `uv run scripts/check-anchors.py` exits 0.
- [ ] `uv run pytest docs/knowledge/tests` passes.
- [ ] `git grep -n "plugins/agentdev/skills/iwe-" -- .pre-commit-config.yaml .prettierignore .github/renovate.json .github/workflows/validate-knowledge-base.yml scripts/link-knowledge-support.py`
  prints nothing.

### Task 13: Name the IWE skills and agents by their new namespace

**Files:** Modify: the files under `.agents/plugins/` and `AGENTS.md` that name
`agentdev:iwe-`, and `docs/knowledge/data/backlog/implement-opens-pr.md`,
`docs/knowledge/data/backlog/migrate-earlier-iwe-scaffold.md`,
`docs/knowledge/data/backlog/observe-adversarial-review-depth-on-opencode.md`,
`docs/knowledge/data/backlog/observe-planned-adversarial-review.md`,
`docs/knowledge/data/someday/rename-plan-document.md`,
`docs/knowledge/data/plans/20261115-decisions-in-git-history.md`. The accepted
ADRs keep their text.

- [ ] `git grep -n "agentdev:iwe-" -- .agents/plugins AGENTS.md docs/knowledge/data/backlog/implement-opens-pr.md docs/knowledge/data/backlog/migrate-earlier-iwe-scaffold.md docs/knowledge/data/backlog/observe-adversarial-review-depth-on-opencode.md docs/knowledge/data/backlog/observe-planned-adversarial-review.md docs/knowledge/data/someday/rename-plan-document.md docs/knowledge/data/plans/20261115-decisions-in-git-history.md`
  prints nothing.

### Task 14: Move the OpenCode bridge out of agentdev

**Files:** Move: `.agents/plugins/agentdev/.opencode-plugin/` to
`.agents/opencode-bridge/`, `.agents/plugins/agentdev/tests/opencode/` to
`.agents/opencode-bridge/tests/`. Modify:
`py_packages/agentdev_runtime/agentdev_runtime/catalog.py`,
`py_packages/agentdev_runtime/tests/test_opencode_config.py`,
`.github/workflows/validate-agent-files.yml`, and the tests under
`scripts/tests/` that name the bridge path.

- [ ] The bridge reads `.claude-plugin/marketplace.json` and registers
  `<plugin>:<skill>` commands for each plugin it lists.
- [ ] The skill tool strips the namespace prefix of each plugin.
- [ ] `bun test ./.agents/opencode-bridge/tests` passes.
- [ ] `uv run pytest py_packages/agentdev_runtime/tests/test_opencode_config.py`
  passes.

### Task 15: Install every plugin in a cloud session

**Files:** Modify: `.claude/startup.py`, `scripts/tests/test_cloud_startup.py`,
`.claude/settings.json`.

- [ ] `.claude/startup.py::register_plugin` installs each plugin that
  `.claude-plugin/marketplace.json` publishes.
- [ ] `.claude/settings.json#permissions.allow` allows the scripts of every
  plugin, in the checkout and in the plugin cache.

### Task 16: Document the plugins, uv, and the script contract

**Files:** Modify: `.agents/plugins/agentdev/README.md`, `.agents/AGENTS.md`,
`.agents/plugins/agentdev/skills/skill-scripts/SKILL.md`, `README.md`.

- [ ] `.agents/plugins/agentdev/README.md#installing-in-claude-code` enables
  `agentdev-iwe@agent-devcontainer` as a separate choice.
- [ ] `.agents/plugins/agentdev/README.md#what-it-expects` requires `uv`.
- [ ] `.agents/plugins/agentdev/README.md#installing-in-opencode` describes only
  the image.
- [ ] `.agents/AGENTS.md#catalog-locations-and-portability` states the uv script
  rule and names `agentdev-lib` instead of the standard-library rule.
- [ ] `.agents/plugins/agentdev/skills/skill-scripts/SKILL.md#implementation`
  imports `result_codes` from `agentdev_lib`.

### Task 17: Observe the first agentdev-lib release

**Closed by:** the first merge to `main` after Task 8.

- [ ] `.github/workflows/tag-agentdev-lib.yml` pushed `agentdev-lib/<version>`.
- [ ] `.github/workflows/release-agentdev-lib.yml` published the version to
  PyPI.
- [ ] The GitHub Release for the tag has the wheel attached.
- [ ] The next push to `main` that keeps the version pushes no tag.

### Task 18: Observe both plugins in a built image and outside it

**Closed by:** the maintainer, in a container from the image that CI builds
after the merge, and in a Claude Code session outside the image.

- [ ] In the image, a Claude Code session lists `/agentdev-iwe:iwe-plan`.
- [ ] In the image, `/agentdev-iwe:iwe-branch-name` in a Claude Code session
  runs its script.
- [ ] In the image, an OpenCode session lists `agentdev-iwe:iwe-plan`.
- [ ] In the image, `agentdev-iwe:iwe-branch-name` in an OpenCode session runs
  its script.
- [ ] Outside the image, with both plugins enabled, the first run of a skill
  script downloads `agentdev-lib` from PyPI and succeeds.

## Acceptance

### Scenario: A script in the checkout runs the local agentdev-lib

- **WHEN** a script of a plugin runs in this checkout
- **THEN** it imports `agentdev_lib` from `py_packages/agentdev_lib/`, and an
  edit there applies with no reinstall
- **Test:**
  `py_packages/agentdev_lib/tests/test_checkout_source.py::test_plugin_script_imports_checkout_package`

### Scenario: A signal ends a script that runs through uv

- **WHEN** SIGTERM ends a plugin script that runs through its
  `#!/usr/bin/env -S uv run --quiet` shebang
- **THEN** the script prints `RESULT=SIGNAL_TERM` last, and its caller sees exit
  status 143, not a signal death
- **Test:**
  `py_packages/agentdev_lib/tests/test_result_codes.py::test_sigterm_through_a_uv_shebang_exits_143`

### Scenario: The pin hook rewrites a stale pin

- **WHEN** a plugin pins an `agentdev-lib` version that differs from the version
  in `py_packages/agentdev_lib/pyproject.toml`
- **THEN** the pre-commit hook writes the package version into the pin and exits
  non-zero
- **Test:**
  `scripts/tests/test_sync_agentdev_lib_pins.py::test_stale_pin_is_rewritten`

### Scenario: A change to agentdev-lib without a new version fails

- **WHEN** a pull request changes `py_packages/agentdev_lib/` after the latest
  `agentdev-lib/*` tag and keeps its version
- **THEN** the version check exits 1
- **Test:**
  `scripts/tests/test_check_agentdev_lib_version.py::test_change_without_bump_fails`

### Scenario: A new version is released

- **WHEN** a push to `main` carries an `agentdev-lib` version with no tag
- **THEN** the tag `agentdev-lib/<version>` is pushed, the version is on PyPI,
  and a GitHub Release for the tag holds the same wheel
- **Checked at ship:** `.github/workflows/tag-agentdev-lib.yml` and
  `.github/workflows/release-agentdev-lib.yml`

### Scenario: The image runs the bundled agentdev-lib read-only

- **WHEN** a script of a staged plugin runs in the image
- **THEN** it imports the `agentdev-lib` built from the image's source, and
  writes nothing in the read-only catalog
- **Checked at ship:** `ansible/roles/agent_catalog/tasks/stage_catalog.yml` and
  `## Verification results` of this plan

### Scenario: A consumer installs agentdev without the IWE workflow

- **WHEN** a user enables only `agentdev@agent-devcontainer`
- **THEN** no `iwe-*` skill or agent is installed
- **Checked at ship:** `.claude-plugin/marketplace.json` and the `skills/` and
  `agents/` of `.agents/plugins/agentdev/`

### Scenario: OpenCode loads every plugin

- **WHEN** the bridge starts in a catalog whose marketplace lists `agentdev` and
  `agentdev-iwe`
- **THEN** it registers `agentdev:<skill>` and `agentdev-iwe:<skill>` commands,
  and the skill tool loads a skill named with either prefix
- **Test:**
  `.agents/opencode-bridge/tests/bridge.test.ts::registers every marketplace plugin`

### Scenario: A cloud session installs every plugin

- **WHEN** `.claude/startup.py setup` runs in a cloud session
- **THEN** it installs each plugin that the marketplace publishes
- **Test:**
  `scripts/tests/test_cloud_startup.py::test_setup_installs_every_marketplace_plugin`

## ADRs

[The catalog is split into opt-in plugins, and the IWE workflow is its own
plugin](../adr/0104-catalog-split-into-opt-in-plugins.md)

[Catalog scripts run through uv and share code through a published
package](../adr/0105-catalog-scripts-run-through-uv-with-a-published-package.md)

## Depends on

None.

## Verification

- `uv run pytest py_packages/agentdev_lib/tests`
- `uv run pytest .agents/plugins/agentdev/tests .agents/plugins/agentdev-iwe/tests`
- `uv run pytest scripts/tests/test_sync_agentdev_lib_pins.py scripts/tests/test_check_agentdev_lib_version.py scripts/tests/test_cloud_startup.py`
- `uv run pytest py_packages/agentdev_runtime/tests/test_opencode_config.py`
- `bun test ./.agents/opencode-bridge/tests`
- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `uv run scripts/check-anchors.py`
- `uv run pytest docs/knowledge/tests`
- `git grep -n "agentdev:iwe-" -- .agents/plugins AGENTS.md docs/knowledge/data/backlog/implement-opens-pr.md docs/knowledge/data/backlog/migrate-earlier-iwe-scaffold.md docs/knowledge/data/backlog/observe-adversarial-review-depth-on-opencode.md docs/knowledge/data/backlog/observe-planned-adversarial-review.md docs/knowledge/data/someday/rename-plan-document.md docs/knowledge/data/plans/20261115-decisions-in-git-history.md`
  prints nothing.
- `git grep -n "sys.path.insert" -- '.agents/plugins/*/bin/*.py' '.agents/plugins/*/skills/*/agent-code/*.py'`
  prints nothing.

## Verification results

Task 1 spike, with uv 0.13.8, a copy of `agentdev` 5.0.0, and
`iwe-branch-name.py` importing `git_default_branch` and `result_codes` from an
`agentdev_lib` wheel:

- `uv run` finds the plugin's project from the script's own path, not from the
  working directory, so a script run from inside another uv project still uses
  the plugin's `.venv/`.
- From the root-owned, read-only staged plugin, a non-root user runs the script
  and gets its normal result. uv cannot take the environment lock there and
  warns; `--quiet` hides the warning. Nothing in the staged tree changes.
- The copy that `claude plugin install` makes in `~/.claude/plugins/cache/` has
  no `.venv/bin/python`. The first `uv run` there repairs the `.venv/` and runs
  the script, so the cache copy must be writable by the session user.
- The staged `.venv/` is 120K (`du -sh`) and adds a 147kB image layer.
- `uv.lock` records the `UV_FIND_LINKS` directory as the registry of
  `agentdev-lib`, so that directory must stay in the image.

## Out of scope

- Dropping the `iwe-` prefix from the skill and agent names.
- `bin/macos-bootstrap.zsh` and the native macOS install.
- OpenCode outside the image.
- Further splits of `agentdev`.

## Key references

- `.claude-plugin/marketplace.json#plugins` — the plugins that the marketplace
  publishes.
- `.agents/plugins/agentdev/.claude-plugin/plugin.json#version` — the `agentdev`
  version.
- `py_packages/agentdev_lib/agentdev_lib/result_codes.py::emit_result` — a
  module that moves to `agentdev-lib`.
- `py_packages/agentdev_lib/agentdev_lib/skill_common.py::Stop` — a module that
  moves to `agentdev-lib`.
- `py_packages/agentdev_lib/agentdev_lib/git_default_branch.py::is_default_branch`
  — a module that moves to `agentdev-lib`.
- `.agents/plugins/agentdev/tests/conftest.py::plugin_root` — the plugin root
  that the tests resolve scripts from.
- `.agents/plugins/agentdev/tests/conftest.py::installed_iwe_bootstrap` — a
  fixture that copies `bin/` into a plugin layout.
- `pyproject.toml#tool.uv.sources` — the root sources that point at the
  checkout.
- `pyproject.toml#tool.pytest.ini_options.testpaths` — the test roots.
- `.agents/plugins/agentdev/.opencode-plugin/index.ts::readCatalog` — reads one
  plugin root and takes the namespace from its `plugin.json`.
- `.agents/plugins/agentdev/.opencode-plugin/index.ts::bridge` — the v1 entry
  and its prefix strip.
- `.agents/plugins/agentdev/.opencode-plugin/index.ts::setupBridge` — the v2
  entry and its prefix strip.
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py::opencode` —
  registers the bridge path in `opencode.json`.
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py::claude` — installs
  every plugin that a marketplace publishes.
- `ansible/roles/agent_catalog/defaults/main.yml#agent_catalog_trees` — the
  trees that staging copies.
- `ansible/roles/agent_catalog/tasks/stage_catalog.yml` › "Fail when the
  manifest does not publish exactly one matching plugin" — the one-plugin check.
- `ansible/roles/agent_catalog/tasks/stage_catalog.yml` › "Make the staged
  catalog root-owned and read-only" — the step that `uv sync` runs before.
- `ansible/roles/agent_catalog/tasks/install_catalog.yml` › "Install the plugin
  for Claude at user scope" — the one-plugin install.
- `docker/base/agentdev-base.Dockerfile` › "ARG AGENTDEV_PLUGIN_VERSION" — the
  version pin that staging checks.
- `.claude/startup.py::register_plugin` — installs only `agentdev` in a cloud
  session.
- `.claude/settings.json#permissions.allow` — the script permissions.
- `.github/workflows/validate-agent-files.yml` › "bun test
  ./.agents/plugins/agentdev/tests/opencode" — the bridge test run.
- `.github/workflows/renovate.yml` › "permission-contents: write" — the app
  token pattern that Task 6 follows.
- `.agents/AGENTS.md#catalog-locations-and-portability` — the standard-library
  rule that goes.
- `.agents/plugins/agentdev/skills/skill-scripts/SKILL.md#implementation` — the
  script contract.
- `py_packages/agentdev_lib/agentdev_lib/result_codes.py::_report_signal` —
  re-raises a terminating signal; behind `uv run` the caller sees 128 + its
  number.
- `scripts/link-knowledge-support.py` › "SCAFFOLD = Path(" — the scaffold path
  that the support links follow.
- `scripts/check-anchors.py` › "SCAN_GLOBS = (" — the catalog paths that the
  anchor check scans.
- `docs/knowledge/data/adr/0081-venv-link-to-the-home-volume.md` — rejects one
  `UV_PROJECT_ENVIRONMENT` for the whole container.
