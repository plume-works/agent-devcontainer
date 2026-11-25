# agent-devcontainer

A reproducible, multi-architecture development environment built for agent-driven
software development.

`agent-devcontainer` combines a ready-to-use container image, a plugin catalog for
Claude Code and OpenCode, project-memory workflows, automated pull-request review,
validation tooling, and reusable scaffolding for adopting the environment in other
repositories.

## What you get

- A multi-architecture `linux/amd64` and `linux/arm64` image published through GHCR,
  built on [`ghcr.io/plume-works/devcontainer-base`](https://github.com/plume-works/images).
- Python development through `uv`, and Bun for JavaScript (no Node.js).
- systemd as PID 1, running a nested Docker engine with Buildx and Compose, plus Git LFS
  and GitHub CLI.
- Claude Code and OpenCode preinstalled with the shared `agentdev` and `agentdev-iwe`
  plugins.
- A browser-accessible Xpra desktop with VirtualGL support.
- An optional default-deny egress firewall with repository-controlled allowlisting.
- IWE knowledge-graph workflows from project setup through verified shipment.
- GitHub Actions for validation, formatting, image publishing, and AI review.

The repository publishes one image, `ghcr.io/plume-works/agentdev-devcontainer:edge`:
the base image's toolchain and agents, plus Xpra, Playwright, the pinned linters, the
staged catalog, the firewall, and the lifecycle commands. It is built on native runners,
merged into a multi-architecture manifest, and `edge` moves only after it passes native
acceptance. Ubuntu 26.04 comes from the base image, with apt pinned to a dated archive
snapshot.

To run OpenCode or Claude Remote Control without an editor, as a Coder workspace, use
plume-works' Coder template image instead; this repository publishes no standalone
runtime.

## Quick start

There are two supported adoption paths, both on the same published runtime.

### Use the image

Point an existing devcontainer at the published image:

```jsonc
// .devcontainer/devcontainer.json
{
  "image": "ghcr.io/plume-works/agentdev-devcontainer:edge@sha256:dddd993a4ba9d09b0c05e452d9ccdd56ab261b3454a16826cf3a72fb47e1e12c",
  "containerEnv": {
    "DEV_WORKSPACE_FOLDER": "/workspaces/${localWorkspaceFolderBasename}",
  },
}
```

The image's metadata supplies the create, start, and attach commands, `waitFor`, the
privileged mode, the `dev` remote user, and the volumes for `/home/dev`,
`/var/lib/docker`, and `/var/lib/containerd`. systemd stays PID 1 and starts the
services. Declare none of them again, add no Docker-in-Docker Feature, and copy no
lifecycle script; the editor attaches only once the required services are ready.
GitHub Codespaces is not supported.

Pin by tag and digest so the environment never changes silently. Renovate or an
equivalent dependency updater can advance the digest when a new image is available;
this repository's [Renovate configuration](.github/renovate.json) provides a working
example.

### Derive a custom image

Add tooling in an image that starts `FROM ghcr.io/plume-works/agentdev-devcontainer`.
Extend the lifecycle with executable hooks in
`/etc/agentdev/hooks/{created,started,attached}.d/`, which run in name order at the end
of their phase, and override the image's documented environment. Files below
`/opt/uv-tools/agentdev-runtime/` belong to the image: the runtime refuses to start when one is
changed, added, or removed. See [ADR-0032](docs/knowledge/data/adr/0032-runtime-integrity-from-wheel-record.md).

## Services and troubleshooting

systemd runs every service. At each start, `agentdev-bootstrap.service` runs as root
before the Docker engine: it hands the container's environment to the other units,
prepares the home, workspace, and shared auth volume, trusts an extra CA, and applies
the opt-in firewall. `docker.service` comes from the base image and requires the
bootstrap, so the engine never starts without the firewall. `agentdev-created.service`
runs the create phase once per container as `dev`, and the user unit
`agentdev-xpra.service` runs the desktop.

- `agentdev-runtime health status` prints each unit's state and, for a failed one,
  the `journalctl` command that shows its log. The image healthcheck runs
  `agentdev-runtime health ready`.
- `systemctl status agentdev-bootstrap agentdev-created docker` and
  `systemctl --user status agentdev-xpra` show the units; `journalctl -u <unit> -b`
  shows a unit's log.
- systemd restarts a failed engine or desktop; a failed bootstrap or create phase
  stays failed until the container restarts, and the start phase reports it.

Tools run as `dev`, with passwordless `sudo`. The devcontainer CLI changes its UID and
GID to the host user's.

| Path                     | Volume                                 | Holds                                                   |
| ------------------------ | -------------------------------------- | ------------------------------------------------------- |
| `/home/dev`              | `agentdev-home-<devcontainerId>`       | Configuration, sessions, uv cache, and project venvs    |
| `/var/lib/docker`        | `dind-var-lib-docker-<devcontainerId>` | The nested engine, including its image store            |
| `/var/lib/containerd`    | `dind-var-lib-containerd-<id>`         | The nested engine's containerd content                  |
| `/var/lib/agentdev/auth` | `agentdev-agents-auth-<uid>-<gid>`     | Claude Code logins shared by the host user's containers |

## Development environment

| Area        | Included tools and capabilities                                        |
| ----------- | ---------------------------------------------------------------------- |
| Python      | `uv`, system Python, and `pre-commit`                                  |
| JavaScript  | Bun; Playwright and MCP Inspector run through `bun --bun`              |
| Agents      | Claude Code, OpenCode, and MCP Inspector                               |
| Quality     | Ruff, ShellCheck, Zizmor, Prettier, Hadolint, Gitleaks, and Actionlint |
| GitHub      | Git, Git LFS, `gh`, and a transparent host-token wrapper               |
| Containers  | Docker CE, Buildx, and Compose under systemd                           |
| Desktop     | Xpra with its HTML5 client, VirtualGL, Mesa, and Xvfb                  |
| Credentials | Shared agent authentication                                            |
| Security    | An opt-in egress firewall with an allowlist and startup checks         |

Python commands run through `uv run`. Python environments, agent state, and pre-commit
environments persist across container rebuilds and remain isolated per worktree. Authentication is shared so opening another worktree does not
require signing in again.

### Upgrading from an image with Codex

Earlier images also shipped Codex. Claude Code and OpenCode are now the only
supported harnesses, so an existing devcontainer's `agentdev-codex` volume and the
`codex/auth.json` file on the shared auth volume are no longer used. Nothing removes
them; delete them by hand once you no longer need them:

```bash
# A devcontainer's per-instance Codex volume
docker volume rm <project>_agentdev-codex
# The Codex login on the devcontainer's shared auth volume
docker run --rm -v agentdev-agents-auth:/auth busybox rm -rf /auth/codex
```

## The plugin catalog

The repository is its own plugin marketplace. It publishes two plugins, `agentdev`
and `agentdev-iwe`; a project enables either or both. OpenCode loads every published
plugin through the OpenCode bridge in `.agents/opencode-bridge/`. The plugins'
bundled scripts run through `uv run` and share the `agentdev-lib` package, published
to PyPI from `py_packages/agentdev_lib/`.

The image stages the catalog under `/opt/agentdev`. The create phase installs every
plugin into each agent's user scope, and the attach phase refreshes a repository's
workspace copy on editor attachment.

### `agentdev`

The image carries `agentdev` 6.0.0, a cross-agent plugin for Claude Code and
OpenCode. It covers:

- Git commits, branch updates, merges, and conflict resolution.
- Pull-request creation, synchronization, review, feedback resolution, and merging.
- GitHub Actions and CodeQL diagnostics.
- Formatting, linting, and semantic-refactor auditing.
- Agent and skill authoring.
- Docker-backed execution through the project devcontainer.

Skills use the `/agentdev:<name>` namespace, including `/agentdev:pr-open`,
`/agentdev:pr-review`, and `/agentdev:pr-merge`. See the
[catalog README](.agents/plugins/agentdev/README.md) for standalone installation
instructions and contributor guidance.

### `agentdev-iwe`

`agentdev-iwe` 1.0.0 is the complete IWE project-memory workflow described in
[IWE project memory](#iwe-project-memory). Its skills use the `/agentdev-iwe:<name>`
namespace, such as `/agentdev-iwe:iwe-plan`.

## IWE project memory

IWE stores product context, architecture, specifications, plans, and releases as
a Markdown knowledge graph. The `agentdev-iwe` plugin's `iwe-*` skills
provide a complete workflow over it.

Plan checkboxes carry traceable evidence, and behavior-changing plans state their
intended contract before implementation. Machine-managed dependency pins can be
masked from map freshness checks without hiding structural source changes.

Consumers adopting IWE receive a schema-valid seed without inheriting this
publisher repository's project knowledge.

## Pull-request automation

The optional `ai-responder.yml` workflow performs Claude-powered pull request reviews.
It runs only on pull request events; no comment starts it. Its merge gate stays pending
while review runs and requires an accepted AI review.

Security gates prevent the responder from checking out or executing untrusted fork
code and restrict reviews to pull request events from actors with write access. Reviews use the pull
request branch's own catalog, so changes to agent workflows are reviewed as changed.
To request another review after new work lands, add the `request-ai-review` label; the
workflow removes it when the review finishes. While the `block-ai-reviews` label is on, no
review runs, requested ones included; removing it runs a waiting request.

Reviews and trusted-bot approvals post as the `plume-works-quill` GitHub App, the only
reviewer the merge gate accepts. Consumers must register and install a GitHub App and
create the `plume-works-review` environment holding the `CLAUDE_CODE_OAUTH_TOKEN`,
`QUILL_APP_CLIENT_ID`, and `QUILL_APP_PRIVATE_KEY` secrets, and create the
`request-ai-review` and `block-ai-reviews` labels before enabling the workflow.

Pull-request descriptions record only closed checks, each with its evidence,
under `Verification`; an open check goes to the user, never into the
description. Repository-specific additions belong in
`.github/pr-description-guidance.md`.

## Validation and quality

`validate_agent_files` 1.0.0 validates agents, skills, prompts, plugin manifests,
marketplace metadata, references, and plugin layout. Repository discovery respects
`.gitignore`, while explicitly named files remain directly validatable.
`--recommend` enables warning-level guidance and `--errors-only` suppresses it.

Pre-commit is the single lint and formatting gate: CI runs the same hooks in the
pinned devcontainer image, alongside the validator suites, knowledge-base gates,
and image builds.

## Firewall and desktop

The firewall is installed but disabled by default. Enable it and edit the allowlist:

```jsonc
// .devcontainer/devcontainer.json
"containerEnv": { "ENABLE_FIREWALL": "true" }
```

Rules come from [`.devcontainer/firewall-allowlist.txt`](.devcontainer/firewall-allowlist.txt).
When enabled, the firewall default-denies IPv4 egress, blocks IPv6, preserves Docker
DNS, and verifies both an allowed and a blocked destination during startup.

The supplied devcontainer runs in privileged mode for nested Docker and optional
GPU access. Use it only with trusted repositories and container contents.

Xpra starts on display `:100` and container port `14500`. Open the **Xpra HTML5**
entry in VS Code's Ports panel to reach the desktop; concurrent worktrees receive
distinct local ports. Prefix graphical applications with `vglrun` for GPU
acceleration. `systemctl --user restart agentdev-xpra` restarts the desktop, and
`AGENTDEV_SKIP_XPRA=1` keeps it off.

## Build and contribute

Build the image from the repository root:

```bash
docker buildx build \
  -f docker/devcontainer/agentdev-devcontainer.Dockerfile \
  -t local/agentdev-devcontainer .
```

Install dependencies and run the primary repository checks:

```bash
uv sync --all-groups
uv run validate_agent_files --recommend . --require-marketplace claude
uv run pytest
```

The independently released validator must also pass outside the publisher project:

```bash
cd py_packages/validate_agent_files
uv run --isolated --extra dev pytest
```

The canonical plugin source is
[`.agents/plugins/agentdev/`](.agents/plugins/agentdev/). Repository
conventions live in [AGENTS.md](AGENTS.md).

## License

MIT — see [LICENSE](LICENSE).
