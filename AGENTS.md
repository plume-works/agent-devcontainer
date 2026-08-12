# Agents Guidelines

NEVER use "$TMPDIR" env variable.
ALWAYS use "./.tmp" (relative to the repo root) for temporary files; create it if it does not exist.
NEVER use GitHub API or GitHub MCP tools to update branch refs or push branch contents. Use local git branch workflows instead; if push authentication is unavailable, stop and report the blocker rather than updating the branch remotely via API.
Commit at checkpoints as meaningful progress is achieved, rather than accumulating a whole task into one commit at the end.

## Best Practices for Agents

0. NEVER change git config on local or global level unless explicitly instructed. NEVER switch/change remote.
1. **Use `uv` for Python and `bun` for JavaScript.** Run project commands through `uv run`; sync with `.devcontainer/scripts/uv-sync.sh` (or `uv sync`) after changing dependencies. Never install packages globally.
2. **Scope test runs narrowly** while iterating: `uv run pytest <path>::<test_name>`, `bun test <path>`. Run the full suite only when asked.
3. **Escalate to a container when the host lacks the toolchain — never give up after a local failure.** If `uv` or `bun` is missing, or a command needs the provisioned image, escalate in this order: (a) Docker daemon available → use the `/agentdev:microvm-sandbox` skill to run the command through `devcontainer exec`; (b) no Docker daemon → use the `/agentdev:remote-codespace-session` skill to run it on a GitHub Codespace over SSH. Only report a blocker if both escalation paths are unavailable (e.g. no `gh` auth).
4. **For yes/no and multiple-choice questions, prefer the assistant's structured-question tool** over free-text (VS Code Copilot: `vscode/askQuestions`; Claude Code: `AskUserQuestion`).
5. Keep devcontainer-related scripts in `.devcontainer/scripts`.

### When in Doubt

Consult the **Principal Engineer** agent supplied by the `agentdev` catalog for architecture,
design decisions, and implementation strategies.

## Coding Conventions

### Python

- Follow **PEP 8**: 4 spaces per indentation level, descriptive names. The line limit is **99** (`.ruff.toml`), not 79.
- Use type hints (PEP 484, `typing` module) and PEP 257 docstrings placed immediately after `def`/`class`
- Formatting and autofixes are applied by **ruff**, via the pre-commit hooks locally and Super-Linter in CI (`super-linter-local.sh`, from the plugin `bin/`, reproduces the CI pass). Verify with `python-lint-check.sh` for a fast, Docker-free check. Never judge style with stock `flake8` or `black`: their defaults (79-char limit, double quotes, different isort grouping) produce false positives that do not match this repo and do not fail CI. Full workflow in the `/agentdev:python-format-lint` skill
- **Exception handling**: never write empty handlers (`except ...: pass`). Handle expected exceptions explicitly by at least one of: logging context, returning a safe fallback value, re-raising with context, or raising `SystemExit` for CLI interruption paths (`raise SystemExit(130)` for user interrupts). If an exception must be intentionally ignored, document the reason in a comment and keep the ignored scope minimal. Prefer specific exception types over broad `except Exception`

### Python Testing

- **Always use `pytest`** — never `unittest`.
- Prefer multiple smaller, focused test files over large monolithic ones.
- Keep fixtures independent of repository identity when the behavior under test is meant to
  work in other repositories or installed packages.
- Import values that belong to the tested contract from the code under test instead of
  restating them as literals.

### Shell

- All scripts are `#!/usr/bin/env bash` with `set -euo pipefail`, and must pass `shellcheck` (enforced by pre-commit and Super-Linter)
- Quote every expansion; prefer `"${var:-default}"` over assuming a variable is set

### C++

- Follow the C++ Core Guidelines with modern C++ (C++17 or later): RAII for resource management, value semantics by default, smart pointers instead of raw pointers, standard library containers and algorithms
- Make ownership explicit in API design; focus on correctness first, then optimize with evidence
- Formatting is `clang-format` per [.clang-format](.clang-format)

**Edit `AGENTS.md`; `CLAUDE.md` only includes it (`@AGENTS.md`), so changes there cover all agents.**

## Project memory

This repository uses IWE project memory under `docs/knowledge/data/`.

For substantial feature, bug, architecture, or behavior work:

- query relevant project memory before planning or implementation;
- treat `docs/knowledge/data/` as the source of truth for project state and decisions;
- update project memory when the work changes durable project knowledge.

When modifying files under `docs/knowledge/data/`, follow `docs/knowledge/data/AGENTS.md`.

## Spikes

When doing investigation work aka spikes document your findings in specs under `docs/agents/specs/<spike-topic>` in a structured way, create new subfolder `<spike-topic>` for the subject of investigation. Create `README.md` with raw findings, including list of issues with assigned priorities. Create a series of spec files with implementation guidance.

## Other

Before calling any codebase-memory-mcp tools read `AGENTS-codebase-memory-mcp.md`
