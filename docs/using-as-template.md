# Using this repository as a template

This is a manual guide for projects that want the development environment and repository
conventions supplied by `agent-devcontainer`. It covers both starting from a complete copy
and adding the template surface to an existing repository. It does not introduce a
generator, synchronization service, or new capability that this repository does not
already carry.

Read `docs/repository-structure.md` first. It is the authoritative keep/customize/optional/
delete inventory.

## What the finished project receives

The default setup retains all runtime capabilities provided by the current devcontainer:

- the digest-pinned `agent-desktop` image;
- Docker-in-Docker and Codespaces SSH;
- worktree-safe workspace mounts;
- Xpra/VirtualGL desktop access;
- the Docker Desktop MCP gateway and secrets socket integration;
- persistent state volumes: one shared volume holding both agents' credentials, with the
  rest of each agent's state scoped per devcontainer instance;
- the `agentdev` catalog staged in the image and installed after volume mounts;
- Codex devcontainer policy configuration;
- keyring and GitHub authentication support;
- uv environment caching and pre-commit setup; and
- an opt-in egress firewall with a project-owned allowlist.

The setup targets any project, but it only supplies the tools and conventions already
present here. It does not infer a language, create application code, choose dependencies,
or invent CI for the consuming project's product.

## Workflow A: start from a full repository copy

Use this workflow with GitHub's “Use this template” operation, a normal clone copied into a
new repository, or any equivalent complete checkout.

### 1. Establish the new repository identity

Before pruning files, record:

- the new repository name and owner;
- its default branch;
- whether it will publish a custom development image; and
- whether agent authentication/configuration should remain shared with other local projects.

The supplied configuration uses the literal Docker volume `agentdev-agents-auth`, mounted at
`/root/.agents-auth` with one subdirectory per agent. Keeping it shares Claude Code's and
Codex's credentials only — nothing else — across this project, its worktrees, and other
projects using the same volume name. That is the default behavior supplied here. The rest
of each agent's state — plugins, marketplaces, sessions, `~/.claude.json`,
`~/.codex`'s logs and sqlite state — lives in the `agentdev-claude` and `agentdev-codex`
mounts, which Compose scopes per devcontainer instance because that state records absolute
workspace paths that differ between worktrees.

Replace the publisher-oriented `README.md` sections with the consuming project's purpose,
setup, tests, and ownership. Remove image/catalog publishing instructions that the project
does not retain. Update the project identity in `pyproject.toml` as well. Keep the existing
`LICENSE` notice unless the project deliberately chooses another compatible licensing
arrangement.

### 2. Delete publisher-only source

Delete these paths from the copied repository:

```text
.agents/
.claude-plugin/
py_packages/
scripts/validate-super-linter-tool-versions.sh
docs/agents/specs/
```

`scripts/` holds nothing else, so it disappears with its one file; delete the empty
directory rather than leaving it behind. The same applies to the `py_packages/` wrapper and
its standalone `LICENSE` once `validate_agent_files` is gone.

The catalog is not lost. The published image stages it at `/opt/agentdev`, and the retained
post-create scripts install it through the Claude and Codex plugin CLIs. The validator
source is also unnecessary: the image installs `validate_agent_files` at
`/usr/local/bin/validate_agent_files`, so the command works in the devcontainer with no
`uv run` prefix. Confirm it with `command -v validate_agent_files`.

Do not delete `.claude/` or `.codex/`; those are project-facing configuration. Do not delete
the root `AGENTS.md` or `CLAUDE.md`; publisher-only instructions were split into the source
trees removed above.

### 3. Choose whether to retain custom-image publishing

For the normal consumer path, delete the optional bundle:

```text
ansible/
docker/
.dockerignore
.github/actions/docker/
.github/workflows/ci.yml
.github/workflows/delete-old-containers.yml
```

Then remove the `ci` job that calls `.github/workflows/ci.yml` from
`.github/workflows/primary-checks.yml`, and remove image/catalog publisher paths from
`.github/actions/paths-filter/action.yml`.

