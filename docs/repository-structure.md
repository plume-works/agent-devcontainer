# Repository structure

This repository has three responsibilities:

1. publish the `agent-desktop` development image;
2. publish the `agentdev` catalog for Claude Code and Codex; and
3. carry reusable repository scaffolding for projects that consume the image.

Those responsibilities share one checkout but have different distribution mechanisms. The
image is consumed from GHCR, the catalog is installed from the copy staged in that image,
and repository scaffolding is copied manually. This document is the persistent inventory of
that boundary. The spike under `docs/agents/specs/` is a historical decision record, not the
current template manifest.

## Classification

Every tracked surface belongs to one of these classes:

| Class     | Meaning                                                                     |
| --------- | --------------------------------------------------------------------------- |
| Template  | Retain for a normal project consuming `agent-desktop`.                      |
| Customize | Retain as a starting point, then edit project identity or owned paths.      |
| Optional  | Retain only when building a customized image.                               |
| Publisher | Required to publish this repository's image/catalog/package, not to use it. |
| Generated | Host, container, test, or tool state; never template source.                |

“Template” and “customize” describe manual reuse. This repository does not currently ship a
Copier template, generator, or synchronization tool.

## Runtime flow

```text
ansible/ + docker/ + catalog publisher source
                    |
                    v
        ghcr.io/plume-works/agent-desktop
                    |
                    | digest pin in compose.pins.yml
                    v
 .devcontainer/devcontainer.json + docker-compose.yml
                    |
          postCreateCommand (once)
                    |
     install staged agentdev catalog into the
     persistent Claude and Codex state volumes
                    |
           postStartCommand (each start)
                    |
 pre-commit, keyring, firewall, Xpra, Codex policy,
 and a workspace catalog override when one exists
```

The image contains the environment and a read-only catalog staged at `/opt/agentdev`. It
does not contain the repository scaffolding. A consuming project therefore needs the
template files below even though it does not need the catalog publisher source.

## Default template surface

### Devcontainer runtime

The default devcontainer surface is the complete tracked `.devcontainer/` directory plus
two root companions:

| Path                                                 | Responsibility                                                                                                   |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `.devcontainer/devcontainer.json`                    | Dev Container entry point, features, mounts, ports, editor configuration, and lifecycle commands.                |
| `.devcontainer/docker-compose.yml`                   | Devcontainer service, MCP gateway, worktree mounts, and persistent Claude/Codex volumes.                         |
| `.devcontainer/devcontainer-init.sh`                 | Generates host-specific Compose state and creates shared agent volumes before startup.                           |
| `.devcontainer/devcontainer-lock.json`               | Locks the Docker-in-Docker and SSH feature digests.                                                              |
| `.devcontainer/firewall-allowlist.txt`               | Project-owned allowlist read when the opt-in firewall starts.                                                    |
| `.devcontainer/scripts/postCreateCommand.sh`         | Sets up persistent Claude and Codex auth state, syncs the uv environment, and installs the image-staged catalog. |
| `.devcontainer/scripts/postStartCommand.sh`          | Starts repository hooks, keyring, firewall, Xpra, Codex policy, and workspace catalog override.                  |
| `.devcontainer/scripts/uv-sync.sh`                   | Runs `uv sync` and links the cached environment to `.venv`.                                                      |
| `.devcontainer/scripts/setup-pre-commit.sh`          | Trusts the checkout and installs pre-commit and pre-push hooks.                                                  |
| `.devcontainer/scripts/setup-keyring.sh`             | Starts and persists the headless keyring used by authenticated tooling.                                          |
| `.devcontainer/scripts/firewall.sh`                  | Activates the image-provided egress firewall when enabled.                                                       |
| `.devcontainer/scripts/configure-codex.py`           | Sets devcontainer-only Codex sandbox and approval policy.                                                        |
| `.devcontainer/scripts/link-codex-auth.sh`           | Persists Codex's `auth.json` in the shared `agentdev-agents-auth` volume and symlinks it into place.             |
| `.devcontainer/scripts/reinstall-agentdev-claude.sh` | Installs the staged Claude plugin and overrides it with a workspace marketplace when present.                    |
| `.devcontainer/scripts/reinstall-agentdev-codex.sh`  | Performs the equivalent Codex marketplace/plugin installation.                                                   |
| `compose.pins.yml`                                   | Supplies the Renovate-managed tag-plus-digest image override referenced by `devcontainer.json`.                  |
| `.mcp.json`                                          | Points repository agents at the MCP gateway sidecar.                                                             |

