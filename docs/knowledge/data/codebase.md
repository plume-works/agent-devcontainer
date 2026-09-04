---
type: hub
description: Codebase maps derived from the code, each pinned to the tracked-source fingerprint it was read from.
stage: living
generated:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:09:00Z
---

# 🧭 Codebase

*The map of the code as it actually is — written only by reading the code, never
from memory. The map mirrors the code's containment tree: one doc per component
(crate, package, module) at a canonical key matching its source path, children
linked from their parent's `## Contains` — so `iwe tree -k data/codebase`
renders the component tree. Every doc carries `source` (the code it describes),
`commit` (the git revision it was read at), and `verified` (the date); code
newer than `commit` means the doc is suspect — refresh it. Division of truth:
spec/ is what must be, architecture/ is why it's shaped this way, this hub is
what is.*

## Getting around

**Build.** The image: `docker build -t local/ubuntu-ansible docker/ansible`,
then
`docker buildx build -f docker/desktop/agent-desktop.Dockerfile --build-arg FROM_IMAGE=local/ubuntu-ansible -t local/agent-desktop .`
from the repository root. The Python environment: `uv sync --all-groups` (the
devcontainer runs `.devcontainer/scripts/uv-sync.sh` for you).

**Run.** Open the folder in a devcontainer, or
`devcontainer up --workspace-folder .`; the lifecycle hooks do the rest
([flow](codebase/flow-devcontainer-lifecycle.md)). Ansible alone:
`uv run ansible-playbook --syntax-check ansible/playbooks/setup-dev.yml`.

**Test.** `uv run pytest` runs the three suites `pyproject.toml` lists
(`.agents/plugins/agentdev/tests`, `docs/knowledge/tests`, `py_packages`);
`uv run validate_agent_files --recommend . --require-marketplace claude codex`
validates the catalog; `uv run pre-commit run --all-files` mirrors CI's
formatters; `super-linter-local.sh` runs the full Super-Linter pass;
`iwe schema validate` gates this workspace.

**Entry points.** `.devcontainer/devcontainer.json` (the container),
`docker/desktop/agent-desktop.Dockerfile` (the image),
`ansible/playbooks/setup-dev.yml` (provisioning),
`.github/workflows/primary-checks.yml` (CI), the `validate_agent_files` console
script, `/agentdev:<skill>` (the catalog), and `.codex/setup-codex-cloud.sh`
(Codex Cloud bootstrap).

| Path                                                                                                                                                                                          | Component                                                                                         |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `ansible/`, `ansible.cfg`                                                                                                                                                                     | [Image provisioning](codebase/ansible.md)                                                         |
| `docker/`                                                                                                                                                                                     | [Image build](codebase/docker.md)                                                                 |
| `.devcontainer/`, `devcontainer-compose-pins.yml`                                                                                                                                             | [Devcontainer scaffolding](codebase/devcontainer.md)                                              |
| `.agents/plugins/agentdev/`, `.agents/plugins/marketplace.json`, `.claude-plugin/`                                                                                                            | [The agentdev catalog](codebase/agents/plugins/agentdev.md)                                       |
| `py_packages/validate_agent_files/`                                                                                                                                                           | [validate_agent_files package](codebase/py_packages/validate_agent_files.md)                      |
| `.github/`                                                                                                                                                                                    | [GitHub automation](codebase/github.md)                                                           |
| `.iwe/`, `docs/knowledge/`                                                                                                                                                                    | [Knowledge workspace machinery](codebase/docs/knowledge.md) — the `data/` inside it is this graph |
| `scripts/validate-super-linter-tool-versions.sh`                                                                                                                                              | checks pre-commit and local tool versions against the pinned Super-Linter image; no doc           |
| `.codex/`, `.claude/`, `.mcp.json`, `.vscode/`                                                                                                                                                | project-local agent and editor configuration, not the catalog; no doc                             |
| `README.md`, `AGENTS.md`, `CLAUDE.md`, `AGENTS-codebase-memory-mcp.md`, `LICENSE`                                                                                                             | the human and agent entry documents; `CLAUDE.md` only includes `AGENTS.md`                        |
| `pyproject.toml`, `uv.lock`, `.ruff.toml`                                                                                                                                                     | the uv project and Python style                                                                   |
| `.pre-commit-config.yaml`, `.ansible-lint.yml`, `.clang-format`, `.editorconfig`, `.hadolint.yaml`, `.markdownlint.yml`, `.prettierrc.yml`, `.prettierignore`, `.shellcheckrc`, `zizmor.yaml` | formatter and linter configuration, kept in sync with Super-Linter                                |
| `.dockerignore`, `.gitignore`                                                                                                                                                                 | build-context and checkout hygiene                                                                |
| `py_packages/LICENSE`                                                                                                                                                                         | the package license copied into the wheel                                                         |

## Components

[Image provisioning (Ansible)](codebase/ansible.md)

[Image build (Docker)](codebase/docker.md)

[Devcontainer scaffolding](codebase/devcontainer.md)

[The agentdev catalog](codebase/agents/plugins/agentdev.md)

[validate_agent_files package](codebase/py_packages/validate_agent_files.md)

[GitHub automation](codebase/github.md)

[Knowledge workspace machinery](codebase/docs/knowledge.md)

## Flows

[Flow: image build](codebase/flow-image-build.md)

[Flow: devcontainer lifecycle](codebase/flow-devcontainer-lifecycle.md)

[Flow: pull request checks](codebase/flow-pull-request-checks.md)

## Interfaces

*External surfaces — HTTP APIs, CLI commands, storage formats, IPC contracts —
one doc each, keyed `api-<name>`.*

[Interface: image runtime contract](codebase/api-image-runtime.md)

[Interface: validate_agent_files CLI](codebase/api-validate-agent-files-cli.md)
