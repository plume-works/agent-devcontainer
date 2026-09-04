---
type: codebase
description: Installs Claude Code, Codex, and the MCP inspector, optionally cc-filter, and stages and installs the agentdev catalog into the image.
source: ansible/roles/agentic_tools
source_digest: sha256:21c366be6379dedb0b62857b2b24368fbb1deb3a5cb964d843c64b97a2e2332f
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
sources:
- id: code
  resource: ansible/roles/agentic_tools
---

# agentic_tools role

The role behind `install_agentic_tools`: the agent CLIs through Bun, an optional
checksummed `cc-filter` binary, and the catalog staging that lets a container
install `agentdev` with no clone and no network.

## Public surface

- `agentic_tools_stage_catalog`, `agentic_tools_install_catalog`,
  `agentic_tools_catalog_source_dir`, `agentic_tools_plugin_version`,
  `agentic_tools_catalog_root` —
  `ansible/roles/agentic_tools/defaults/main.yml:25-58`
- `agentic_tools_cc_filter_*` — `defaults/main.yml:4-24`, off by default
- The staged tree at `agentic_tools_catalog_root` (`/opt/agentdev`), holding
  `.claude-plugin/` and `.agents/` copied whole (`defaults/main.yml:58-63`)

## How it works

`tasks/main.yml` installs the Bun globals, then includes `cc_filter.yml`,
`stage_catalog.yml`, and `install_catalog.yml` behind their booleans. Staging
reads the Claude marketplace manifest, fails unless it publishes exactly one
`agentdev` plugin, fails when the Claude and Codex plugin manifests disagree on
`version`, fails when a non-empty `agentic_tools_plugin_version` differs from
the staged version, copies the two trees, prunes `__pycache__`, `.pytest_cache`,
`.ruff_cache`, and `.tmp`, and makes the result root-owned and read-only.
Installing registers the staged root as a marketplace for Claude (user scope)
and Codex and installs the plugin for both, so a raw-image consumer resolves
`agentdev:*` skills without lifecycle hooks.

## Depends on

`bun_setup` for the global installs; `extra_facts` for `system_arch` and
`user_home`; the [catalog](../../agents/plugins/agentdev.md) sources, reached
through `agentic_tools_catalog_source_dir` (`/provision` in the image build).

## Invariants & gotchas

- The catalog lives outside `$HOME` because `~/.claude` and `~/.codex` are
  mounted as volumes in a devcontainer, which would shadow anything there. The
  build-time install is likewise shadowed by those volumes, so
  [postCreateCommand](../../devcontainer/scripts.md) installs again.
- Bumping the catalog version means bumping four pins together; the version
  check at `stage_catalog.yml:68` is what turns a missed pin into a failed build
  rather than a mislabeled image.
- The `.tmp` prune matters: the repository's scratch directory is at the root of
  the tree being copied.

## Key references

Verified anchor points (line numbers as of 2026-09-04):

- `ansible/roles/agentic_tools/tasks/main.yml:2` — Bun global installs
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:28` — exactly one plugin
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:55` — Claude/Codex
  version agreement
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:68` — pinned version
  check
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:123` — root-owned,
  read-only
- `ansible/roles/agentic_tools/tasks/install_catalog.yml:27-81` — marketplace
  registration and plugin install for both agents
