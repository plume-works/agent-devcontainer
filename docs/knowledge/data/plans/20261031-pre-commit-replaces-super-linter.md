---
type: plan
created: 2026-10-31
release:
- features/pre-commit-ci-gate
description: Replace Super-Linter and reformat.yml with a pre-commit job in the digest-pinned devcontainer image, make every hook a uv-locked or image-provisioned tool, scan gitleaks over commit ranges, and remove Super-Linter from the whole repository.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T13:00:00Z
sources:
- resource: .github/workflows/reformat.yml
- resource: .github/workflows/primary-checks.yml
- resource: .pre-commit-config.yaml
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: ansible/roles/dev_tools/tasks/install_pinned_tool.yml
- resource: scripts/refresh-pin-checksums.py
- resource: pyproject.toml
- resource: .github/renovate.json
- resource: https://github.com/gitleaks/gitleaks-action
---

# Replace Super-Linter with pre-commit in CI

## Context

Delivers [pre-commit is the CI gate](../features/pre-commit-ci-gate.md).

[Let pre-commit own formatting](../features/pre-commit-owns-formatting.md) made
the hooks the only local formatting path but left Super-Linter as the CI gate.
Every check Super-Linter makes is also made by a pre-commit hook, so the gate is
a slower, Docker-image-bound duplicate of the hooks. Its image is the version
authority that forces the manual `sync-super-linter-tool-versions` loop and
keeps Renovate from bumping the tools it pins.

Two tools already disagree with themselves: the ruff and ansible-lint hooks
install `v0.15.17` and `v26.4.0` into pre-commit's own venvs while `uv.lock`
holds `0.17.1` and `26.10.1`, which `python_lint_check.py` runs. And the
gitleaks hook, `gitleaks git --pre-commit --staged`, scans an empty diff at
pre-push and would do the same in CI.

## Approach

pre-commit becomes the single lint gate, locally and in CI, and every tool has
one version owner:

- **`uv.lock`** — ruff, ruff-format, ansible-lint, clang-format, and the
  `pre-commit-hooks` fixers, run as `language: system` hooks with
  `entry: uv run <tool>`.
- **`dev_tools_pinned_tools`** — hadolint, shellcheck, gitleaks, actionlint,
  zizmor, and iwe, run as `language: system` binaries, each under a
  `# renovate:` comment.
- **`bunx <package>@<version>`** — prettier and the Renovate config validator,
  unchanged.

No hook names a remote repository, so `pre-commit install-hooks` builds nothing,
and Renovate bumps every tool through its owner.

CI runs a `pre-commit` job in Primary checks inside the same
`agentdev-devcontainer:edge@sha256:…` reference as
`devcontainer-compose-pins.yml`, which the existing "agentdev image digests"
Renovate group already moves. Its steps are checkout, the range selection,
`uv sync --locked`, `pre-commit install-hooks`, and `pre-commit run`, each its
own step so the jobs API records each duration. `ci` keeps `needs:` on it; the
`CI/CD / CI finished` required check is what blocks a merge when it fails.

The job checks the files the event's range changed, and every file when the
range touches a tool-version owner (`uv.lock`, `pyproject.toml`,
`.pre-commit-config.yaml`, `ansible/roles/dev_tools/defaults/main.yml`,
`devcontainer-compose-pins.yml`), so a formatter bump fails at the pull request
that made it.

gitleaks is one hook with three modes, chosen in order: `GITLEAKS_LOG_OPTS` when
set (CI sets it for every event), `--log-opts=FROM..TO` when pre-commit exports
`PRE_COMMIT_FROM_REF`/`PRE_COMMIT_TO_REF` (pre-push), and
`--pre-commit --staged` otherwise (commit). A range scan reads every commit's
patch, so a secret added and removed inside the range is still found.

Rejected: `gitleaks/gitleaks-action`, which needs a licence key for an
organization, lists only the first 30 commits of a pull request, and downloads
its own gitleaks; running the job on the image this pull request builds, which
puts lint behind the full image build; and keeping remote hooks, which leaves a
second copy of each tool beside `uv.lock`.

