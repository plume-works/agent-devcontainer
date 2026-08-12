---
type: tracker
description: What the product is, who it is for, and the decisions every plan and spec derives from.
stage: living
generated:
  by: human:author
  at: 2026-08-01T00:00:00Z
---

# Product

## What is it

A general-purpose, Ansible-provisioned devcontainer built for agent-driven
development, published as `ghcr.io/plume-works/agent-desktop`.

The repository has three responsibilities in one checkout: it publishes the
`agent-desktop` image (Python + Node, Docker-in-Docker, an Xpra remote desktop,
Claude Code and Codex preinstalled, an opt-in egress firewall), it publishes the
`agentdev` catalog of agents and skills for Claude Code and Codex, and it
carries reusable devcontainer scaffolding that other projects copy in (either by
pointing at the published image, or by copying the template surface — lifecycle
scripts, MCP config, GitHub workflows). A project adopting it gets a
digital-pinned, reproducible agent development environment without building its
own container tooling.

## Users

Two audiences, matching the repo's own dual role:

- **This repository's maintainers** — build and evolve the `agent-desktop`
  image, the `agentdev` catalog (Principal Engineer + TDD Red/Green/Refactor
  agents, 24+ skills), and the Ansible/Docker publishing pipeline itself.
- **Consuming-project developers** — point their own devcontainer at the
  published image, or copy the template surface into an existing repository, to
  get the same environment and agent catalog without building it themselves.

Built internal-first for plume-works' own projects: external reuse is welcome
and supported (the template/copy workflow exists deliberately), but it is not
the driver of design decisions — internal needs come first.

## Platforms

- **Distribution**: multi-arch (`linux/amd64` + `linux/arm64`) container images
  on GHCR — `ghcr.io/plume-works/agent-desktop:edge` and
  `ghcr.io/plume-works/ubuntu-ansible:edge` — pinned by tag *and* digest
  (`compose.pins.yml`), kept current by Renovate.
  - Consumed via VS Code / any `devcontainer.json`-compatible tool (Dev
    Containers spec), or GitHub Codespaces.
- **Host requirement**: a Docker daemon (Docker-in-Docker is provisioned inside
  the container itself for nested builds).
- **Base OS**: Ubuntu, provisioned with Ansible.
- **Deliberately not supported**: no non-container/bare-metal install path; the
  environment is only distributed as a container image plus copyable
  devcontainer scaffolding, not as a standalone installer.

## Stack

- **Languages**: Python (`uv`-managed, `requires-python >= 3.12`) and shell
  (bash, `set -euo pipefail`, shellcheck-clean) for tooling; Ansible YAML for
  provisioning; the devcontainer/catalog surfaces are JSON/YAML/Markdown.
- **Package/build tools**: `uv` for Python, `bun` for JavaScript — see
  `AGENTS.md` at the repository root. Never install packages globally.
- **Key entry points**:
  - `pyproject.toml` — root Python project (`agent-devcontainer`), dev
    dependency group only, `package = false`.
  - `py_packages/validate_agent_files/` — an independently-released Python
    package (its own `pyproject.toml`, isolated test suite) that validates
    agent/skill definitions.
  - `.agents/plugins/agentdev/` — the canonical source for the `agentdev` Claude
    Code / Codex plugin (agents, skills, hooks, `bin/` scripts); this directory
    is the source of truth, everything else under `.claude-plugin/`,
    `.agents/plugins/marketplace.json`, and the reinstall scripts is derived.
  - `ansible/playbooks/`, `ansible/roles/` — image provisioning.
  - `docker/desktop/agent-desktop.Dockerfile`, `docker/ansible/` — image build.
  - `.devcontainer/` — the devcontainer definition and lifecycle scripts
    (`postCreateCommand`, `postStartCommand`, firewall, Xpra startup).
- **Tests**: two independent pytest suites declared in `pyproject.toml`'s
  `testpaths` — `.agents/plugins/agentdev/tests/` (plugin script behavior, via a
  `plugin_root` fixture, not repo-relative paths) and `py_packages/` (the
  `validate_agent_files` package, must pass with no knowledge of this
  repository:
  `cd py_packages/validate_agent_files && uv run --isolated --extra dev pytest`).
  Run both from root with `uv run pytest`.