If the project needs image customization, retain those paths for reference and complete
the additional steps in [Optional custom-image setup](#optional-custom-image-setup). Do not
assume the retained publisher build works after the catalog source was deleted.

### 4. Adapt the uv project

The post-create lifecycle runs `.devcontainer/scripts/uv-sync.sh` unconditionally, so keep a
valid root `pyproject.toml` even when the application itself is not Python. It can remain a
development-tool project.

In `pyproject.toml`:

1. replace the publisher project name, version, and description;
2. remove `validate_agent_files` from the development dependency list;
3. remove the editable `validate_agent_files` entry from `[tool.uv.sources]`, and delete the
   now-empty `[tool.uv.sources]` table;
4. remove `toml`, `pydantic`, and `python-frontmatter` — they exist for the validator
   package, not for the development environment;
5. remove `.agents/plugins/agentdev/tests` and `py_packages` from pytest `testpaths`. If
   that empties the list, delete the whole `[tool.pytest.ini_options]` table rather than
   leaving `testpaths = []`, which makes a bare `pytest` collect nothing;
6. remove `ansible` and `ansible-lint` when the optional image bundle is not retained; and
7. add only the dependencies and test paths the consuming project actually owns.

Regenerate `uv.lock` after those edits, then run `uv sync --all-groups --all-extras`.

Do not add the deleted local package back merely to make it importable from this repository.

### 5. Adapt pre-commit and lint configuration

Review `.pre-commit-config.yaml` hook by hook:

1. keep the general whitespace, Prettier, clang-format, ruff, ShellCheck, Gitleaks,
   Actionlint, and Zizmor hooks that match the project;
2. remove the Ansible hook when the optional image bundle is absent, and the clang-format
   and Hadolint hooks when the project has no C/C++ and no Dockerfile;
3. remove publisher-only catalog path patterns;
4. when agent-file validation is retained, invoke the image-provided `validate_agent_files`
   command rather than the deleted local package — change the hook's
   `entry: uv run validate_agent_files` to `entry: validate_agent_files`, keeping
   `language: system`. The hook then requires the development image, like the `zizmor` hook
   below;
5. the `zizmor` hook is `language: system` and expects `zizmor` on `PATH`, which holds
   inside the development image and not on a bare host. A project that does not run
   Super-Linter should point the hook at the pinned `zizmorcore/zizmor-pre-commit`
   repository instead, so `pre-commit run --all-files` works anywhere; and
6. update file selectors for the consuming project's source layout.

In `.ruff.toml`, remove `validate_agent_files` and `mock_catalog` from
`known-first-party`, then add the consuming project's own first-party packages. Leaving the
publisher names in place is not cosmetic: the project's own modules get sorted as
third-party imports, and the isort pass silently enforces the wrong grouping.

Set `target-version` to the project's real floor. The supplied value is `py312`, which is
this repository's floor rather than a default.

Review the Ansible patterns in `.prettierignore` if the optional bundle was deleted, and add
any directory holding verbatim third-party captures — a formatter must not rewrite content
whose whole point is that it matches an upstream byte for byte.

The remaining lint configuration is still template content even when a particular language
is not yet present; unused file selectors simply match nothing.

### 6. Review the devcontainer configuration

Keep the complete `.devcontainer/` tree, `compose.pins.yml`, and `.mcp.json`. Then review
these project-owned values:

1. Change `name` in `.devcontainer/devcontainer.json`.
2. Keep `workspaceFolder`, `DEV_WORKSPACE_FOLDER`, and the Compose workspace mount aligned.
   They currently derive the folder name automatically and normally need no edit.
3. Replace `python.testing.pytestArgs`, which currently names `py_packages`, with the
   consuming project's test roots or remove it when the project has no Python tests.
4. Remove Ansible-specific editor settings and extensions only when the project does not
   want the supplied optional tooling visible. Keeping them does not enable image building.
5. Review the extension list and chat terminal auto-approval settings for the project's
   trust model.
6. Review `.devcontainer/firewall-allowlist.txt`. Leave `ENABLE_FIREWALL=false` until the
   allowlist contains every destination the project needs, then opt in deliberately.
7. Keep the `14500-14599` forwarded range when retaining Xpra.
8. Keep `compose.pins.yml` in the `dockerComposeFile` list; it is the actual digest pin.
9. Rewrite publisher-specific comments in `compose.pins.yml` when the consumer no longer
   builds `agent-desktop` itself; keep the pinned image reference and Renovate discovery
   behavior intact.

The lifecycle scripts are not optional fragments:

- post-create depends on `uv-sync.sh` and both plugin installers;
- post-start depends on pre-commit, keyring, firewall, Xpra, and Codex configuration; and
- `devcontainer-init.sh` supplies the environment consumed by Compose.

### 7. Review agent configuration

Retain `.claude/` and `.codex/`, then review them as project policy:

- `.claude/settings.json` is strict JSON. Review allowed paths, Bash commands, web domains,
  MCP tools, and enabled official plugins. Remove the workspace-source permission for
  `.agents/plugins/agentdev/skills/*/scripts/*` after deleting `.agents/`; keep the
  installed-plugin cache permission when those scripts should remain callable.
- `.claude/settings.local.json` remains ignored for machine-specific permissions.
- Rewrite `.claude/README.md` so it no longer links to the deleted catalog publisher tree.
- `.codex/setup-codex-cloud.sh` is useful only for Codex Cloud hosts that need GitHub CLI;
  retaining it is harmless elsewhere.
- Rewrite `.codex/README.md` to describe the consumer project without links to deleted
  publisher manifests.
- Root `CLAUDE.md` continues to include root `AGENTS.md`.

The project does not need to declare `agentdev` in `.claude/settings.json` merely to use the
devcontainer. The image-staged installation is handled by `postCreateCommand`. The retained
post-start installers look for a workspace marketplace and exit successfully when the
consumer has none.

### 8. Adapt GitHub Actions and Renovate

The `.github/` tree is a starting point, not a copy-and-run contract.

#### Primary checks and reformatting

In `.github/workflows/primary-checks.yml`, keep the reformat call and remove the `ci` job
unless the optional image bundle is retained. That job is the only consumer of the
`clean_build` `workflow_dispatch` input, so remove the input with it.

In `.github/actions/paths-filter/action.yml`, the built-in filter is named `image` and lists
the publisher's build inputs. Delete the `ansible/**`, `docker/**`, `scripts/**`,
`.agents/plugins/**`, `.claude-plugin/**`, and `py_packages/validate_agent_files/**`
entries; keep `.devcontainer/**` and `.github/actions/**` so the retained workflows still
trigger.

In `.github/workflows/reformat.yml`:

1. remove catalog, validator-source, Ansible, and excluded tool-version paths that no longer
   exist;
2. remove the `scripts/validate-super-linter-tool-versions.sh` step;
3. replace the two `./.agents/plugins/agentdev/bin/super-linter-env.sh` calls; and
4. update formatter path filters for the consuming project.

Step 3 is the only one with real work in it. Both steps write the Super-Linter environment
into `$GITHUB_ENV`, and the helper is nothing but a sequence of `NAME=value` lines — one set
for the autofix pass, one for the check pass, differing in the `FIX_*` values and in four
`VALIDATE_*` flags for linters that cannot autofix. Inline those two blocks into the
workflow as heredocs and drop `VALIDATE_ANSIBLE` and `ANSIBLE_DIRECTORY` if the optional
bundle is gone. Nothing else in the workflow depends on the catalog.

The current workflow references publisher files under `.agents/` and `scripts/`; it will
fail if copied and pruned without these edits.

#### Agent-file validation

Retain agent-file validation only for agent files the consuming repository owns. Adapt
`.github/workflows/validate-agent-files.yml` so validator-dependent jobs execute through the
digest-pinned `agent-desktop` image: give the job a `container.image` carrying the same
tag-plus-digest as `compose.pins.yml`, never the moving `edge` tag. Remove:

- tests for `py_packages/validate_agent_files/tests`;
- tests for `.agents/plugins/agentdev/tests`;
- the `--require-marketplace claude codex` argument, which asserts publisher manifests a
  consumer does not have; and
- path filters for deleted catalog/package source.

What remains is a job that needs no Python setup at all, because the image already carries
the validator:

```yaml
jobs:
  validate-agent-files:
    runs-on: ubuntu-latest
    container:
      # Same tag-plus-digest as compose.pins.yml. Never the moving `edge` tag.
      image: ghcr.io/plume-works/agent-desktop:edge@sha256:<digest>
      credentials:
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    steps:
      - uses: actions/checkout@v7.0.1
        with:
          persist-credentials: false
      - run: validate_agent_files --ci .
```

`--ci` prints nothing when everything passes and the full report when anything fails, so a
green run stays quiet in the log. Add `--verbose` if the report is wanted either way.

Keep the digest in step with `compose.pins.yml` so CI and the devcontainer validate with the
same version — Renovate already bumps that file.

A project that ships no skills or agents of its own should delete the workflow and the
`validate-agent-files` pre-commit hook outright.

#### Renovate

Retain `.github/renovate.json`, but review every rule:

1. keep Docker dependency management for `compose.pins.yml` so the development image does
   not become stale;
2. remove the image-publisher self-build/automerge explanation when the project consumes
   rather than publishes the image;
3. remove the publisher-only Super-Linter synchronization rule if its excluded script and
   release process are not retained; and
4. update organization, repository, and branch assumptions.

The catalog needs no Renovate rule of its own: the devcontainer reinstalls the bundled
catalog on start, so its version follows the image pin rather than a separate one.

### 9. Verify the copied project

Run these checks from the new repository:

1. Parse the effective Compose configuration:

   ```bash
   docker compose \
     -f .devcontainer/docker-compose.yml \
     -f compose.pins.yml \
     config
   ```

2. Sync the retained development-tool project:

   ```bash
   uv sync --all-groups --all-extras
   ```

3. Run the retained pre-commit hooks against the tree:

   ```bash
   uv run pre-commit run --all-files
   ```

4. Generate the host-specific Compose environment and check the derived workspace name:

   ```bash
   ./.devcontainer/devcontainer-init.sh && cat .devcontainer/.env
   ```

5. Create or rebuild the devcontainer and confirm the post-create and post-start commands
   finish successfully.
6. Confirm Claude and Codex list `agentdev@agent-devcontainer` after starting new sessions.
7. When agent files are present, run the image-provided validator against their actual
   locations.
8. Enable the firewall only after checking the project allowlist, then rebuild/restart and
   verify required network destinations still work.
9. Open the forwarded Xpra port and confirm the desktop starts.
10. Run the adapted GitHub workflows on a branch before making them required checks.

## Workflow B: add the template to an existing repository

This workflow avoids copying publisher source in the first place.

### 1. Copy the runtime unit

Copy all of these paths, preserving executable bits:

```text
.devcontainer/
compose.pins.yml
.mcp.json
```

Do not copy only the two visible devcontainer configuration files. The lifecycle hooks,
feature lock, allowlist, Compose environment setup, and plugin installers are direct
dependencies.

Then adapt the project-owned values from [step 6 of Workflow A](#6-review-the-devcontainer-configuration),
and add these to the existing `.gitignore` before the first container start:

```text
.devcontainer/.env
.devcontainer/local.env
```

`devcontainer-init.sh` generates the first file on every start. Without the ignore rules it
lands in the next commit, carrying the host's absolute paths with it.

### 2. Merge agent-facing configuration

Copy or merge:

```text
AGENTS.md
CLAUDE.md
.claude/
.codex/
```

When the existing repository already has agent instructions or settings, merge the rules
semantically rather than overwriting them. Keep `CLAUDE.md` as an include of the resulting
root `AGENTS.md` unless the project deliberately maintains separate Claude instructions.

### 3. Merge the tooling baseline

Selectively copy and merge:

```text
pyproject.toml
uv.lock
.pre-commit-config.yaml
.ruff.toml
.clang-format
.ansible-lint.yml
.hadolint.yaml
.shellcheckrc
.markdownlint.yml
.prettierrc.yml
.prettierignore
zizmor.yaml
.editorconfig
.gitignore
```

Do not overwrite an existing project manifest, lockfile, ignore file, or lint configuration.
Transfer the supplied dependencies, hooks, and rules that the project wants, then regenerate
the lockfile. Preserve a valid root uv project because the supplied post-create hook runs
`uv sync`.

Two collisions are worth naming, because both fail silently:

- **`.ruff.toml` outranks `pyproject.toml`.** Ruff reads the first configuration it finds and
  stops. Dropping this file into a repository that configures ruff under `[tool.ruff]`
  disables that block entirely — line length, `target-version`, selected rules, and all — with
  no warning. Merge the two into `.ruff.toml` and delete the `[tool.ruff]` tables, or keep
  the project's `pyproject.toml` configuration and do not copy this file. Confirm which one
  won with `ruff check --show-settings <path> | head -3`, which prints the resolved settings
  path.
- **Copy only the linter configuration that has a matching hook, and vice versa.** A
  `.clang-format` with no C++ is inert, but a clang-format hook with no `.clang-format` is a
  failing hook. The same holds for Ansible and Hadolint.

Where the project vendors verbatim third-party files, exclude them in `.prettierignore` and
in ruff's `extend-exclude` before running the hooks for the first time. Adopting the
formatters rewrites everything they can reach, including snapshots whose value is that they
are unmodified.

### 4. Merge GitHub configuration

Copy or merge the pull request template, Renovate configuration, reusable actions, and the
workflow starting points described in the repository-structure inventory. Apply the same
manual CI edits from Workflow A; selecting fewer files does not remove their internal
publisher assumptions.

### 5. Verify

Run the same verification sequence from Workflow A. Pay particular attention to merged
mounts, lifecycle command keys, GitHub workflow permissions, and duplicate pre-commit hooks.

## Optional custom-image setup

Only follow this section when the published `agent-desktop` image does not meet the
project's needs.

Retain or copy:

```text
ansible/
docker/
.dockerignore
.github/actions/docker/
.github/workflows/ci.yml
.github/workflows/delete-old-containers.yml
```

Also retain the image job in `primary-checks.yml` and the corresponding image paths in the
shared filter action.

Before running the build, inspect `docker/desktop/agent-desktop.Dockerfile`. Its current
Ansible invocation reads publisher source from the repository build context twice: it
enables `agentic_tools_stage_catalog` for `.agents/` and `.claude-plugin/`, and
`install_validate_agent_files` for `py_packages/validate_agent_files/`. After the normal
publisher-source deletion, none of those trees exist and the build fails with an explicit
message from each role. Choose explicitly whether to:

- retain those publisher trees and continue building the complete image;
- alter the retained build so it stages no local catalog and builds no validator — set
  `agentic_tools_stage_catalog=false` and `install_validate_agent_files=false`, and drop the
  `AGENTDEV_PLUGIN_VERSION` and `VALIDATE_AGENT_FILES_VERSION` pins and labels with them; or
- construct a derivative from the published `agent-desktop` image, which already carries
  both.

Only the first option is implemented by this repository today. Treat the other options as
project-owned image work and update the CI path filters, image names, GHCR permissions,
digest update flow, and cleanup workflow to match it.

Do not publish under `plume-works` names from a consuming repository. Update image names and
metadata to the new repository owner, then pin the resulting consumer image in
`compose.pins.yml`.

## Ongoing maintenance

Manual copying creates no upstream relationship. After bootstrap:

- Renovate advances external image and tool pins configured in the consumer;
- fixes to the reusable scaffolding do not automatically arrive from this repository;
- catalog updates arrive through a rebuilt/pinned `agent-desktop` image; and
- project-specific changes remain owned by the consuming repository.

Compare template files manually when adopting a later improvement. Reconsider a real
template synchronization mechanism only if the number of consumers or the scaffolding churn
makes manual review unreliable.
