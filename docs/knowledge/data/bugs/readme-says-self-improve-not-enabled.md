---
type: bug
description: README.md says that nothing this repository ships enables the self-improve plugin, but the create phase installs and enables each plugin of the catalog, self-improve too.
stage: pending
severity: low
sources:
- resource: README.md
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: .claude-plugin/marketplace.json
---

# Bug: The README says that the containers do not enable self-improve

## Symptom

`README.md#self-improve` says that the plugin is "**not enabled** by anything
this repository ships" and that the Ansible catalog role stages only `agentdev`.
Each container enables `self-improve`, so a reader who trusts the README does
not know that its hooks run.

## Reproduction

1. Read `.claude-plugin/marketplace.json#plugins`: it lists `agentdev` and
   `self-improve`.
2. Read `py_packages/agentdev_runtime/agentdev_runtime/catalog.py::claude`: it
   runs `claude plugin install` for each plugin in that list.
3. Read `README.md#self-improve`: it says that nothing in this repository
   enables the plugin.

## Root cause

`.claude-plugin/marketplace.json#plugins` publishes `agentdev` and
`self-improve`.
`py_packages/agentdev_runtime/agentdev_runtime/catalog.py::claude` installs each
plugin that the manifest publishes, and
`py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::created` and
`py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::attached` call it
at user scope. The README text was not changed when the runtime started to
install the full catalog.

## Potential solution

Change `README.md#self-improve` to say that each container enables the plugin.
[ADR-0088](../adr/0088-self-improve-lives-in-this-repository.md) records the
current behaviour as a consequence.
