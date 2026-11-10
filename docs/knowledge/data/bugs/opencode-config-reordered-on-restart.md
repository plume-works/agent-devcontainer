---
type: bug
description: The OpenCode policy step moved the permission key to the end of opencode.json on every start, so the first restart of a runtime with an unchanged catalog rewrote the file in a new key order.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
- resource: scripts/tests/test_agent_runtime_acceptance.py
- resource: https://github.com/plume-works/agent-devcontainer/actions/runs/41245073592
stage: done
severity: low
---

# Bug: OpenCode's config is reordered on the first restart

## Symptom

[Catalog lifecycle](../../../../openspec/specs/catalog-lifecycle/spec.md)
promises that a container restart with an unchanged catalog leaves every
client's configuration file byte-identical. In `agentdev-deploy`,
`~/.config/opencode/opencode.json` changed between the first start and the first
restart: the `plugin` and `mcp` keys moved ahead of `permission`. Later restarts
kept the new order.

## Reproduction

Start an `agentdev-deploy` runtime on a fresh home volume and wait for `ready`,
then restart the container and wait for `ready` again. Compare
`~/.config/opencode/opencode.json` before and after the restart; the bytes
differ. `test_restarts_leave_the_opencode_config_byte_identical` in
`scripts/tests/test_agent_runtime_acceptance.py` does exactly this.

## Root cause

On the first start the policy step writes `$schema` and `permission`, then the
catalog step appends `plugin` and the CBM install adds `mcp`. On every later
start `apply_policy` rebuilt the document as `$schema`, every unmanaged key,
then `permission`, so `permission` moved behind `plugin` and `mcp`. The values
were unchanged; only the key order moved.

## Fix

`apply_policy` keeps every existing key where it is and only replaces the values
of `$schema` and `permission`. It adds `$schema` first and `permission` last
only when they are missing. `test_a_configured_file_keeps_its_key_order` in
`py_packages/agentdev_runtime/tests/test_opencode_config.py` checks that
configuring an already-configured file leaves it byte-identical.

## Key references

- `py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py::apply_policy`
  — `apply_policy`;
  `py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py::apply_policy`
  — the order-preserving rebuild
- `py_packages/agentdev_runtime/tests/test_opencode_config.py::test_a_configured_file_keeps_its_key_order`
  — `test_a_configured_file_keeps_its_key_order`
- `scripts/tests/test_agent_runtime_acceptance.py::test_restarts_leave_the_opencode_config_byte_identical`
  — `test_restarts_leave_the_opencode_config_byte_identical`
- `docs/knowledge/data/spec/catalog-lifecycle.md#scenario-the-container-restarts-with-an-unchanged-catalog › "every client's configuration file is byte-identical"`
  — the unchanged-catalog restart scenario