These files are one runtime unit. Copying only `devcontainer.json` and
`docker-compose.yml` leaves direct references unresolved.

The default runtime intentionally retains all capabilities currently supplied here:

- Docker-in-Docker;
- Xpra and VirtualGL desktop access;
- the Docker Desktop MCP gateway and secret socket integration;
- shared Claude and Codex authentication/configuration volumes;
- image-staged `agentdev` installation;
- the opt-in egress firewall; and
- Codespaces SSH and worktree-safe mounts.

### Agent-facing repository configuration

| Path        | Disposition | Notes                                                                                    |
| ----------- | ----------- | ---------------------------------------------------------------------------------------- |
| `AGENTS.md` | Template    | Reusable safety, workflow, language, testing, and spike guidance.                        |
| `CLAUDE.md` | Template    | Includes the root `AGENTS.md` for Claude Code.                                           |
| `.claude/`  | Customize   | Shared Claude permissions, official plugins, local ignore rules, and explanatory README. |
| `.codex/`   | Customize   | Codex Cloud bootstrap and explanation of where the shared catalog lives.                 |

Publisher-only instructions are scoped below `.agents/`, `.claude-plugin/`, `ansible/`,
and `py_packages/validate_agent_files/`. Deleting those sources also deletes their local
maintenance contract; the reusable root instructions remain.

### Project tooling

The following files are template starting points. They express the development conventions
supplied by this repository, but several contain publisher-owned package names or paths and
must be reviewed in a copied project.

