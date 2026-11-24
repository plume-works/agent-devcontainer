# `agentdev-iwe` — an IWE project-memory workflow for Claude Code and OpenCode

A Claude Code and OpenCode plugin that keeps a repository's project memory in an
[IWE](https://github.com/iwe-org/iwe) knowledge graph under `docs/knowledge/`, and
runs the work recorded there: explore an idea, plan it, implement the plan task by
task, verify the code against it, and ship it.

It is published from [plume-works/agent-devcontainer](https://github.com/plume-works/agent-devcontainer)
next to the `agentdev` plugin, whose git and pull-request skills the workflow calls.
Install both.

## Installing in Claude Code

Inside the `agentdev-devcontainer` image, both plugins are installed at user
scope when the container is created.

Everywhere else, add the marketplace to your repository's `.claude/settings.json`
and enable both plugins:

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
  "enabledPlugins": {
    "agentdev@agent-devcontainer": true,
    "agentdev-iwe@agent-devcontainer": true
  }
}
```

## Requirements

- [`uv`](https://docs.astral.sh/uv/) on `PATH`: the bundled scripts run through
  `uv run` and import the `agentdev-lib` package from PyPI.
- The `iwe` CLI on `PATH`.

## Starting a knowledge base

Run `/agentdev-iwe:iwe-bootstrap` in a repository with no `docs/knowledge/` yet,
then `/agentdev-iwe:iwe-setup`.
