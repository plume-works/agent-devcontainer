# Agent Catalog Role

Stages the agent catalog Claude Code and OpenCode read into the image, then
installs it into each agent's plugin state during the build:

- **The staged catalog**: a build-time copy of the catalog, so a container built
  from the image can install it with no clone and no network.
- **The build-time install**: registers that staged copy and installs the plugin
  into each agent's plugin state, so a raw-image consumer resolves the catalog
  without any lifecycle hooks.

Gated by `install_agent_catalog` in the playbook, and placed after
`agentic_tools`, whose `claude` CLI the install runs.

## The staged catalog

The role copies `.claude-plugin/` and `.agents/plugins/` to `agent_catalog_root`
in their source layout. The Claude Code marketplace manifest resolves each plugin
by a path relative to the marketplace root, and OpenCode loads the bridge plugin
inside it, so the layout is preserved rather than rearranged:

```text
$agent_catalog_root/
  .claude-plugin/marketplace.json     # Claude Code marketplace
  .agents/plugins/<plugin>/           # the plugin, with its OpenCode bridge
```

The `.agents/` root files are contributor instructions for the catalog's
publisher and are not staged. Plugin `tests/` directories and build scratch are
pruned from the staged copy: plugin tests run only in the publisher checkout.

**This role both stages and installs.** `install_catalog.yml` registers the
staged root as a Claude marketplace, installs the plugin at user scope, and
registers the OpenCode bridge during the build, so a consumer that runs the image
without lifecycle hooks — a plain `docker run`, a Codespace, a CI job — still
resolves `agentdev:*` skills. See
[ADR-0044](../../../docs/knowledge/data/adr/0044-image-and-create-phase-both-install-catalog.md).

The container's lifecycle scripts **also** install, and must: a devcontainer
mounts a persistent `~/.claude` volume over where Claude Code keeps its
marketplace registry, enablement flags, and plugin cache, so the build-time
install is shadowed there and would otherwise go stale. The runtime's
`agentdev-runtime catalog install <root>` takes the staged root and re-applies it
on every container create.

Two properties constrain changes:

- **The catalog is staged from the provisioning sources**
  (`agent_catalog_source_dir`, the build context under Docker), so the image and
  the catalog it carries always come from the same commit. Set
  `agent_catalog_plugin_version` to pin: the Claude marketplace manifest must
  declare exactly that version or provisioning fails.
- **The staged copy is read-only.** It is installed root-owned, directories
  `0755` and files `0644` with existing executables preserved, and lives outside
  `$HOME` so no volume can shadow it. Nothing writes to it at runtime, so
  **updating the staged catalog means rebuilding the image** — a container that
  wants a different catalog registers its own marketplace on top instead.

## Example Usage

```yaml
- name: Stage and install the agent catalog
  hosts: all
  become: true
  roles:
    - {
        role: agent_catalog,
        tags: ['agent_catalog'],
        when: install_agent_catalog | default(false) | bool,
      }
```

## Variables

| Variable                             | Default                             | Description                                                                    |
| ------------------------------------ | ----------------------------------- | ------------------------------------------------------------------------------ |
| `agent_catalog_source_dir`           | the repository root                 | Tree whose root holds the marketplace manifest to copy from.                   |
| `agent_catalog_marketplace_manifest` | `.claude-plugin/marketplace.json`   | Claude manifest path within that tree.                                         |
| `agent_catalog_plugin_name`          | `agentdev`                          | Plugin to resolve out of the manifest.                                         |
| `agent_catalog_plugin_version`       | `""`                                | Version pin; the manifest must declare it. Empty means "whatever it declares". |
| `agent_catalog_root`                 | `/opt/agentdev`                     | Where the catalog is staged.                                                   |
| `agent_catalog_trees`                | `.claude-plugin`, `.agents/plugins` | Directories copied from the source tree.                                       |
| `agent_catalog_prune_names`          | scratch and `tests` dir names       | Directories removed from the staged copy.                                      |
| `agent_catalog_mode`                 | `u=rwX,go=rX`                       | Permissions applied across the staged copy.                                    |

## Required External Variables

These variables are not defined by this role and must be supplied by the
playbook or inventory (the `extra_facts` role provides them in this
repository):

| Variable    | Description                                                      |
| ----------- | ---------------------------------------------------------------- |
| `user_home` | Home directory of the target user (locates the OpenCode config). |
