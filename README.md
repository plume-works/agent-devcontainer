# agent-devcontainer

A general-purpose, Ansible-provisioned development container built for
agent-driven development. Python + Node, Docker-in-Docker, an Xpra remote
desktop, Claude Code and Codex preinstalled, an opt-in egress firewall, and a
curated catalog of agents and skills.

The runtime is project-agnostic. This publishing repository also contains image,
catalog, validator, and CI source that a consuming project does not need. Point an
existing devcontainer at the published image for the environment, or follow the
[manual template guide](docs/using-as-template.md) for the complete setup.

## What's in the image

| Area          | Contents                                                                                  |
| ------------- | ----------------------------------------------------------------------------------------- |
| Python        | `uv` (installer, resolver, venv manager), system `python3`, `pre-commit`                  |
| JavaScript    | `bun` (also used to install global CLIs), Node.js 24 from NodeSource, `yarn`              |
| Agents        | `@anthropic-ai/claude-code`, `@openai/codex`, `@modelcontextprotocol/inspector`           |
| Build tooling | `build-essential`, CMake (Kitware), Ninja, `pkg-config`                                   |
| Lint / CI     | `shellcheck`, `zizmor` (pinned + checksummed), `jq`, `ffmpeg`, `btop`                     |
| Git / GitHub  | `git`, `git-lfs`, `gh` + a transparent auth wrapper that injects `GH_TOKEN` from the host |
| Shells        | `bash` and `fish` (with fisher + bass), UTC timezone, `en_US.UTF-8` locale                |
| Desktop       | Xpra 6.4.3 with the HTML5 client, xpra-html5 v19, VirtualGL 3.1.4, mesa, Xvfb             |
| Containers    | Docker CE + CLI + buildx + compose (daemon started by the devcontainer DinD feature)      |
| Secrets       | GNOME Keyring Secret Service, brought up headless so `gh auth login` can persist a token  |
| Firewall      | `init-firewall.sh` + a NOPASSWD sudoers entry — **installed but inert unless enabled**    |

Images are published multi-arch (`linux/amd64` + `linux/arm64`), built on native
runners and merged into a single manifest:

- `ghcr.io/plume-works/agent-desktop:edge` — the development image
- `ghcr.io/plume-works/ubuntu-ansible:edge` — the Ansible base it is built from

## Using it in another project

### Option 1 — point an existing devcontainer at the image

```jsonc
// .devcontainer/devcontainer.json
{
  "image": "ghcr.io/plume-works/agent-desktop:edge@sha256:dfd576e3ad4afb6b3b5dfae01582bd88f4542d7bab528eae36be158931fe001d",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:4.0.0": {},
  },
  "containerEnv": {
    "DEV_WORKSPACE_FOLDER": "/workspaces/${localWorkspaceFolderBasename}",
  },
}
```

`DEV_WORKSPACE_FOLDER` is the one variable the image cares about: the `gh`
wrapper PATH shim and the firewall allowlist lookup both read it, falling back to
the `workspace_folder` baked in at build time.

That is the whole setup for the development environment. The catalog is staged in
the image but must be installed after user volumes are mounted. Use the lifecycle
scripts from Option 2 when the existing project should receive it automatically.

### Option 2 — copy the template

The template surface is broader than the two visible devcontainer files: lifecycle
scripts, the feature lock, digest pin, MCP configuration, agent settings, tooling,
and adaptable GitHub workflows all participate. Use the
[step-by-step manual guide](docs/using-as-template.md) for either a full repository
copy or a selective copy into an existing project. The complete classified inventory
is in [Repository structure](docs/repository-structure.md).

### The catalog ships with the image

The image stages the catalog at `AGENTDEV_CATALOG_DIR` (`/opt/agentdev`), and the
template's `postCreateCommand` installs it from there through each agent's own
plugin CLI — `claude plugin install` at user scope and `codex plugin add`. No
clone, no network, no firewall allowlist entry, and no per-repository
configuration. Skills are namespaced by the plugin: `/agentdev:pr-open`,
`/agentdev:pr-merge`, and so on. Codex gets the same catalog, agents included.

The install happens in a lifecycle hook rather than during the image build
because the `agentdev-claude` and `agentdev-codex` volumes mount over `~/.claude`
and `~/.codex`, which is exactly where both agents record installed plugins. An
install baked into the image would be hidden by those volumes for every container
after the first. Both volumes are scoped per devcontainer instance, so the
install also runs once per worktree rather than once per machine; only each
agent's credentials are shared across worktrees, via the separate `agentdev-agents-auth`
volume.

Consequences worth knowing:

- **Updating the catalog means updating the image.** The staged copy is
  root-owned and read-only, and nothing rewrites it at runtime. Which version an
  image carries is inspectable:

  ```bash
  docker inspect -f '{{ index .Config.Labels "org.opencontainers.image.version.agentdev" }}' \
    ghcr.io/plume-works/agent-desktop:edge
  ```

