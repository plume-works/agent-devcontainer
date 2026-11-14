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
