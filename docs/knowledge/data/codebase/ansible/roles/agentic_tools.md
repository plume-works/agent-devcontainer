---
type: codebase
description: Installs Claude Code, Codex, and the MCP inspector, optionally cc-filter, and stages and installs the agentdev catalog into the image.
source: ansible/roles/agentic_tools
source_digest: sha256:11d32a9ac0500f6cef83fca14f5752d10dbef8594658b73c15d68b3f47ced7dc
verified:
  by: claude-code/opus-5.5
  at: 2026-09-26T00:00:00Z
stale_after: 2026-12-25
generated:
  by: claude-code/opus-5.5
  at: 2026-09-26T00:00:00Z
sources:
- id: code
  resource: ansible/roles/agentic_tools
---

# agentic_tools role

The role behind `install_agentic_tools`: the agent CLIs through Bun, an optional
checksummed `cc-filter` binary, and the catalog staging that lets a container
install `agentdev` with no clone and no network.

## Public surface

- `agentic_tools_claude_code_version`, `agentic_tools_codex_version`,
  `agentic_tools_inspector_version`, and the `agentic_tools_bun_packages` list
  they feed — `ansible/roles/agentic_tools/defaults/main.yml:5-17`
- `agentic_tools_stage_catalog`, `agentic_tools_install_catalog`,
  `agentic_tools_catalog_source_dir`, `agentic_tools_plugin_version`,
  `agentic_tools_catalog_root` —
  `ansible/roles/agentic_tools/defaults/main.yml:43-71`
- `agentic_tools_cc_filter_*` — `defaults/main.yml:21-38`, off by default; the
  version is a `# renovate:` pin whose checksums
  `scripts/refresh-pin-checksums.py` recomputes
- The staged tree at `agentic_tools_catalog_root` (`/opt/agentdev`), holding
  `.claude-plugin/` and `.agents/` copied whole (`defaults/main.yml:76-78`)

## How it works

`tasks/main.yml` reads the installed global package set from
`bun pm ls --global` and installs each pinned `package@version` that is missing,
so a version bump reinstalls where a guard on the binary's existence would skip.
It then includes `cc_filter.yml`, `stage_catalog.yml`, and `install_catalog.yml`
behind their booleans. Staging reads the Claude marketplace manifest, fails
unless it publishes exactly one `agentdev` plugin, fails when the Claude and
Codex plugin manifests disagree on `version`, fails when a non-empty
`agentic_tools_plugin_version` differs from the staged version, copies the two
trees, prunes `__pycache__`, `.pytest_cache`, `.ruff_cache`, and `.tmp`, and
makes the result root-owned and read-only. Installing registers the staged root
as a marketplace for Claude (user scope) and Codex and installs the plugin for
both, so a raw-image consumer resolves `agentdev:*` skills without lifecycle
hooks.

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

Verified anchor points (line numbers as of 2026-09-21):

- `ansible/roles/agentic_tools/tasks/main.yml:5` — installed-globals probe
- `ansible/roles/agentic_tools/tasks/main.yml:23` — pinned Bun global installs
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:28` — exactly one plugin
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:55` — Claude/Codex
  version agreement
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:68` — pinned version
  check
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:123` — root-owned,
  read-only
- `ansible/roles/agentic_tools/tasks/install_catalog.yml:27-81` — marketplace
  registration and plugin install for both agents
