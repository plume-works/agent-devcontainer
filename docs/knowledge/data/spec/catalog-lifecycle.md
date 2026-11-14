---
type: spec
description: When and how the agentdev catalog gets installed into the persistent Claude plugin state and the OpenCode user config — during the agentdev-base build, by the agentdev-devcontainer lifecycle phases, by the standalone runtime, per Claude worktree, and in CI agent jobs — and how the create phase clears codebase-memory-mcp's leftovers.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/cbm_purge.py
- resource: ansible/roles/agent_catalog/tasks/install_catalog.yml
- resource: ansible/roles/agent_catalog/tasks/stage_catalog.yml
- resource: docker/base/agentdev-base.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: README.md
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/workspace.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/worktree.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/git.py
- resource: .github/actions/run-claude-responder/action.yml
- resource: .claude/.gitignore
- resource: ansible/roles/agentic_tools/defaults/main.yml
- resource: .devcontainer/docker-compose.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode.py
---

# Catalog lifecycle

## Requirements

### Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the `agentdev-base` build, at Claude user scope
and by registering the catalog's OpenCode bridge plugin in the user's OpenCode
config, so a consumer that runs the image without lifecycle commands resolves
`agentdev:*` skills. The install step SHALL take the marketplace name from the
staged `.claude-plugin/marketplace.json` and add the marketplace from the staged
path, needing no network access and no authentication. `agentdev-base` SHALL
install OpenCode v2 from the npm package `@opencode/cli` at the version
`agentic_tools_opencode_version` pins. `agentdev-devcontainer`'s create phase
SHALL also install it into the runtime account's home volume, which starts empty
and receives no image content. `~/.claude.json` SHALL be a regular file on that
volume.

#### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `agentdev-base` without client-state volumes
  and no lifecycle command runs
- **THEN** the catalog installed during the image build is present, an
  `agentdev:*` skill resolves in Claude Code, and OpenCode loads the staged
  bridge plugin and lists the catalog's skills.

#### Scenario: a devcontainer starts with a catalog already installed on its home volume

- **WHEN** the home volume already holds a prior install and `~/.claude.json`,
  and the container is recreated
- **THEN** `~/.claude.json`'s content is preserved (Claude may append bootstrap
  fields, so the guarantee is content preservation, not byte-identity), and the
  create phase re-applies the catalog install every time the container is
  created, so it is never silently stale.

#### Scenario: a home volume still holds the ~/.claude.json link

- **WHEN** `~/.claude.json` is a symlink to `~/.claude/claude.json`
- **THEN** it is replaced by a regular file with the link target's content, and
  the target is removed.

### Requirement: registering a catalog root replaces earlier registrations

`agentdev-runtime catalog install <root>` SHALL uninstall every plugin the
root's `.claude-plugin/marketplace.json` publishes from the `user`, `project`,
and `local` scopes, under the manifest's marketplace name and under any
marketplace already registered from the same root, SHALL remove those
marketplaces, and SHALL then add the root as a marketplace and install every
published plugin at the requested scope. It SHALL leave exactly one bridge entry
in the OpenCode config's `plugin` list, pointing at the root's bridge, replacing
any entry for another root's bridge and keeping every other key and plugin. A
root that ships no Claude manifest or no OpenCode bridge SHALL leave that
client's registration as it was.