- **To run a different version than the image carries**, declare it in your
  project's `.claude/settings.json` as
  [`.agents/plugins/agentdev/README.md`](.agents/plugins/agentdev/README.md)
  describes. Because the image install is an ordinary user-scope install, a
  project declaration composes with it the usual way — nothing has to be disabled
  first.
- **A project that ships the catalog itself** — this repository, or a fork of it
  — needs no opt-out. `postStartCommand` re-runs
  [`reinstall-agentdev-claude.sh`](.devcontainer/scripts/reinstall-agentdev-claude.sh)
  and its Codex counterpart with no arguments on every container start, which
  re-registers the marketplace from the workspace over the image's copy. In any
  other project those scripts find no marketplace manifest and exit quietly.

### Staying on the current image

Both options pin `agent-desktop` by tag **and** digest
(`:edge@sha256:...`) rather than a bare moving tag, so the image a consumer runs
never changes silently under it. That only helps if something advances the pin
when the image is rebuilt — point [Renovate](https://docs.renovatebot.com/) (or
an equivalent) at the repository with a config that includes the `docker` (or
`docker-compose`/`dockerfile`, depending on where the pin lives) manager, for
example:

```jsonc
// renovate.json
{
  "extends": ["config:recommended"],
}
```

This repository's own [`.github/renovate.json`](.github/renovate.json) shows how
the consumer pin is discovered and why it lives outside the image-build path filter.
It also contains publisher-specific rules that a copied project must review; see the
[manual template guide](docs/using-as-template.md#renovate).

#### Renovate dashboard

The [Renovate dashboard is here](https://developer.mend.io/github/plume-works/agent-devcontainer).

## Enabling the firewall

The firewall is installed in the image but does nothing until you ask for it.
Set `ENABLE_FIREWALL=true` and edit the allowlist:

```jsonc
// .devcontainer/devcontainer.json
"containerEnv": { "ENABLE_FIREWALL": "true" }
```

`.devcontainer/firewall-allowlist.txt` is read at container start, so per-branch
edits take effect on the next start with no image rebuild. It default-DROPs IPv4
egress, blocks IPv6 entirely, preserves Docker's embedded-DNS NAT rules, and
self-verifies (a known-blocked host must fail, `api.github.com` must succeed) —
exiting non-zero if either check goes the wrong way.

## Reaching the Xpra desktop

`.devcontainer/scripts/postStartCommand.sh` starts Xpra in the background on
display `:100`. The HTML5 client port is derived per devcontainer as
`14500 + cksum(DEVCONTAINER_ID) % 100`, so parallel worktrees never collide;
`forwardPorts` covers the whole `14500-14599` range. Open the forwarded port in a
browser. For GPU-accelerated rendering, prefix the app with `vglrun`.

Manage it directly with `/start-xpra.sh --background`, `--stop`, or
`--port <n>`.

## Provisioning knobs

`docker/desktop/agent-desktop.Dockerfile` enables every capability role. To
build a leaner image, flip them off — they default to `false` in
`ansible/playbooks/group_vars/all.yml`:

| Variable                        | Effect when `true`                                                      |
| ------------------------------- | ----------------------------------------------------------------------- |
| `install_xpra`                  | Xpra + xpra-html5 + VirtualGL + mesa/Xvfb (the largest single addition) |
| `install_docker`                | Docker CE, CLI, buildx, compose (installed, daemon not started)         |
| `install_agentic_tools`         | Claude Code, Codex, MCP inspector                                       |
| `install_validate_agent_files`  | The `validate_agent_files` CLI, on `PATH` as an isolated `uv` tool      |
| `install_devcontainer_firewall` | `init-firewall.sh` + sudoers entry (still runtime-gated)                |
| `setup_user`                    | Create a non-root `devuser` (1001:1001) instead of running as root      |
| `workspace_folder`              | Fallback workspace path baked into the image                            |

The staged catalog rides on `install_agentic_tools` and is switched separately by
`agentic_tools_stage_catalog`, which the desktop dockerfile turns on; the version
it stages comes from the `AGENTDEV_PLUGIN_VERSION` build argument.
[`ansible/roles/agentic_tools/README.md`](ansible/roles/agentic_tools/README.md)
documents the staged layout and the variables that shape it.

`install_validate_agent_files` works the same way: the package is built from
`py_packages/validate_agent_files/` in the build context, and the
`VALIDATE_AGENT_FILES_VERSION` build argument is a pin the build verifies against
the version it actually installs. Bump it together with the package's
`pyproject.toml`.
[`ansible/roles/validate_agent_files/README.md`](ansible/roles/validate_agent_files/README.md)
documents the install layout.

## Building locally

The desktop image's build context is the repository root — the dockerfile
bind-mounts the whole context at `/provision` so Ansible can read `ansible/`,
`docker/bin/gh`, the catalog, and the validator package.

```bash
docker build -t local/ubuntu-ansible docker/ansible

docker buildx build \
  -f docker/desktop/agent-desktop.Dockerfile \
  --build-arg FROM_IMAGE=local/ubuntu-ansible \
  -t local/agent-desktop .
```

Then smoke it:

```bash
docker run --rm local/agent-desktop bash -lc '
  bun --version && node --version && uv --version &&
  gh --version | head -1 && cmake --version | head -1 && zizmor --version &&
  command -v xpra init-firewall.sh gnome-keyring-daemon validate_agent_files &&
  validate_agent_files --help >/dev/null'
```

And check the staged catalog:

```bash
docker run --rm local/agent-desktop bash -lc '
  cat "$AGENTDEV_CATALOG_DIR/.claude-plugin/marketplace.json" | jq -r .name &&
  cat "$AGENTDEV_CATALOG_DIR/.agents/plugins/marketplace.json" | jq -r .name &&
  ls "$AGENTDEV_CATALOG_DIR/.agents/plugins"/*/skills | head -3'
```

Ansible alone, without a build:

```bash
cd ansible
uv run ansible-lint .
uv run ansible-playbook --syntax-check playbooks/setup-dev.yml
```

## The agent catalog

The catalog ships as the `agentdev` Claude Code and Codex plugin in [`.agents/plugins/agentdev/`](.agents/plugins/agentdev/) —
four agents (Principal Engineer plus the TDD Red/Green/Refactor trio) and 24
skills covering git, pull requests, review, CI log extraction, formatting, and
container/Codespace escalation. **[`.agents/plugins/agentdev/README.md`](.agents/plugins/agentdev/README.md) documents
what it contains and how to enable it in another repository**; the rest of this
section is about developing it here.

### Source of truth

`.agents/plugins/agentdev/` is canonical. Everything else is derived:

| Path                                            | Role                                                                         |
| ----------------------------------------------- | ---------------------------------------------------------------------------- |
| `.agents/plugins/agentdev/`                     | Canonical agents, skills, hooks, and `bin/` scripts.                         |
| `.agents/plugins/agentdev/tests/`               | The plugin's own tests for the scripts it ships.                             |
| `.agents/plugins/agentdev/.claude-plugin/`      | Packages the catalog for Claude Code.                                        |
| `.agents/plugins/agentdev/.codex-plugin/`       | Packages the same catalog for Codex.                                         |
| `.claude-plugin/marketplace.json`               | Publishes the plugin so other repositories can consume it.                   |
| `.agents/plugins/marketplace.json`              | Publishes the repo-local Codex marketplace entry.                            |
| `.devcontainer/scripts/reinstall-agentdev-*.sh` | Registers the image or workspace marketplace after persistent volumes mount. |
| `.claude/settings.json`                         | Repository permissions and enabled third-party Claude plugins.               |

### Editing rules

- **Edit files under `.agents/plugins/agentdev/`, never under `.codex/`.**
- Codex consumes agents and skills directly from the canonical plugin tree; do
  not recreate `.codex/agents/` trampolines or a `.codex/skills` symlink.
- Use the [create-agent](.agents/plugins/agentdev/skills/create-agent/SKILL.md) and
  [create-skill](.agents/plugins/agentdev/skills/create-skill/SKILL.md) skills — they encode the
  frontmatter, discovery-description, and validation rules.
- **Never write a repository-relative catalog path** such as
  `.claude/skills/<name>/...`: inside a plugin it resolves nowhere. Use
  `${CLAUDE_SKILL_DIR}/...` for a path within the same skill, and a namespaced
  invocation for a sibling skill.
- A script in `.agents/plugins/agentdev/bin/` must not assume it sits inside the repository it
  operates on. Resolve the target repository from the working directory (see
  [`.agents/plugins/agentdev/bin/__utils.sh`](.agents/plugins/agentdev/bin/__utils.sh)).
- Bump `version` in both plugin manifests and the marketplace entry together.

[AGENTS.md](AGENTS.md) has the repository conventions agents follow.

### Iterating and validating

```bash
claude --plugin-dir ./.agents/plugins/agentdev
claude plugin validate ./.agents/plugins/agentdev
```

Run the repository validator and both test suites before pushing a catalog change:

```bash
uv sync --all-groups
uv run validate_agent_files --recommend . --require-marketplace claude codex
uv run pytest   # both suites: py_packages/ and .agents/plugins/agentdev/tests/
```

The two test suites are separate on purpose and stay that way. `py_packages/validate_agent_files/tests/`
covers a package that is released independently, so it must pass with no knowledge of this
repository — check that directly with:

```bash
cd py_packages/validate_agent_files && uv run --isolated --extra dev pytest
```

`.agents/plugins/agentdev/tests/` covers the behavior of the scripts the plugin ships — `bin/`
helpers and the `scripts/` bundled with individual skills. It resolves them through a
`plugin_root` fixture rather than a repository-relative path, so the suite also passes from a
consumer's plugin cache. A test that exercises a shipped script belongs here, never in the
package.

## Repository layout

[Repository structure](docs/repository-structure.md) is the persistent inventory of
the live tree, including the default template surface, files that require manual
customization, the optional image-building bundle, publisher-only source, and generated
state. The [template guide](docs/using-as-template.md) turns that inventory into manual
full-copy and selective-copy procedures.

## License

MIT — see [LICENSE](LICENSE).
