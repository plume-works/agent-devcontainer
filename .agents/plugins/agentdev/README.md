# `agentdev` — a shared agent catalog for Claude Code and OpenCode

A Claude Code and OpenCode plugin with the agents, skills, and helper scripts for
everyday development work: git and pull requests, code review, CI log triage,
formatting and linting, and escalating a command to a container or Codespace when
the host lacks the toolchain.

It is published from [plume-works/agent-devcontainer](https://github.com/plume-works/agent-devcontainer),
so projects consume it by version instead of copying files around.

## Installing in Claude Code

Working inside the `agentdev-devcontainer` image, there is nothing to do:
the catalog is staged in the image and installed at user scope when the container
is created, with no clone and no network. It is an ordinary install, so updating
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

Restart Claude Code (or run `/plugin`) and the catalog is available.

## Installing in OpenCode

OpenCode reads the same directory through the bridge plugin in
`.opencode-plugin/`. The agentdev images register the staged bridge in
`~/.config/opencode/opencode.json`, and this repository's devcontainer points it
at the workspace copy on every editor attachment.

Everywhere else, check out this repository and list the bridge directory's
absolute path in the `plugin` array of your OpenCode config — the project's
`opencode.json`, or `~/.config/opencode/opencode.json` for every project:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "/path/to/agent-devcontainer/.agents/plugins/agentdev/.opencode-plugin"
  ]
}
```

The bridge has no dependencies to install. Restart OpenCode to load it.

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
- **`~/.local/bin`** — `iwe`, `iwes`, and `codebase-memory-mcp` from their
  GitHub releases, at the versions the devcontainer image pins, each verified
  against a recorded SHA-256.
- **`~/.zprofile`** — one block between `# >>> agentdev macos-bootstrap >>>`
  markers that loads `brew shellenv` and puts `~/.local/bin` first on `PATH`.
  A re-run rewrites that block and leaves the rest of the file alone.
- **Plugins** — registers this marketplace in Claude Code at user scope and
  installs `agentdev`, and does the same in Codex when `codex` is on `PATH`.
  Pass `--skip-plugins` (`curl ... | zsh -s -- --skip-plugins`) to leave both
  agents untouched.

It ends by checking every tool and the `python3` from a fresh login shell, and
exits nonzero naming whatever failed. Open a new terminal afterwards to pick up
the `PATH` change. Docker-backed skills such as `microvm-sandbox` and
Super-Linter are not set up; escalate those to a Codespace with
`remote-codespace-session`.

## Using it

Skills are namespaced by the plugin name — `/agentdev:pr-open`,
`/agentdev:pr-merge`, and so on. There is no opt-out; namespacing is what keeps
plugins from colliding. Claude also invokes them on its own when a request
matches a skill's description, so most of the time you just ask for the work.

Agents are addressed by name (`principal-engineer`, `tdd-red`, `tdd-green`,
`tdd-refactor`).

In OpenCode the same `/agentdev:<name>` commands appear in the `/` menu, the
model loads skills by either spelling, and each agent is a subagent limited to
the tools its definition lists. A skill that opts out of model invocation stays
available as its command only.

Scripts in `bin/` are on `PATH` while the plugin is enabled, so you can run e.g.
`super_linter.py local` or `python_lint_check.py` directly in a terminal.

### Agents

| Agent                | Use it for                                               |
| -------------------- | -------------------------------------------------------- |
| `principal-engineer` | Architecture, design decisions, implementation strategy. |
| `tdd-red`            | Write the failing test first.                            |
| `tdd-green`          | Make the failing test pass with the smallest change.     |
| `tdd-refactor`       | Clean up once the test is green.                         |

### Skills

#### Pull requests and git

| Skill                              | What it does                                                            |
| ---------------------------------- | ----------------------------------------------------------------------- |
| `/agentdev:git-commit`             | Conventional commit messages from the staged changes.                   |
| `/agentdev:git-new-branch`         | Start a work branch at the fetched remote base, with its own upstream.  |
| `/agentdev:git-merge-resolve`      | Merge a ref and resolve conflicts, escalating when unsure.              |
| `/agentdev:update-branch`          | Update the current feature branch from its remote base.                 |
| `/agentdev:gh-stack`               | Drive `gh stack` non-interactively; vendored from `github/gh-stack`.    |
| `/agentdev:pr-open`                | Open a PR from conversation context, or refresh the branch existing PR. |
| `/agentdev:pr-sync`                | Resync the branch PR title and body, delegating to `pr-open`.           |
| `/agentdev:pr-gen-description`     | Write a PR description from the change analysis.                        |
| `/agentdev:pr-review`              | Full automated review, published as one GitHub review.                  |
| `/agentdev:pr-feedback-resolution` | Work through review threads, CI failures, and CodeQL findings.          |
| `/agentdev:pr-eval-review-needed`  | Decide if pushed work needs a fresh AI review, and request it.          |
| `/agentdev:pr-request-ai-review`   | Ask an AI agent to review a PR.                                         |
| `/agentdev:pr-merge`               | Merge a PR with an explicit squash once CI and reviews are resolved.    |
| `/agentdev:pr-merge-stack`         | Bring every layer of a GitHub stack to green, then merge it at once.    |

