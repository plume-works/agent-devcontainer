---
type: spec
description: Devcontainer OpenCode sessions allow every action and every external directory, configured in the user's OpenCode config on every start by a runtime command that needs nothing from the consumer project.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/pyproject.toml
- resource: scripts/tests/test_configure_opencode.py
---

# Devcontainer OpenCode policy

## Purpose

Defines the OpenCode action and filesystem permission policy inside the
devcontainer, which is itself the isolation boundary.

## Requirements

### Requirement: devcontainer OpenCode runs with unrestricted filesystem access

On every container start, `agentdev-runtime lifecycle ready` SHALL, through
`agentdev-runtime state agent-policy`, set `$schema` to
`https://opencode.ai/config.json`, `permission["*"]` to `"allow"`,
`permission.external_directory["/**"]` to `"allow"`, and
`experimental.subagent_depth` to `5` in the OpenCode `opencode.json` resolved
from `OPENCODE_CONFIG_DIR`, `XDG_CONFIG_HOME`, or the user's default config
directory. It SHALL patch `opencode.jsonc` when that file exists and
`opencode.json` otherwise, SHALL parse either as JSONC and reject duplicate
keys, and SHALL write the result as strict JSON, replacing the file atomically
through a temporary file in the same directory. It SHALL keep every existing
top-level key in its position, replacing only the managed keys' values, and
SHALL add `$schema` first and `permission` and `experimental` last only when
missing. The config directory SHALL have mode `0700` and the file SHALL have
mode `0600`. The step SHALL run after the supervised services are ready and
after the git credential helper setup, so a failure fails the start hook without
keeping those services from starting.

#### Scenario: a container starts with no OpenCode config

- **WHEN** the container starts and `opencode.json` does not exist
- **THEN** it is created with the schema, both permission rules, and the nesting
  depth at mode `0600`.

#### Scenario: the config carries catalog and user settings

- **WHEN** `opencode.json` contains a plugin list, unrelated top-level keys,
  additional permission rules, or other `experimental` keys
- **THEN** those values survive and the managed values are set.

#### Scenario: the container restarts with a configured config

- **WHEN** the container starts again and `opencode.json` is unchanged since the
  configure step last wrote it
- **THEN** the configure step leaves it byte-identical.

#### Scenario: the config directory contains JSON and JSONC

- **WHEN** `opencode.jsonc` contains comments or trailing commas and exists
  alongside `opencode.json`
- **THEN** the configure step patches the higher-precedence JSONC config,
  preserves its setting values, and leaves `opencode.json` unchanged.

#### Scenario: a session changed the policy

- **WHEN** any managed value holds a different value
- **THEN** the next container start restores the approved value.

#### Scenario: the config repeats a key

- **WHEN** the selected config declares the same key twice
- **THEN** the configure step fails and leaves the file unchanged.

#### Scenario: a JSONC config carries comments

- **WHEN** the configure step patches an `opencode.jsonc` that holds comments
- **THEN** the setting values survive and the file is rewritten as strict JSON
  without the comments.

#### Scenario: the config is malformed

- **WHEN** the existing `opencode.json` is not valid JSON
- **THEN** the configure step fails and leaves the file unchanged.

### Requirement: the OpenCode configure step is consumer-independent

`agentdev-runtime state agent-policy` SHALL take its pinned JSONC parser
dependency from the `agentdev_runtime` package installed in the image, without
depending on the consumer workspace's Python project or installed packages.

#### Scenario: a consumer repository has no Python project

- **WHEN** the devcontainer starts for a repository without `pyproject.toml`
- **THEN** the OpenCode policy is still configured.

## Rationale

### OpenCode runs with full access, patched into its own config on every start

The devcontainer is the isolation boundary, so OpenCode runs inside it without
action or external-directory prompts. The policy is merged into the user's
config on every start, replacing only the managed values, and is parsed with a
pinned `json5` that `agentdev_runtime` carries itself, so template consumers add
no Python dependency. Normalizing JSONC to strict JSON keeps every setting value
and gives up comments and formatting.

Rejected:

- **Replacing the whole config with the managed object.** It would remove the
  catalog bridge and the user's own settings.
- **Patching only `opencode.json`.** An existing `opencode.jsonc` takes
  precedence and could override the policy.
- **Parsing JSONC or editing its text locally.** Comments, trailing commas,
  strings, and duplicate keys need a maintained parser.
- **Folding the policy into catalog reinstallation.** Catalog registration runs
  on create and attach and only when a bridge plugin exists, while the policy
  must be restored on every start.

### The policy keeps OpenCode v1's `permission` form

OpenCode v1 ignores v2's `permissions` key, while v2 reads v1's `permission`
object, so one `permission` block grants full access under either major. This
holds as long as v2 never rewrites `opencode.json` into its own form.

Rejected:

- **Rewriting the policy into v2's `permissions` form.** A v1 install would lose
  full access.
