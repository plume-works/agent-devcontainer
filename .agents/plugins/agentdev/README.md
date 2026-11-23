# `agentdev` — a shared agent catalog for Claude Code and OpenCode

A Claude Code and OpenCode plugin with the agents, skills, and helper scripts for
everyday development work: git and pull requests, code review, CI log triage,
formatting and linting, and escalating a command to the project devcontainer when
the host lacks the toolchain.

It is published from [plume-works/agent-devcontainer](https://github.com/plume-works/agent-devcontainer),
so projects consume it by version instead of copying files around.

## Installing in Claude Code

Working inside the `agentdev-devcontainer` image, there is no setup step:
the image stages the catalog and installs every plugin it publishes at user
scope once the container is created, without a clone or network access. It is an ordinary install, so updating
it means updating the image, and a project that declares its own marketplace
composes with it the usual way.

Everywhere else, add to your repository's `.claude/settings.json` — strict JSON, so no comments
and no trailing commas (unlike `devcontainer.json`):

```json
{
  "extraKnownMarketplaces": {
    "agent-devcontainer": {
      "source": {
        "source": "github",
        "repo": "plume-works/agent-devcontainer"
      }
    }
  },
  "enabledPlugins": { "agentdev@agent-devcontainer": true }
}
```

The IWE project-memory workflow is a separate plugin from the same marketplace.
To use it as well, also enable it:

```json
  "enabledPlugins": {
    "agentdev@agent-devcontainer": true,
    "agentdev-iwe@agent-devcontainer": true
  }
```

Restart Claude Code (or run `/plugin`) and the catalog is available.

## Installing in OpenCode

OpenCode runs the catalog only inside the agentdev images. The image stages an
OpenCode bridge beside the plugins and registers it in
`~/.config/opencode/opencode.json`; the bridge loads every plugin that the
marketplace publishes. This repository's devcontainer points it at the
workspace copy on every editor attachment.

## Native macOS

To run the catalog on a Mac without the devcontainer, install
[Homebrew](https://brew.sh) and then run the bootstrap with macOS's own zsh:

```sh
curl -fsSL https://raw.githubusercontent.com/plume-works/agent-devcontainer/main/.agents/plugins/agentdev/bin/macos-bootstrap.zsh | zsh
```

Once the plugin is enabled, the same script is on `PATH` as
`macos-bootstrap.zsh`, so re-running it is a plain command. Every step is safe
to repeat. It changes the host in these ways:

- **Homebrew packages** — `uv`, `jq`, `gh`, `shellcheck`, `bun`, `pre-commit`,
  and the `claude-code` cask, at whatever version Homebrew ships.
- **Python** — `uv python install --default` puts the Python version the catalog
  is tested on in `~/.local/bin` as `python3`.
- **`~/.local/bin`** — `iwe` and `iwes` from their GitHub release, at the version
  the devcontainer image pins, verified against a recorded SHA-256.
- **`~/.zprofile`** — one block between `# >>> agentdev macos-bootstrap >>>`
  markers that loads `brew shellenv` and puts `~/.local/bin` first on `PATH`.
  A re-run rewrites that block and leaves the rest of the file alone.
- **`~/.config/fish/conf.d/agentdev.fish`** — when fish is installed or is your
  login shell, the same kind of block for fish: `brew shellenv fish`, then
  `fish_add_path` for `~/.local/bin`.
- **Plugins** — registers this marketplace in Claude Code at user scope and
  installs `agentdev`; Claude Code is the only agent it configures. Pass
  `--skip-plugins` (`curl ... | zsh -s -- --skip-plugins`) to leave Claude
  Code's plugins untouched.

It ends by checking every tool and the `python3` from a fresh zsh login shell,
and `python3` again from your `$SHELL` when that is not zsh, and exits nonzero
naming whatever failed. A shell configuration that later puts another `python3`
first, such as a `config.fish` that re-runs `brew shellenv`, fails that check. Open a new terminal afterwards to pick up
the `PATH` change. Docker-backed skills such as `devcontainer-sandbox` are
not set up.

## Using it

Skills are namespaced by the plugin name — `/agentdev:pr-open`,
`/agentdev:pr-merge`, and so on. There is no opt-out; namespacing is what keeps
plugins from colliding. Claude also invokes them on its own when a request
matches a skill's description, so most of the time you just ask for the work.

Agents are addressed by name (`principal-engineer`).

In OpenCode the same `/agentdev:<name>` commands appear in the `/` menu, the
model loads skills by either spelling, and each agent is a subagent limited to
the tools its definition lists. A skill that opts out of model invocation stays
available as its command only.

Scripts in `bin/` are on `PATH` while the plugin is enabled, so you can run e.g.
`python_lint_check.py` directly in a terminal.

### Knowledge-graph workflow (IWE)

The IWE workflow — planning, implementing, verifying, and shipping work recorded
in an [IWE](https://iwe.md) knowledge graph — is the separate `agentdev-iwe`
plugin, invoked as `/agentdev-iwe:<name>`.

## What it expects

Every bundled script runs through `uv run`, so `uv` is required: on first use
it installs the script's dependencies, including the `agentdev-lib` package from
PyPI. Most skills shell out to tools rather than reimplementing them. Depending on
which ones you use, you will also need `git`, an authenticated `gh` CLI, and
Docker (for `devcontainer-sandbox`). The
[devcontainer image](https://github.com/plume-works/agent-devcontainer) ships
all of them preinstalled, but the plugin works in any environment that has the
tools a given skill needs.

## Tests

The plugin carries its own suite in `tests/`, covering the observable behavior of the
scripts it ships — the `bin/` helpers and the `agent-code/` bundled with individual skills,
including their exit codes and `RESULT=` lines. Run it with `uv run pytest tests` from
this directory; it needs `git` and `bash`.

The tests resolve everything they exercise through a `plugin_root` fixture, so they pass
from an installed copy of the plugin as readily as from the repository that develops it.
A test for a script this plugin ships belongs here, not in the test suite of whatever
package happens to live alongside it.

## Contributing

`.agents/plugins/agentdev/` is the canonical source for the catalog, and this repository is where
it is developed. See the [repository README](https://github.com/plume-works/agent-devcontainer#the-agent-catalog) for
the editing rules and how to validate a change.
