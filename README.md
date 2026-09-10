# agent-devcontainer

A reproducible, multi-architecture development environment built for agent-driven
software development.

`agent-devcontainer` combines a ready-to-use container image, a plugin catalog for
Claude Code and Codex, project-memory workflows, automated pull-request review,
validation tooling, and reusable scaffolding for adopting the environment in other
repositories.

## What you get

- Multi-architecture `linux/amd64` and `linux/arm64` images published through GHCR.
- Python development through `uv`, plus Bun and Node.js 24.
- Docker-in-Docker, Buildx, Compose, CMake, Ninja, Git LFS, and GitHub CLI.
- Claude Code and Codex preinstalled with the shared `agentdev` catalog.
- An optional `self-improve` plugin that turns verified corrections into reviewable
  instructions, published but not enabled by default.
- A browser-accessible Xpra desktop with VirtualGL support.
- An optional default-deny egress firewall with repository-controlled allowlisting.
- IWE knowledge-graph workflows from project setup through verified shipment.
- GitHub Actions for validation, formatting, image publishing, and AI review.
- A resumable template workflow for adopting or updating the environment elsewhere.

The repository publishes two images:

- `ghcr.io/plume-works/agent-desktop:edge` — the development environment.
- `ghcr.io/plume-works/ubuntu-ansible:edge` — its Ansible-ready base image.

Both are built on native runners and merged into multi-architecture manifests.

## Quick start

There are two supported adoption paths.

### Use the image

Point an existing devcontainer at the published image:

```jsonc
// .devcontainer/devcontainer.json
{
  "image": "ghcr.io/plume-works/agent-desktop:edge@sha256:b5175b7e5e9d2e7b99a67cbb3f25d37523fc0763800495ca613443f538b3eed8",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:4.1.0": {},
  },
  "containerEnv": {
    "DEV_WORKSPACE_FOLDER": "/workspaces/${localWorkspaceFolderBasename}",
  },
}
```

Pin by tag and digest so the environment never changes silently. Renovate or an
equivalent dependency updater can advance the digest when a new image is available;
this repository's [Renovate configuration](.github/renovate.json) provides a working
example.

### Adopt the complete template

Run `/agentdev:template-consume` to copy the complete setup or merge selected parts
into an existing repository. The workflow installs the devcontainer lifecycle,
agent settings, MCP configuration, project tooling, and adaptable GitHub workflows.
It also records the adopted revision so future runs can safely propose upstream
updates.

Template adoption is resumable, preserves settled choices, and never overwrites
consumer-authored IWE knowledge. See the
[template consumption guide](.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md)
for prerequisites and the full-copy and selective-copy workflows.

## Development environment

| Area          | Included tools and capabilities                                                      |
| ------------- | ------------------------------------------------------------------------------------ |
| Python        | `uv`, system Python, and `pre-commit`                                                |
| JavaScript    | Bun, Node.js 24, and Yarn                                                            |
| Agents        | Claude Code, Codex, MCP Inspector, and Codebase Memory MCP                           |
| Build tooling | `build-essential`, Kitware CMake, Ninja, and `pkg-config`                            |
| Quality       | Ruff, ShellCheck, Zizmor, Ansible Lint, Prettier, Hadolint, Gitleaks, and Actionlint |
| GitHub        | Git, Git LFS, `gh`, and a transparent host-token wrapper                             |
| Containers    | Docker CE, Buildx, and Compose                                                       |
| Desktop       | Xpra with its HTML5 client, VirtualGL, Mesa, and Xvfb                                |
| Credentials   | Headless GNOME Keyring and shared agent authentication                               |
| Security      | An opt-in egress firewall with an allowlist and startup checks                       |

Python commands run through `uv run`. Python environments, agent state, Codebase
Memory data, and pre-commit environments persist across container rebuilds and remain
isolated per worktree. Authentication is shared so opening another worktree does not
require signing in again.

## The plugin catalog

The repository is its own plugin marketplace. Claude Code sees two plugins,
`agentdev` and `self-improve`; Codex sees `agentdev` alone, because `self-improve`
ships no Codex manifest.

### `agentdev`

The image carries `agentdev` 3.3.0, a cross-agent plugin with 36 skills and five
agent definitions for Claude Code and Codex. It covers:

- Git commits, branch updates, merges, and conflict resolution.
- Pull-request creation, synchronization, review, feedback resolution, and merging.
- GitHub Actions and CodeQL diagnostics.
- Formatting, linting, and semantic-refactor auditing.
- Agent and skill authoring.
- Docker-backed execution and remote GitHub Codespace sessions.
- Template adoption and updates.
- The complete IWE project-memory workflow.

The catalog is installed during image construction. The devcontainer lifecycle
installs it again after persistent agent volumes mount and refreshes a repository's
workspace copy on editor attachment.

Skills use the `/agentdev:<name>` namespace, including `/agentdev:pr-open`,
`/agentdev:pr-review`, and `/agentdev:pr-merge`. See the
[catalog README](.agents/plugins/agentdev/README.md) for the complete skill list,
standalone installation instructions, and contributor guidance.

### `self-improve`

`self-improve` 0.1.0 is a hook-driven experiential-learning engine for Claude Code.
It captures turns, applies a deterministic gate to decide when a lesson is worth a
review, runs an isolated reviewer that holds no tools, and proposes edits to
`CLAUDE.md`, rules, and skills. Every mutation is authorized by the user against
exact bytes, targets a normative path allowlist, and is reversible. Its four skills
are `/self-improve:improve`, `apply`, `reject`, and `rollback`.