- **Lint/format**: ruff (Python, 99-char line limit per `.ruff.toml`, not 79),
  ansible-lint, shellcheck, clang-format, Prettier — orchestrated through
  Super-Linter locally (`agentdev:local-reformat`) and in CI
  (`.github/workflows/reformat.yml`); pre-commit hooks wire the same tools in
  locally.
- **CI**: GitHub Actions — `ci.yml` (image build/publish), `primary-checks.yml`,
  `validate-agent-files.yml`, `validate-knowledge-base.yml`, `reformat.yml`,
  `delete-old-containers.yml`.

## Constraints

- Images are pinned by tag **and** digest everywhere they're consumed
  (`compose.pins.yml`); moving off a pin is a deliberate Renovate-driven update,
  never a silent float.
- The staged `agentdev` catalog inside the image is root-owned and read-only;
  updating it requires rebuilding the image, not a runtime patch.
- `py_packages/validate_agent_files` must remain installable and testable with
  zero knowledge of this repository — it is released independently.
- The firewall (`init-firewall.sh`) ships inert by default (`ENABLE_FIREWALL`
  opt-in); when enabled it default-DROPs IPv4 egress and blocks IPv6 entirely,
  self-verifying at start.
- License: MIT.

No additional performance budgets, compatibility promises, or privacy/security
obligations beyond what's already encoded above — confirmed with the maintainer.

## Authoring rules

From `AGENTS.md` at the repository root (canonical; `CLAUDE.md` only includes
it):

- Never use `$TMPDIR`; always use `./.tmp` (relative to repo root), creating it
  if absent.
- Never use the GitHub API/MCP tools to update branch refs or push branch
  content — local git workflows only; stop and report if push auth is
  unavailable.
- Commit at meaningful checkpoints during a task, not only at the end.
- Never change git config (local or global) or switch/change the remote unless
  explicitly instructed.
- Use `uv` for Python and `bun` for JavaScript; run through `uv run`; never
  install globally.
- Scope test runs narrowly while iterating (`uv run pytest <path>::<test>`);
  full suite only when asked.
- If the local toolchain is missing, escalate — don't give up: Docker available
  → `/agentdev:microvm-sandbox`; no Docker →
  `/agentdev:remote-codespace-session` over SSH. Only report a blocker if both
  are unavailable.
- Prefer the structured-question tool (`AskUserQuestion` /
  `vscode/askQuestions`) for yes/no and multiple-choice questions over free
  text.
- Keep devcontainer-related scripts under `.devcontainer/scripts`.
- Edit `.agents/plugins/agentdev/` for catalog changes, never `.codex/`; Codex
  reads the canonical plugin tree directly.
- Consult the **Principal Engineer** agent for
  architecture/design/implementation strategy decisions ("When in Doubt").
- Python: PEP 8, 99-char line limit, type hints + PEP 257 docstrings, ruff for
  style (never stock flake8/black — their defaults don't match this repo), no
  empty `except: pass` handlers.
- Python testing: pytest only, never `unittest`; prefer several small focused
  test files; keep fixtures independent of repo identity when behavior is meant
  to generalize.
- Shell: `#!/usr/bin/env bash`, `set -euo pipefail`, shellcheck-clean, quote
  every expansion.
- Investigation/spike work gets documented directly in IWE project memory: an
  issue found during a spike → `data/bugs/<slug>.md`; a design decision the
  spike settles → `data/architecture/<slug>.md`; implementation guidance for
  follow-up → a plan or `data/backlog/<slug>.md` task. (The `agentdev` catalog's
  `implement-agent-specs` skill and its `docs/agents/specs/` convention still
  exist for consumers of that catalog who don't run IWE — not used in this
  repository.)
- This workspace uses IWE project memory under `docs/knowledge/data/` — query it
  before planning/implementing substantial work; update it when work changes
  durable project knowledge; follow `docs/knowledge/data/AGENTS.md` when editing
  it directly.

## Changelog

- 2026-08-01 — document created.
- 2026-08-12 — filled from codebase scan (README, AGENTS.md, pyproject.toml,
  repository-structure.md, CI workflows) via the setup skill.
- 2026-08-12 — folded `docs/agents/specs/`, `docs/repository-structure.md`, and
  `docs/using-as-template.md` into IWE (architecture, spec, and bug docs); the
  spike-documentation authoring rule now routes to IWE instead of
  `docs/agents/specs/`.