| Path                                 | Purpose and required review                                                                                                                                |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pyproject.toml`                     | uv-managed developer environment. Remove the local validator source and publisher test paths; rename the project and add the consumer's dependencies.      |
| `uv.lock`                            | Recreate after editing `pyproject.toml`.                                                                                                                   |
| `.pre-commit-config.yaml`            | Shared formatter/linter hooks. Remove optional-source hooks that do not match the consumer and invoke the image-provided validator directly when retained. |
| `.ruff.toml`                         | Python lint/format policy. Remove publisher-only first-party module names.                                                                                 |
| `.clang-format`                      | C/C++ formatting policy.                                                                                                                                   |
| `.ansible-lint.yml`                  | Ansible lint policy; useful with the optional image bundle and requiring comment/path review without it.                                                   |
| `.hadolint.yaml`                     | Dockerfile lint policy.                                                                                                                                    |
| `.shellcheckrc`                      | Shell lint policy.                                                                                                                                         |
| `.markdownlint.yml`                  | Markdown lint policy.                                                                                                                                      |
| `.prettierrc.yml`, `.prettierignore` | Markdown, JSON, YAML, and related formatting policy.                                                                                                       |
| `zizmor.yaml`                        | GitHub Actions security lint policy.                                                                                                                       |
| `.editorconfig`                      | Cross-editor whitespace and newline conventions.                                                                                                           |
| `.gitignore`                         | Ignores devcontainer, agent, environment, test, and tool state.                                                                                            |

`scripts/validate-super-linter-tool-versions.sh` is deliberately not in this group. It
checks this publisher repository's CI/tool pin synchronization and stays behind.

### GitHub surface

The `.github/` tree is template-related, but it is mixed rather than copy-ready:

| Path                                          | Class     | Current coupling                                                                                                                  |
| --------------------------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `.github/pull_request_template.md`            | Template  | General pull request structure.                                                                                                   |
| `.github/renovate.json`                       | Customize | Contains image-publisher and catalog-release assumptions in addition to the consumer image pin.                                   |
| `.github/workflows/primary-checks.yml`        | Customize | Calls both reformatting and the optional image-building CI workflow.                                                              |
| `.github/workflows/reformat.yml`              | Customize | Calls `super-linter-env.sh` from the catalog and this repository's excluded tool-version check; both must be replaced inline.     |
| `.github/workflows/validate-agent-files.yml`  | Customize | Tests publisher sources and uses local validator packaging; consumers run validator-dependent CI through `agent-desktop` instead. |
| `.github/actions/log-debug-stats/`            | Template  | Reusable GitHub API diagnostic action.                                                                                            |
| `.github/actions/setup-python-venv/`          | Customize | Reusable for uv projects after the consumer lockfile/project metadata is established.                                             |
| `.github/actions/paths-filter/`               | Customize | Its current filters name image and catalog publisher paths.                                                                       |
| `.github/workflows/ci.yml`                    | Optional  | Builds, publishes, merges, and smoke-tests the two container images.                                                              |
| `.github/workflows/delete-old-containers.yml` | Optional  | Deletes old GHCR versions for repositories that publish custom images.                                                            |
| `.github/actions/docker/`                     | Optional  | Composite actions used by the image publishing workflow.                                                                          |

The existing workflows are evidence of the supplied CI design; they are not claimed to run
unchanged after publisher source is removed.

### Repository presentation

`README.md`, `LICENSE`, this document, and `docs/using-as-template.md` are template content.
The root README and the READMEs under `.claude/` and `.codex/` must be rewritten to remove
publisher-only descriptions and links. The MIT license and its existing notice remain
unless the project deliberately adopts a compatible alternative.

## Optional custom-image bundle

Keep these paths together only when a project needs to build a customized development image:

- `ansible/`;
- `docker/`;
- `.dockerignore`;
- `.github/workflows/ci.yml`;
- `.github/workflows/delete-old-containers.yml`;
- `.github/actions/docker/`; and
- the matching image paths and job invocation in the shared GitHub files.

This is the source used to publish `agent-desktop`, not a generic derivative-image template.
The current desktop Dockerfile reads publisher-only source from the build context twice: it
sets `agentic_tools_stage_catalog=true` for `.claude-plugin/` plus `.agents/`, and
`install_validate_agent_files=true` for `py_packages/validate_agent_files/`. A full template
copy deletes both, so the optional image bundle cannot build unchanged afterward. A project
retaining the bundle must explicitly choose one of these manual directions:

1. retain the publisher source too and keep building this repository's full image;
2. stop staging a local catalog and stop building the validator — set
   `agentic_tools_stage_catalog=false` and `install_validate_agent_files=false`, and adapt
   the image build accordingly; or
3. create a derivative build based on the published `agent-desktop` image.

The repository currently implements the first direction. The other two are customization
work, not hidden template behavior.

## Publisher-only source

These paths stay in this repository but are deleted from a normal full template copy:

| Path                                             | Responsibility                                                                                               |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `.agents/`                                       | Canonical `agentdev` plugin source: four agents, 24 skills, hooks, helper commands, and plugin-script tests. |
| `.claude-plugin/`                                | Claude marketplace manifest for the catalog.                                                                 |
| `py_packages/validate_agent_files/`              | Standalone validator package source and package tests.                                                       |
| `scripts/validate-super-linter-tool-versions.sh` | Publisher CI consistency check.                                                                              |
| `docs/agents/specs/`                             | Historical spikes and implementation records, including catalog distribution.                                |

After deleting `py_packages/validate_agent_files/`, remove the now-empty `py_packages/`
wrapper and its standalone `LICENSE` as well. `scripts/` holds nothing but the tool-version
check, so it disappears with it.

`validate_agent_files` itself remains available from the `agent-desktop` image, which
installs it at `/usr/local/bin/validate_agent_files` as an isolated `uv` tool
(`ansible/roles/validate_agent_files/`). It can still be used locally or by CI that executes
through the image, with no `uv run` prefix and no copy of the package source.

## Generated and local-only state

The following observed paths are not repository structure and must never be treated as
template input:

- `.devcontainer/.env` — generated by `devcontainer-init.sh`;
- `.devcontainer/local.env` — ignored host-specific overrides;
- `.claude/settings.local.json` — ignored machine-specific Claude permissions;
- `.tmp/` — required scratch root for agents and audits;
- `.venv`, `.cache/`, `.pytest_cache/`, `.coverage`, and tool caches;
- `.ansible/`, `ansible/.ansible/`, and `ansible/ansible.log`; and
- `log/` and Super-Linter output.

## Why this differs from the original spike

The repository history explains the boundary change:

- `c1dce21` extracted a project-agnostic image publisher and described `.devcontainer/` as
  ready to copy.
- `efc55c1` added digest pinning and Renovate.
- `a07718f` moved the Claude catalog into the `agentdev` plugin.
- `d2270b6` packaged the same tree for Codex.
- `6cb9487` moved lifecycle helpers from root `scripts/` into
  `.devcontainer/scripts/`.
- `07e125b` replaced build-time plugin seeding with a staged catalog plus lifecycle
  installation for both agents.

The catalog-distribution spike's four-file estimate predates the final lifecycle layout.
The live dependency chain now makes the complete `.devcontainer/` tree, `compose.pins.yml`,
and related configuration part of the manual template inventory.