The plugin is published from the Claude marketplace and **not enabled** by anything
this repository ships: the tracked agent settings name it nowhere, and the Ansible
catalog role stages `agentdev` alone. Enable it deliberately, per session or per
project.

Its runtime is standard-library-only — a rule enforced by a test that walks every
runtime import — so the plugin adds no dependency to a consuming project. Tests
that drive a real Claude session and spend model usage are skipped at collection
unless `SELF_IMPROVE_RUN_LIVE` is set; the root `Makefile` carries those live
targets. Behavior is specified in
[the learning-loop spec](docs/knowledge/data/spec/self-improve-learning-loop.md),
and the comparative analysis behind it is in [`docs/research/`](docs/research/).

## IWE project memory

IWE stores product context, architecture, specifications, plans, releases, and a
source-backed codebase map as a Markdown knowledge graph. The catalog provides a
complete workflow:

| Skill                              | Purpose                                                               |
| ---------------------------------- | --------------------------------------------------------------------- |
| `iwe-setup`                        | Onboard an existing project and establish its product context.        |
| `iwe-map`                          | Create and refresh the codebase map.                                  |
| `iwe-explore`                      | Investigate ideas or GitHub issues without changing code.             |
| `iwe-plan`                         | Plan work with verified anchors and risk-scaled specification impact. |
| `iwe-implement`                    | Execute plans task by task and record evidence.                       |
| `iwe-verify`                       | Check implementation claims against code and specifications.          |
| `iwe-ship`                         | Block CRITICAL findings and record released behavior.                 |
| `iwe-weekly`                       | Summarize project status and graph health.                            |
| `iwe-audit`                        | Keep durable documents free of session residue.                       |
| `iwe-implement-all`/`iwe-ship-all` | Process all eligible plans in sequence.                               |

Plan checkboxes carry traceable evidence, and behavior-changing plans state their
intended contract before implementation. Machine-managed dependency pins can be
masked from map freshness checks without hiding structural source changes.

Consumers adopting IWE receive a schema-valid seed without inheriting this
publisher repository's project knowledge.

## Pull-request automation

The optional `ai-responder.yml` workflow performs Claude-powered reviews and handles
authorized `@claude` tasks. Its merge gate stays pending while review runs and
requires an accepted AI review.

Security gates prevent the responder from checking out or executing untrusted fork
code and restrict task execution to actors with write access. Reviews use the pull
request branch's own catalog, so changes to agent workflows are reviewed as changed.
Comment `@claude review` to request another review after new work lands.

Adopters must configure the `CLAUDE_CODE_OAUTH_TOKEN` repository secret and the
`claude-review` environment before enabling the workflow.

Pull-request descriptions separate completed `Verification` evidence from open
`Reviewer Handoff` tasks. Repository-specific additions belong in
`.github/pr-description-guidance.md`.

## Validation and quality

`validate_agent_files` 1.0.0 validates agents, skills, prompts, plugin manifests,
marketplace metadata, references, and plugin layout. Repository discovery respects
`.gitignore`, while explicitly named files remain directly validatable.
`--recommend` enables warning-level guidance and `--errors-only` suppresses it.

Pre-commit is the single local formatting path, and its environments persist across
container rebuilds. CI runs the matching Super-Linter checks, validator suites,
knowledge-base gates, and image builds.

## Firewall and desktop

The firewall is installed but disabled by default. Enable it and edit the allowlist:

```jsonc
// .devcontainer/devcontainer.json
"containerEnv": { "ENABLE_FIREWALL": "true" }
```

Rules come from [`.devcontainer/firewall-allowlist.txt`](.devcontainer/firewall-allowlist.txt).
When enabled, the firewall default-denies IPv4 egress, blocks IPv6, preserves Docker
DNS, and verifies both an allowed and a blocked destination during startup.

The supplied devcontainer runs in privileged mode for Docker-in-Docker and optional
GPU access. Use it only with trusted repositories and container contents.

Xpra starts on display `:100` and container port `14500`. Open the **Xpra HTML5**
entry in VS Code's Ports panel to reach the desktop; concurrent worktrees receive
distinct local ports. Prefix graphical applications with `vglrun` for GPU
acceleration. Advanced users can manage the service with
`/start-xpra.sh --background`, `--stop`, or `--port <n>`.

## Build and contribute

Build both images from the repository root:

```bash
docker build -t local/ubuntu-ansible docker/ansible

docker buildx build \
  -f docker/desktop/agent-desktop.Dockerfile \
  --build-arg FROM_IMAGE=local/ubuntu-ansible \
  -t local/agent-desktop .
```

Install dependencies and run the primary repository checks:

```bash
uv sync --all-groups
uv run validate_agent_files --recommend . --require-marketplace claude codex
uv run pytest
uv run ansible-lint ansible
uv run ansible-playbook --syntax-check ansible/playbooks/setup-dev.yml
```

The independently released validator must also pass outside the publisher project:

```bash
cd py_packages/validate_agent_files
uv run --isolated --extra dev pytest
```

The canonical plugin sources are
[`.agents/plugins/agentdev/`](.agents/plugins/agentdev/) and
[`.agents/plugins/self-improve/`](.agents/plugins/self-improve/). Repository
conventions live in [AGENTS.md](AGENTS.md), while the
[template boundary](docs/knowledge/data/architecture/template-boundary.md) classifies
the reusable, customizable, and publisher-only parts of the tree.

## License

MIT — see [LICENSE](LICENSE).
