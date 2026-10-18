---
type: spec
description: Devcontainer OpenCode sessions allow every action and every external directory, configured in the user's OpenCode config on every start by a script that needs nothing from the consumer project.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-18T20:00:00Z
sources:
- resource: .devcontainer/scripts/configure-opencode.py
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: scripts/tests/test_configure_opencode.py
---

# Devcontainer OpenCode policy

## Purpose

Defines the OpenCode action and filesystem permission policy inside the
devcontainer, which is itself the isolation boundary. Decision and constraints:
[OpenCode full access in the
devcontainer](../architecture/opencode-full-access-in-devcontainer.md).

## Requirements

### Requirement: devcontainer OpenCode runs with unrestricted filesystem access

On every container start, `postStartCommand.sh` SHALL set `$schema` to
`https://opencode.ai/config.json`, `permission["*"]` to `"allow"`, and
`permission.external_directory["/**"]` to `"allow"` in the OpenCode
`opencode.json` resolved from `OPENCODE_CONFIG_DIR`, `XDG_CONFIG_HOME`, or the
user's default config directory. The config directory SHALL have mode `0700` and
the file SHALL have mode `0600`.

#### Scenario: a container starts with no OpenCode config

- **WHEN** the container starts and `opencode.json` does not exist
- **THEN** it is created with the schema and both permission rules at mode
  `0600`.

#### Scenario: the config carries catalog and user settings

- **WHEN** `opencode.json` contains a plugin list, unrelated top-level keys, or
  additional permission rules
- **THEN** those values survive and the three managed values are set.

#### Scenario: the config directory contains JSON and JSONC

- **WHEN** `opencode.jsonc` contains comments or trailing commas and exists
  alongside `opencode.json`
- **THEN** the configure step patches the higher-precedence JSONC config,
  preserves its setting values, and leaves `opencode.json` unchanged.

#### Scenario: a session changed the policy

- **WHEN** any managed value holds a different value
- **THEN** the next container start restores the approved value.

#### Scenario: the config is malformed

- **WHEN** the existing `opencode.json` is not valid JSON
- **THEN** the configure step fails and leaves the file unchanged.

### Requirement: the OpenCode configure step is consumer-independent

The configure script SHALL declare its pinned JSONC parser dependency inline
with PEP 723 and run through `uv`, without depending on the consumer workspace's
Python project or installed packages.

#### Scenario: a consumer repository has no Python project

- **WHEN** the devcontainer starts for a repository without `pyproject.toml`
- **THEN** the OpenCode policy is still configured.
