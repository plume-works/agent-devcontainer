---
type: spec
description: Devcontainer Codex sessions run with no sandbox and no approval prompts, configured in config.toml on every start by a runtime command that needs nothing from the consumer project.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T20:55:00Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/codex_config.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/pyproject.toml
- resource: scripts/tests/test_configure_codex.py
---

# Devcontainer Codex policy

## Purpose

Defines the Codex sandbox and approval policy inside the devcontainer, which is
itself the isolation boundary. Decision and constraints: Codex full access in
the devcontainer.

## Requirements

### Requirement: devcontainer Codex runs without sandbox or approval prompts

On every container start, `agentdev-runtime lifecycle ready` SHALL set the
top-level keys, through `agentdev-runtime state agent-policy`,
`sandbox_mode = "danger-full-access"` and `approval_policy = "never"` in
`${CODEX_HOME:-~/.codex}/config.toml`, leaving the Codex home at mode `0700` and
the file at mode `0600`.

#### Scenario: a container starts with no Codex config

- **WHEN** the container starts and `config.toml` does not exist
- **THEN** `config.toml` exists with both keys set, at mode `0600`

#### Scenario: the config carries other tools' sections

- **WHEN** `config.toml` holds codebase-memory-mcp's marker-delimited sections
- **THEN** every other key, table, and comment survives unchanged

#### Scenario: a session changed the policy

- **WHEN** `sandbox_mode` or `approval_policy` holds a different value
- **THEN** the next container start restores the managed values

### Requirement: the configure step needs nothing from the consumer project

`agentdev-runtime state agent-policy` SHALL take its dependencies from the
`agentdev_runtime` package installed in the image, independent of the workspace
`pyproject.toml`.

#### Scenario: a consumer repository without tomlkit

- **WHEN** a template consumer's `pyproject.toml` does not list `tomlkit`
- **THEN** the container start still configures Codex
