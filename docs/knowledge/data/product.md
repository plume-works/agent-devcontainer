---
type: tracker
description: What the product is, who it is for, and the decisions every plan and spec derives from.
stage: living
---

# Product

## What is it

A general-purpose devcontainer built for agent-driven development, published as
`ghcr.io/plume-works/agentdev-devcontainer` and built on
`ghcr.io/plume-works/devcontainer-base`.

The repository has three responsibilities in one checkout: it publishes the
`agentdev-devcontainer` image (the base image's toolchain, nested Docker, and
Claude Code and OpenCode, plus an Xpra remote desktop, Playwright, the staged
catalog, an opt-in egress firewall, and the lifecycle commands), it publishes
the `agentdev` catalog of agents and skills for Claude Code and OpenCode, and it
carries the devcontainer descriptor this repository develops in. Other projects
point a descriptor at `agentdev-devcontainer` or derive their own image from it;
the lifecycle implementation always comes from the image. A project adopting it
gets a digest-pinned, reproducible agent development environment without
building its own container tooling.

## Users

Two audiences, matching the repo's own dual role:

- **This repository's maintainers** — build and evolve the image, the `agentdev`
  catalog (agents and skills), and the image publishing pipeline itself.
- **Consuming-project developers** — point their own devcontainer at the
  published image, or derive an image from it, to get the same environment and
  agent catalog without building it themselves.

Built internal-first for plume-works' own projects: external reuse is welcome
and supported, but it is not the driver of design decisions — internal needs
come first.

## Platforms

- **Distribution**: one multi-arch (`linux/amd64` + `linux/arm64`) image on
  GHCR, `agentdev-devcontainer`, pinned by tag *and* digest
  (`devcontainer-compose-pins.yml`) and kept current by Renovate. Its base,
  `ghcr.io/plume-works/devcontainer-base`, is pinned by tag and digest in
  `docker/devcontainer/agentdev-devcontainer.Dockerfile`.
  - Consumed via VS Code / any `devcontainer.json`-compatible tool (Dev
    Containers spec), in privileged mode.
- **Host requirement**: a Docker daemon that can run a privileged container: the
  image runs systemd as PID 1 and its own nested Docker engine.
- **Base OS**: Ubuntu 26.04, with apt pinned to the base image's dated archive
  snapshot.
- **Deliberately not supported**: GitHub Codespaces; a standalone runtime that
  serves an agent without an editor (plume-works' Coder template image fills
  that role); a non-container/bare-metal install path.

## Stack

- **Languages**: Python (`uv`-managed, `requires-python >= 3.12`) and shell
  (bash, `set -euo pipefail`, shellcheck-clean) for tooling; one plain
  Dockerfile and systemd units for the image; the devcontainer/catalog surfaces
  are JSON/YAML/Markdown.
- **Package/build tools**: `uv` for Python, `bun` for JavaScript — see
  `AGENTS.md` at the repository root. Never install packages globally. The image
  carries no Node.js.
- **Key entry points**:
  - `pyproject.toml` — root Python project (`agent-devcontainer`), dev
    dependency group only, `package = false`.
  - `py_packages/validate_agent_files/` — an independently-released Python
    package (its own `pyproject.toml`, isolated test suite) that validates agent
    and skill rulebooks.
  - `.agents/plugins/agentdev/` — the canonical source for the `agentdev`
    catalog for Claude Code and OpenCode (agents, skills, `bin/` scripts); this
    directory is the source of truth, everything else under `.claude-plugin/`
    and the reinstall scripts is derived.
  - `docker/devcontainer/` — the image build: its Dockerfile, the systemd units
    under `systemd/`, and `pinned-tools.yml`, the checksum-pinned release tools
    that `scripts/fetch-pinned-tool.py` installs.
  - `.devcontainer/` — the devcontainer descriptor and the firewall allowlist.
  - `py_packages/agentdev_runtime/` — the `agentdev-runtime` CLI the image
    installs as a uv tool: the root bootstrap, the health probes, the lifecycle
    commands, the firewall, and Xpra. systemd supervises the services.
