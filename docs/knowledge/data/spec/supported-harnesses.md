---
type: spec
description: Claude Code and OpenCode are the only agent harnesses the images, runtime, agentdev catalog, and CI support; nothing installs or configures Codex, while validate_agent_files keeps its Codex ecosystem for other repositories.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
- resource: py_packages/validate_agent_files/validate_agent_files/paths.py
- resource: .claude-plugin/marketplace.json
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .github/workflows/validate-agent-files.yml
- resource: ansible/roles/agentic_tools/defaults/main.yml
- resource: .devcontainer/docker-compose.yml
---

# Supported harnesses

## Purpose

The repository supports exactly two agent harnesses: Claude Code and OpenCode.
The `agentdev-base`, `agentdev-devcontainer`, and `agentdev-deploy` images, the
`agentdev_runtime` package, the `agentdev` catalog, and CI install, configure,
and validate those two and no other. A user may still install another harness
inside a container; nothing configures it or registers the catalog for it.

## Requirements

### Requirement: only Claude Code and OpenCode are installed and configured

The images SHALL NOT install the Codex CLI, and the runtime SHALL write no Codex
configuration, hooks, credential links, or `CODEX_HOME`. The devcontainer SHALL
declare no Codex volume, and the repository SHALL have no `.codex/` directory.
Registering a catalog root SHALL register it with Claude Code and OpenCode only.

#### Scenario: a container is created

- **WHEN** the create and attach phases run in an `agentdev-devcontainer`
  container
- **THEN** the catalog is registered as a Claude marketplace and as an OpenCode
  bridge plugin, and no Codex configuration file or `CODEX_HOME` exists.

#### Scenario: a user installs Codex inside a container

- **WHEN** a user installs the Codex CLI by hand and the lifecycle phases run
  again
- **THEN** nothing configures Codex or registers the catalog for it.

### Requirement: the catalog ships a Claude plugin and an OpenCode bridge only

The `agentdev` catalog SHALL publish its plugins through
`.claude-plugin/marketplace.json` and its OpenCode bridge plugin at
`.agents/plugins/agentdev/.opencode-plugin/`, and SHALL ship no
`.codex-plugin/plugin.json`, no `.agents/plugins/marketplace.json`, no per-skill
`agents/openai.yaml`, and no Codex agent installer. A checkout SHALL be a
complete catalog with the Claude manifest and the OpenCode bridge alone.

#### Scenario: a checkout without a Codex marketplace is attached

- **WHEN** a checkout holds `.claude-plugin/marketplace.json` and the OpenCode
  bridge but no `.agents/plugins/marketplace.json`
- **THEN** `agentdev-runtime catalog complete` reports it complete.

### Requirement: CI validates the catalog for Claude only

This repository's agent-file validation SHALL run `validate_agent_files` with
`--require-marketplace claude` and no Codex requirement. The
`validate_agent_files` package SHALL keep its `codex` ecosystem, so it still
validates a repository that publishes `.agents/plugins/marketplace.json` and
`.codex-plugin/plugin.json`.

#### Scenario: CI validates this repository's catalog

- **WHEN** the agent-file validation workflow runs on a pull request
- **THEN** it requires the Claude marketplace and passes without any Codex
  manifest.

## Rationale

### Claude Code and OpenCode are the only supported harnesses

The maintainer chose Claude Code and OpenCode as the only harnesses. The
`chatgpt-codex-connector[bot]` GitHub actor is a third-party reviewer on GitHub,
not a harness running here, so the workflows and tests that recognize it are not
Codex support. `validate_agent_files` is released independently and validates
other repositories' catalogs, so only this repository's own CI call drops
`codex`.

Rejected:

- **Keeping `.codex-plugin/plugin.json` as an untested, install-yourself
  package.** Codex loads catalog agents only through the generated TOML agents
  the agent installer wrote; without that installer none of the agents the
  skills dispatch would load, so the package would ship broken.