#### Review, CI, and formatting

| Skill                                       | What it does                                             |
| ------------------------------------------- | -------------------------------------------------------- |
| `/agentdev:code-review-standards`           | The review standards the other review skills apply.      |
| `/agentdev:exec-summary`                    | One-minute, non-technical summary of the work in focus.  |
| `/agentdev:extract-github-actions-logs`     | Pull failing job logs out of a workflow run.             |
| `/agentdev:get-codeql-data`                 | Fetch CodeQL code-scanning alerts.                       |
| `/agentdev:local-reformat`                  | Run the full reformat workflow locally via Super-Linter. |
| `/agentdev:semantic-refactor-audit`         | Prove a behavior-preserving rewrite preserved behavior.  |
| `/agentdev:sync-super-linter-tool-versions` | Realign local tools with the pinned Super-Linter image.  |

#### Specs and escalation

| Skill                                | What it does                                                           |
| ------------------------------------ | ---------------------------------------------------------------------- |
| `/agentdev:microvm-sandbox`          | Run a command through the project devcontainer.                        |
| `/agentdev:remote-codespace-session` | Use a GitHub Codespace as a remote build and test machine.             |
| `/agentdev:create-agent`             | Add or update an agent in this catalog.                                |
| `/agentdev:create-skill`             | Add or update a skill in this catalog.                                 |
| `/agentdev:skill-scripts`            | Write a skill script's result and exit-code contract.                  |
| `/agentdev:template-consume`         | Adopt or update the agent-devcontainer template in another repository. |

#### Knowledge-graph workflow (IWE)

These skills run against an [IWE](https://iwe.md) workspace — a markdown
knowledge graph with a `data/` bundle of product, spec, architecture, and plan
documents. They are the project's memory across sessions.

| Skill                         | What it does                                                        |
| ----------------------------- | ------------------------------------------------------------------- |
| `/agentdev:iwe-bootstrap`     | Installs a blank IWE workspace without touching existing knowledge. |
| `/agentdev:iwe-setup`         | Brownfield onboarding: drafts the product and architecture docs.    |
| `/agentdev:iwe-explore`       | Thinking partner from an idea or a GitHub issue; never writes code. |
| `/agentdev:iwe-plan`          | Files a plan with verified anchors and its spec impact.             |
| `/agentdev:iwe-capture`       | Files a complete bug, proposed feature, or task, deduplicated.      |
| `/agentdev:iwe-implement`     | Executes a plan task-by-task, ticking boxes with evidence.          |
| `/agentdev:iwe-implement-all` | Implements every active plan in turn.                               |
| `/agentdev:iwe-branch-name`   | Names a plan's next `iwe/` iteration branch.                        |
| `/agentdev:iwe-verify`        | Pre-ship gate and drift audit: graph claims checked against code.   |
| `/agentdev:iwe-ship`          | Closes the loop: spec sync, stage flips, release recording.         |
| `/agentdev:iwe-ship-all`      | Ships every implemented plan in turn.                               |
| `/agentdev:iwe-weekly`        | Read-only digest: shipped, in flight, bugs, backlog, graph health.  |
| `/agentdev:iwe-audit`         | Prunes session residue from documents and comments.                 |

## What it expects

Most skills shell out to tools rather than reimplementing them. Depending on
which ones you use, you will need `git`, an authenticated `gh` CLI, Docker (for
`microvm-sandbox` and Super-Linter), and `uv` for the Python skills. The
[devcontainer image](https://github.com/plume-works/agent-devcontainer) ships
all of them preinstalled, but the plugin works in any environment that has the
tools a given skill needs.

## Tests

The plugin carries its own suite in `tests/`, covering the observable behavior of the
scripts it ships — the `bin/` helpers and the `agent-code/` bundled with individual skills,
including their exit codes and `RESULT=` lines. Run it with `pytest tests` from this
directory; it needs `pytest`, `git`, and `bash`. The OpenCode bridge has its own
suite, run with `bun test ./tests/opencode`.

The tests resolve everything they exercise through a `plugin_root` fixture, so they pass
from an installed copy of the plugin as readily as from the repository that develops it.
A test for a script this plugin ships belongs here, not in the test suite of whatever
package happens to live alongside it.

## Contributing

`.agents/plugins/agentdev/` is the canonical source for the catalog, and this repository is where
it is developed. See the [repository README](https://github.com/plume-works/agent-devcontainer#the-agent-catalog) for
the editing rules and how to validate a change.