**Order inside this plan.** The pinned image has no hadolint, and the CI job
runs the pinned image. Task 1 ships first in its own pull request; Tasks 4
onward start only once a Renovate digest bump has moved the pin to an image
containing hadolint and the pinned shellcheck.

**Assumptions.** The range selection is a stdlib Python script with tests,
because the event cases are logic, not wiring. The gitleaks hook's mode switch
stays an inline `bash -c` entry, so the hook remains self-contained in
`.pre-commit-config.yaml` for template consumers. The `pre-commit` job has no
path filter: pre-commit already skips hooks whose files did not change.

## Implementation Steps

### Task 1: Provision hadolint and shellcheck as pinned binaries

**Files:** Modify: `ansible/roles/dev_tools/defaults/main.yml`,
`ansible/roles/dev_tools/tasks/install_pinned_tool.yml`,
`ansible/roles/dev_tools/tasks/main.yml`, `scripts/refresh-pin-checksums.py`,
`scripts/tests/test_refresh_pin_checksums.py`

- [ ] `install_pinned_tool.yml` installs an entry published as a bare binary
  (hadolint's `hadolint-linux-<arch>`) and one whose archive unpacks into a
  directory not named after the asset (shellcheck's `shellcheck-<version>/`),
  and `refresh-pin-checksums.py` renders the same URLs for both, covered by
  tests.
- [ ] `dev_tools_pinned_tools` pins hadolint `v2.14.0` and shellcheck `v0.11.0`
  with per-architecture checksums, and the apt `shellcheck` package is removed
  from `tasks/main.yml`.

### Task 2: Let Renovate bump every pinned binary

**Files:** Modify: `ansible/roles/dev_tools/defaults/main.yml`,
`ansible/AGENTS.md`, `.github/renovate.json`, `.agent.metadata.json`

- [ ] zizmor, gitleaks, actionlint, hadolint, and shellcheck each carry a
  `# renovate: datasource=github-releases depName=<owner/repo>` comment; the
  defaults header and `ansible/AGENTS.md` no longer say any tool moves with a
  Super-Linter sync.
- [ ] `.github/renovate.json` drops the Super-Linter sync rule, the npm regex
  manager also matches the prettier `bunx` pin, no description names
  Super-Linter, and `bunx renovate-config-validator --strict` passes.
- [ ] `.agent.metadata.json`'s `digest_ignore` reasons name Renovate as the only
  mover of hook pins.

### Task 3: Gate on the Task 1 image

**Files:** none

- [ ] The `agentdev-devcontainer` digest in `devcontainer-compose-pins.yml` on
  `main` names an image with `hadolint --version` at `2.14.0` and
  `shellcheck --version` at `0.11.0`.

### Task 4: Lock the Python hook tools in uv

**Files:** Modify: `pyproject.toml`, `uv.lock`

- [ ] The `dev` group lists `clang-format>=21.1.2` and `pre-commit-hooks>=6.0.0`
  beside the existing `ruff` and `ansible-lint`, and `uv lock` records them.

### Task 5: Make every hook native

**Files:** Create: `scripts/tests/test_gitleaks_hook.py`; Modify:
`.pre-commit-config.yaml`

- [ ] Every hook is under `repo: local` with `language: system`: the
  pre-commit-hooks fixers, ruff, ruff-format, ansible-lint, and clang-format
  through `uv run`; hadolint and shellcheck as image binaries; ids, `files`
  patterns, and arguments unchanged; no comment names Super-Linter.
- [ ] The `gitleaks` hook picks `GITLEAKS_LOG_OPTS`, then
  `PRE_COMMIT_FROM_REF..PRE_COMMIT_TO_REF`, then `--pre-commit --staged`, and a
  test drives each mode against a scratch repository holding a secret added and
  removed inside the range.

### Task 6: Bring the tree to the new tool versions

**Files:** Modify: whatever `pre-commit run --all-files` rewrites

- [ ] `uv run pre-commit run --all-files` passes, with its rewrites in their own
  commit.

### Task 7: Run pre-commit in Primary checks

**Files:** Create: `scripts/pre-commit-ci-range.py`,
`scripts/tests/test_pre_commit_ci_range.py`,
`scripts/tests/test_pre_commit_ci_job.py`; Modify:
`.github/workflows/primary-checks.yml`,
`scripts/tests/test_paths_filter_last_pass.py`

- [ ] `pre-commit-ci-range.py` writes `from_ref`, `to_ref`, `all_files`, and
  `gitleaks_log_opts` to `GITHUB_OUTPUT`: base..head for `pull_request` and
  `merge_group`; before..after for `push`; all files and `-1 <sha>` for a zero
  `before`; all files and `--all` for `workflow_dispatch`; all files with the
  range scan when the range touches a tool-version owner. Tests cover each case.
- [ ] Primary checks has a `pre-commit` job in the compose-pin image with
  checkout (`fetch-depth: 0`), the range step, `uv sync --locked`,
  `pre-commit install-hooks`, and `pre-commit run` as separate steps,
  `SKIP=no-commit-to-branch`; `ci` needs it; the `reformat` job is gone.
  `test_pre_commit_ci_job.py` asserts the image equals the compose pin, the step
  order, and the `needs:` edge.

### Task 8: Remove Super-Linter from the publisher

**Files:** Delete: `.github/workflows/reformat.yml`,
`scripts/tests/test_reformat_renovate_skip.py`,
`scripts/validate-super-linter-tool-versions.py`,
`scripts/tests/test_validate_super_linter_tool_versions.py`; Modify:
`.gitignore`, `.claude/settings.json`

- [ ] The files above are gone, `.gitignore` drops `super-linter-output/`,
  `.claude/settings.json` drops the `super_linter.py local` allow rule, and no
  workflow, test, or setting names Super-Linter or `reformat.yml`.

### Task 9: Remove Super-Linter from the catalog

**Files:** Delete: `.agents/plugins/agentdev/skills/local-reformat/`,
`.agents/plugins/agentdev/skills/sync-super-linter-tool-versions/`,
`.agents/plugins/agentdev/bin/super_linter.py`,
`.agents/plugins/agentdev/tests/test_super_linter.py`; Modify:
`.agents/plugins/agentdev/README.md`,
`.agents/plugins/agentdev/bin/python_lint_check.py`,
`.agents/plugins/agentdev/skills/pr-merge/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md`,
`.agents/plugins/agentdev/skills/update-branch/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] The two skills and the module are gone, and the plugin README lists
  neither skill nor Super-Linter as a dependency.
- [ ] `pr-merge` has no Reformat Workflow Synchronization section or step,
  `pr-merge-stack` no reformat-commit case, and `update-branch` no mandatory
  reformat.
- [ ] The template-consume skill and guide name no Super-Linter script, no
  `reformat.yml` edits, and no sync rule; the guide tells a consumer to keep the
  `pre-commit` job and adapt its tool-version owner list.
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  and `uv run pytest .agents/plugins/agentdev/tests` pass.

### Task 10: Reword the repository's own guidance and configs

**Files:** Modify: `AGENTS.md`, `README.md`, `.ruff.toml`, `.markdownlint.yml`,
`.ansible-lint.yml`

- [ ] `AGENTS.md`, `README.md`, `.ruff.toml`, and `.markdownlint.yml` say CI
  runs the pre-commit hooks, and none names Super-Linter.
- [ ] `.ansible-lint.yml` drops the Super-Linter framing, and its `skip_list`
  keeps `syntax-check` only if `uv run ansible-lint` in the devcontainer image
  still cannot resolve the roles' collections.

### Task 11: Record the decision in the knowledge graph

**Files:** Modify: `docs/knowledge/data/architecture/formatter-ownership.md`,
`docs/knowledge/data/architecture/renovate-post-upgrade.md`,
`docs/knowledge/data/architecture/validator-image-install.md`,
`docs/knowledge/data/architecture/template-boundary.md`,
`docs/knowledge/data/architecture/self-improve-consolidation.md`,
`docs/knowledge/data/architecture/catalog-script-language.md`,
`docs/knowledge/data/features/bun-only-javascript-runner.md`,
`docs/knowledge/data/features/renovate-maintains-checksums.md`,
`docs/knowledge/data/someday/host-filesystem-dedup.md`,
`docs/knowledge/data/product.md`

- [ ] `architecture/formatter-ownership` records the per-tool version owners,
  pre-commit as the CI gate, the gitleaks range scan, and the rejected
  alternatives from `## Approach`; the other documents above describe the
  current gate. Shipped plans, `data/log.md`, and closed bugs stay as written.

### Task 12: Refresh the codebase map

**Files:** Modify: the `docs/knowledge/data/codebase/` documents
`stale-map-docs.py` reports

- [ ] `/agentdev:iwe-map` refresh leaves no stale map document.

### Task 13: Green pre-commit job on the pull request

**Files:** none

- [ ] The pull request's Primary checks run shows the `pre-commit` job passing
  with `uv sync`, `pre-commit install-hooks`, and `pre-commit run` as separate
  timed steps, and `CI/CD` starting after it.

## Spec changes

[Template consumption](../spec/template-consumption.md) — the version-check
script no longer exists, so it leaves the publisher-only list:

``` markdown
## MODIFIED Requirements

## Requirement: publisher-only source never survives adoption

A consumer SHALL delete `.agents/`, `.claude-plugin/`, and `py_packages/`, and
SHALL adapt every CI workflow, pre-commit hook, `pyproject.toml` entry, and path
filter that referenced them. Agent-file validation, when retained, SHALL run the
validator the digest-pinned image provides, never the deleted working-tree
package.
```

`spec/pre-commit-gate` — new; the gitleaks scan is security behaviour, so the
contract is spelled out:

``` markdown
## ADDED Requirements

### Requirement: CI runs the pre-commit hooks as the lint gate

Primary checks SHALL run `pre-commit run` inside the `agentdev-devcontainer`
image pinned by the same tag and digest as `devcontainer-compose-pins.yml`,
over the files the event's commit range changed, and the `ci` job SHALL start
only after it succeeds.

#### Scenario: a pull request changes source files

- **WHEN** a pull request changes files a hook matches
- **THEN** the pre-commit job runs those hooks on the files changed between the
  base and head commits, and fails when any hook fails or rewrites a file.

#### Scenario: a push to main

- **WHEN** commits are pushed to `main`
- **THEN** the job checks the files changed between `before` and `after` and
  skips `no-commit-to-branch`.

#### Scenario: a manual run

- **WHEN** Primary checks is started by `workflow_dispatch`
- **THEN** the job checks every file.

### Requirement: a tool-version change is checked against every file

When the commit range changes `uv.lock`, `pyproject.toml`,
`.pre-commit-config.yaml`, `ansible/roles/dev_tools/defaults/main.yml`, or
`devcontainer-compose-pins.yml`, the pre-commit job SHALL run every hook on
every file.

#### Scenario: Renovate bumps ruff

- **WHEN** a pull request moves ruff's version in `uv.lock`
- **THEN** the job runs every hook on every file, and fails if the new version
  would rewrite any of them.

### Requirement: gitleaks scans every commit in a range

The gitleaks hook SHALL scan each commit's patch in the range when one is
given, and the staged change otherwise.

#### Scenario: a secret added and removed inside a pull request

- **WHEN** one commit in a pull request adds a secret and a later commit
  removes it
- **THEN** the pre-commit job fails on the commit that added it.

#### Scenario: a push from a working copy

- **WHEN** `git push` runs the pre-push hooks
- **THEN** gitleaks scans every commit being pushed.

#### Scenario: a commit

- **WHEN** `git commit` runs the pre-commit hooks
- **THEN** gitleaks scans the staged change.

#### Scenario: a push that creates a ref

- **WHEN** a push has an all-zero `before` SHA
- **THEN** the job checks every file and gitleaks scans the pushed commit.
```

## Depends on

[Port the catalog's bundled shell scripts to
Python](20261029-catalog-scripts-python.md) — shipped; Tasks 8 and 9 delete the
Super-Linter module and version check it ported.

## Verification

- `uv run pytest scripts/tests/test_refresh_pin_checksums.py scripts/tests/test_pre_commit_ci_range.py scripts/tests/test_pre_commit_ci_job.py scripts/tests/test_paths_filter_last_pass.py`
- `uv run pytest scripts/tests/test_gitleaks_hook.py` (Task 5).
- `uv run pre-commit run --all-files` in the devcontainer.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  and `uv run pytest .agents/plugins/agentdev/tests`.
- `git grep -n -i -E 'super-?linter|reformat\.yml|local-reformat'` returns only
  shipped plans, `data/log.md`, closed bugs, and released notes.
- `iwe normalize` and `iwe schema validate`.
- The pull request's Primary checks run (Task 13).

## Out of scope

- Running `ci` in parallel with the pre-commit job: [backlog
  task](../backlog/parallel-ci-with-pre-commit.md).
- Caching pre-commit or uv state in a volume or a derived CI image; this plan
  only records the step timings that would justify one.
- Deleting the `REPO_PAT` secret and the `reformat-commit` environment from the
  repository settings, which Task 8 leaves unused; that is an admin change
  outside the repository.
- Adding the pre-commit job to the `main` ruleset; `CI/CD / CI finished` already
  blocks a merge when it fails.
- Hosts outside the devcontainer, where `language: system` hooks need the same
  binaries on `PATH`.
- The overlap with [Remove Codex support](20261031-remove-codex.md): it edits
  `reformat.yml`'s draft-AI-PR override and `local-reformat`'s Codex section,
  both deleted here. No order is imposed; whichever plan lands second skips
  edits to files the other already removed.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `.github/workflows/primary-checks.yml:32` — `reformat` job calling
  `reformat.yml`
- `.github/workflows/primary-checks.yml:54` — `ci` job, `needs: [reformat]`
- `.github/workflows/reformat.yml:209` — `Run Super-Linter autofixes` step
- `.github/workflows/validate-renovate-config.yml:59` — a job running in the
  digest-pinned devcontainer image
- `devcontainer-compose-pins.yml:14` — the `agentdev-devcontainer` pin
- `.pre-commit-config.yaml:2` — `pre-commit/pre-commit-hooks` remote repo
- `.pre-commit-config.yaml:14` — `mirrors-clang-format`
- `.pre-commit-config.yaml:20` — `ansible-lint` remote repo
- `.pre-commit-config.yaml:32` — `hadolint-docker`
- `.pre-commit-config.yaml:38` — `ruff-pre-commit` at `v0.15.17`
- `.pre-commit-config.yaml:47` — `shellcheck-py`
- `.pre-commit-config.yaml:56` — `gitleaks` hook, `--pre-commit --staged`
- `.pre-commit-config.yaml:71` — `prettier` `bunx` pin
- `pyproject.toml:8` — `dev` dependency group
- `ansible/roles/dev_tools/defaults/main.yml:17` — header saying three tools
  move with the Super-Linter sync
- `ansible/roles/dev_tools/defaults/main.yml:19` — `dev_tools_pinned_tools`
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:13` — asset and
  extension resolution
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:41` — `Extract archive`
- `ansible/roles/dev_tools/tasks/main.yml:27` — apt `shellcheck`
- `scripts/refresh-pin-checksums.py:47` — `ToolListPins`
- `scripts/refresh-pin-checksums.py:108` — `PIN_FILES`
- `.github/renovate.json:79` — Super-Linter sync rule
- `.github/renovate.json:148` — npm regex manager for `bunx` pins
- `.agent.metadata.json:15` — `digest_ignore` reasons naming the sync skill
- `scripts/renovate-post-upgrade.sh:45` — post-upgrade `pre-commit run`
- `scripts/tests/test_paths_filter_last_pass.py:117` —
  `test_primary_checks_grants_actions_read_to_the_reusable_workflows`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:85` — Reformat Workflow
  Synchronization
- `.agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md:53` — `reformat.yml`
  commit case
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:125` — "mandatory
  reformat"
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:271`
  — Primary checks and reformatting
- `.agents/plugins/agentdev/README.md:122` — `local-reformat` row
- `AGENTS.md:83` — "Super-Linter runs the same tools in CI"
- `.ansible-lint.yml:19` — Super-Linter collections comment
- `docs/knowledge/data/spec/template-consumption.md:75` — publisher-only source
  requirement