- **Tests**: pytest suites declared in `pyproject.toml`'s `testpaths` —
  `.agents/plugins/agentdev/tests/` (catalog script behavior, via a
  `plugin_root` fixture, not repo-relative paths), `docs/knowledge/tests/`,
  `py_packages/` (including `validate_agent_files`, which must pass with no
  knowledge of this repository:
  `cd py_packages/validate_agent_files && uv run --isolated --extra dev pytest`),
  and `scripts/tests/`. Run them from root with `uv run pytest`.
- **Lint/format**: ruff (Python, 99-char line limit per `.ruff.toml`, not 79),
  hadolint, shellcheck, clang-format, Prettier — applied locally by the
  pre-commit hooks that run on every commit, and gated in CI by the same hooks
  in the `pre-commit` job of `primary-checks.yml`.
- **CI**: GitHub Actions — `ci.yml` (image build, acceptance, and publish),
  `primary-checks.yml`, `validate-agent-files.yml`,
  `validate-knowledge-base.yml`, `validate-renovate-config.yml`, `renovate.yml`,
  `ai-responder.yml`, `delete-old-containers.yml`.

## Constraints

- Images are pinned by tag **and** digest everywhere they're consumed
  (`devcontainer-compose-pins.yml`, the image's `FROM`); moving off a pin is a
  deliberate Renovate-driven update, never a silent float.
- The staged `agentdev` catalog inside the image is root-owned and read-only;
  updating it requires rebuilding the image, not a runtime patch.
- `py_packages/validate_agent_files` must remain installable and testable with
  zero knowledge of this repository — it is released independently.
- `agentdev-runtime firewall apply`, run as root by the root bootstrap before
  the nested Docker engine starts, is inert by default (`ENABLE_FIREWALL`
  opt-in); when enabled, it default-DROPs IPv4 egress and blocks IPv6 entirely,
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
- Never force-push. Never use `gh stack` or GitHub native stacked pull requests;
  work that depends on an open pull request is a normal pull request based on
  its predecessor's branch and kept current with merges.
- Never rebase or reset a branch that has been pushed; bring in other history
  with a merge.
- Never change git config (local or global) or switch/change the remote unless
  explicitly instructed.
- Use `uv` for Python and `bun` for JavaScript; run through `uv run`; never
  install globally. JavaScript runs through `bun`/`bunx` everywhere — never
  `npm`, `npx`, `yarn`, or `pnpm`.
- Scope test runs narrowly while iterating (`uv run pytest <path>::<test>`);
  full suite only when asked.
- If the local toolchain is missing, escalate — don't give up: Docker available
  → `/agentdev:devcontainer-sandbox`. Only report a blocker when no Docker
  daemon is available.
- Ask questions in prose, and then stop. Do not use a structured-question tool
  (`AskUserQuestion` / `vscode/askQuestions`): it does not show the text that
  comes before the question.
- Keep devcontainer runtime code in the `agentdev_runtime` package
  (`py_packages/agentdev_runtime/`).
- OpenCode tests default to `openai/gpt-6.1-sol` (big model) and
  `openai/gpt-6-luna` (small model); a costlier model only when the user names
  it.
- Consult the **Principal Engineer** agent for
  architecture/design/implementation strategy decisions ("When in Doubt").
- Python: PEP 8, 99-char line limit, type hints + PEP 257 docstrings, ruff for
  style (never stock flake8/black — their defaults don't match this repo), no
  empty `except: pass` handlers.
- Python testing: pytest only, never `unittest`; prefer several small focused
  test files; keep fixtures independent of repo identity when behavior is meant
  to generalize.
- NEVER WRITE AN END-TO-END TEST THAT DRIVES AN AGENT SESSION through the
  agentdev workflow skills against a live model; behaviour only such a session
  can show is an observation task in its plan.
- Shell: `#!/usr/bin/env bash`, `set -euo pipefail`, shellcheck-clean, quote
  every expansion.
- Record investigation and spike work in IWE project memory, in the document
  type that `docs/knowledge/SCHEMA.md#what-goes-where` names.
- This workspace uses IWE project memory under `docs/knowledge/data/` — query it
  before planning/implementing substantial work; update it when work changes
  durable project knowledge; follow `docs/knowledge/AGENTS.md` when editing it
  directly.
