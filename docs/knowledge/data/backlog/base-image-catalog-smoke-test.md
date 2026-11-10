---
type: task
description: Add a CI check that runs agentdev-base with no client-state volumes and no lifecycle commands and asserts that Claude Code and OpenCode resolve the staged catalog.
stage: pending
priority: low
created: 2026-10-29
sources:
- resource: openspec/specs/catalog-lifecycle/spec.md
- resource: docker/base/agentdev-base.Dockerfile
- resource: ansible/roles/agentic_tools/tasks/install_catalog.yml
- resource: scripts/tests/test_agentdev_devcontainer_image.py
rank: 2100
---

# Smoke-test the agentdev-base catalog without lifecycle commands

The [Catalog lifecycle](../../../../openspec/specs/catalog-lifecycle/spec.md)
scenario "the image runs with no volumes and no lifecycle hooks" has no
automated check. Nothing in `scripts/tests/` or `.github/workflows/ci.yml`
starts `agentdev-base` without client-state volumes and asserts that an
`agentdev:*` skill resolves in Claude Code and that OpenCode lists the catalog's
skills.

A consumer that derives from `agentdev-base` without the Dev Container lifecycle
relies on that build-time install. The only catalog check today goes through the
lifecycle of `agentdev-devcontainer`, whose create phase reinstalls the catalog
and so hides a broken build-time install that a base-image consumer would hit.

**Work:** add a check to CI's acceptance that runs the merged `agentdev-base`
candidate with no volumes and no lifecycle command, then checks both clients.

- `docker/base/agentdev-base.Dockerfile` — `agentic_tools_install_catalog=true`
- `ansible/roles/agent_catalog/tasks/install_catalog.yml › "Register the staged catalog as a Claude marketplace at user scope"`
  — Claude marketplace at user scope;
  `ansible/roles/agent_catalog/tasks/install_catalog.yml › "Register the staged OpenCode bridge plugin"`
  — OpenCode bridge registration
- `scripts/tests/test_agentdev_devcontainer_image.py::test_a_direct_consumer_gets_the_managed_runtime_without_lifecycle_scripts`
  — the lifecycle-based catalog check
