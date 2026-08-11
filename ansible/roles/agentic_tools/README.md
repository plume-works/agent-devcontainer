# Agentic Tools Role

Installs the agentic CLI tooling used in the workspace and the security layer
that guards it:

- **Bun-managed globals**: `@modelcontextprotocol/inspector`,
  `@anthropic-ai/claude-code`, and `@openai/codex`.
- **[cc-filter](https://github.com/wissem/cc-filter)**: a hard security layer in
  front of Claude Code hooks. It blocks sensitive file access, blocks risky
  shell/search commands, and redacts secrets. The role downloads the
  architecture-appropriate release binary and wires it into the user's Claude
  Code hooks (`~/.claude/settings.json`).
- **The staged agent catalog** (`agentic_tools_stage_catalog`): a build-time copy
  of the plugin marketplaces both Claude Code and Codex read, so a container
  built from the image can install the catalog with no clone and no network.

Gated by `install_agentic_tools` in the playbook.

## The staged catalog

The role copies the catalog to `agentic_tools_catalog_root` verbatim. Both agents
publish the same plugin from the same tree, each through its own marketplace
manifest, and each manifest resolves the plugin by a path relative to the
marketplace root — so the source layout is preserved rather than rearranged:

```text
$agentic_tools_catalog_root/
  .claude-plugin/marketplace.json     # Claude Code marketplace
  .agents/plugins/marketplace.json    # Codex marketplace
  .agents/plugins/<plugin>/           # the plugin both publish
```

**This role stages; it does not install.** Registering the marketplace and
installing the plugin belong to the container's lifecycle scripts, because
`~/.claude` and `~/.codex` — where both agents keep their marketplace registry,
enablement flags, and plugin cache — are commonly mounted as volumes. Docker
copies image content into a named volume only when that volume is empty, so a
build-time `claude plugin install` would be correct on a clean machine and
silently inert for every container whose volume already exists. A `postCreate`
hook runs after the mounts and has no such problem; this repository's
`.devcontainer/scripts/reinstall-agentdev-{claude,codex}.sh` take the staged root
as their first argument for exactly that.

Two properties are worth knowing before changing any of it:

- **The catalog is staged from the provisioning sources**
  (`agentic_tools_catalog_source_dir`, the build context under Docker), so the
  image and the catalog it carries always come from the same commit. Set
  `agentic_tools_plugin_version` to pin: the Claude marketplace manifest and the
  plugin's Codex manifest must both declare exactly that version or provisioning
  fails.
- **The staged copy is read-only.** It is installed root-owned, directories
  `0755` and files `0644` with existing executables preserved, and lives outside
  `$HOME` so no volume can shadow it. Nothing writes to it at runtime, so
  **updating the staged catalog means rebuilding the image** — a container that
  wants a different catalog registers its own marketplace on top instead.

## Example Usage

```yaml
- name: Install agentic tools
  hosts: all
  become: true
  roles:
    - {
        role: agentic_tools,
        tags: ['agentic_tools'],
        when: install_agentic_tools | default(false) | bool,
      }
```

## Variables

### cc-filter

| Variable                                  | Default                    | Description                                        |
| ----------------------------------------- | -------------------------- | -------------------------------------------------- |
| `agentic_tools_cc_filter_install`         | `true`                     | Install the cc-filter binary.                      |
| `agentic_tools_cc_filter_version`         | `v0.0.6`                   | cc-filter release tag to download.                 |
| `agentic_tools_cc_filter_install_path`    | `/usr/local/bin/cc-filter` | Destination for the cc-filter binary.              |
| `agentic_tools_cc_filter_binary_mode`     | `"0755"`                   | File mode for the installed binary.                |
| `agentic_tools_cc_filter_checksums`       | per-arch sha256 map        | Expected binary checksums; bump with the version.  |
| `agentic_tools_cc_filter_configure_hooks` | `true`                     | Merge cc-filter hooks into Claude `settings.json`. |
| `agentic_tools_cc_filter_download_url`    | derived from version/arch  | Override to pin a custom binary URL.               |

### Staged catalog

| Variable                                      | Default                           | Description                                                                      |
| --------------------------------------------- | --------------------------------- | -------------------------------------------------------------------------------- |
| `agentic_tools_stage_catalog`                 | `false`                           | Stage the agent catalog into the image.                                          |
| `agentic_tools_catalog_source_dir`            | the repository root               | Tree whose root holds the marketplace manifests to copy from.                    |
| `agentic_tools_catalog_marketplace_manifest`  | `.claude-plugin/marketplace.json` | Claude manifest path within that tree.                                           |
| `agentic_tools_catalog_codex_plugin_manifest` | `.codex-plugin/plugin.json`       | Codex manifest path within the plugin; its version must match.                   |
| `agentic_tools_plugin_name`                   | `agentdev`                        | Plugin to resolve out of the manifest.                                           |
| `agentic_tools_plugin_version`                | `""`                              | Version pin; the manifests must declare it. Empty means "whatever they declare". |
| `agentic_tools_catalog_root`                  | `/opt/agentdev`                   | Where the catalog is staged.                                                     |
| `agentic_tools_catalog_trees`                 | `.claude-plugin`, `.agents`       | Top-level directories copied from the source tree.                               |
| `agentic_tools_catalog_prune_names`           | scratch dir names                 | Build scratch directories removed from the staged copy.                          |
| `agentic_tools_catalog_mode`                  | `u=rwX,go=rX`                     | Permissions applied across the staged copy.                                      |

## Required External Variables

These variables are not defined by this role and must be supplied by the
playbook or inventory (the `extra_facts` role provides them in this
repository):

| Variable      | Description                                                            |
| ------------- | ---------------------------------------------------------------------- |
| `system_arch` | Target CPU architecture (`amd64` or `arm64`) for the binary URL.       |
| `user_home`   | Home directory of the target user (locates `~/.claude/settings.json`). |
