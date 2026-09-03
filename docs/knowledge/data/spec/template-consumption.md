---
type: spec
description: How a project adopts this repository as a template — the normative requirements, with the full setup and update procedure owned by the agentdev template-consume skill.
generated:
  by: codex/gpt-5
  at: 2026-09-03T19:50:54Z
sources:
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/65#discussion_r3794941822
---

# Template consumption

The procedure for adopting this repository's development environment and
conventions in another project is owned by the `agentdev` catalog's
`/agentdev:template-consume` skill, at
`.agents/plugins/agentdev/skills/template-consume/`. Its
`references/consumption-guide.md` is the single step-by-step guide — Workflow A
(full repository copy), Workflow B (existing repository), the optional
custom-image bundle, and verification — and its `SKILL.md` defines setup mode,
update mode, and the `.agentdev-template.json` marker file. Edit the guide, not
this document, when a step, a deleted-or-retained path, or a CI adaptation
changes. The skill ships in the plugin, so a consumer runs it from an installed
catalog without this repository checked out.

This document holds only the requirements the procedure must satisfy. Read
[Template boundary](../architecture/template-boundary.md) for the
keep/customize/optional/delete inventory the guide walks.

## Requirement: the finished project retains every runtime capability

The default setup SHALL retain every runtime capability the template's
devcontainer provides — the digest-pinned `agent-desktop` image,
Docker-in-Docker and Codespaces SSH, worktree-safe mounts, Xpra/VirtualGL, the
MCP gateway and secrets socket, persistent agent-state volumes with one shared
credentials volume, the image-staged `agentdev` catalog, keyring and GitHub
authentication, uv caching and pre-commit setup, and the opt-in egress firewall.
It SHALL NOT infer a language, create application code, choose dependencies, or
invent CI for the consuming project's product.

## Requirement: publisher-only source never survives adoption

A consumer SHALL delete `.agents/`, `.claude-plugin/`, `py_packages/`, and
`scripts/validate-super-linter-tool-versions.sh`, and SHALL adapt every CI
workflow, pre-commit hook, `pyproject.toml` entry, and path filter that
referenced them. Agent-file validation, when retained, SHALL run the validator
the digest-pinned image provides, never the deleted working-tree package.

## Requirement: `.ruff.toml` and `pyproject.toml` never both configure ruff

Ruff resolves the first configuration file it finds and silently ignores the
rest. A consumer SHALL keep exactly one of the template's `.ruff.toml` and a
`[tool.ruff]` table.

## Requirement: a linter hook is never added without its matching config, or vice versa

A `.clang-format` with no C++ is inert; a clang-format hook with no
`.clang-format` fails. Hooks and their configuration SHALL be adopted as pairs.

## Requirement: formatter adoption never rewrites verbatim third-party captures

Directories holding byte-exact third-party captures SHALL be excluded in
`.prettierignore` and ruff's `extend-exclude` before the formatters first run.

## Requirement: the AI review gate's trust is explicit

The `claude-respond` and `ai-review-present` jobs in `ai-responder.yml` SHALL be
kept or dropped together. The responder SHALL NOT auto-review any bot-authored
pull request; `ai-review-present` SHALL waive its requirement only for the bot
logins listed in `TRUSTED_BOT_ACTORS`, matched exactly and only when `user.type`
is `Bot`. The gate checks that the pull request has a review, not that its head
commit does — a copy comparing the review's `commit_id` to the head SHA is a
policy change. The fork gate and write-access gate SHALL be preserved as
written; the owner gate SHALL be repointed at the consumer. The
`workflow_dispatch` bridge SHALL be retained so default-branch comment events
can run the pull request head branch's workflow and attach checks to that head.

## Requirement: adoption is recorded for later updates

Setup SHALL write `.agentdev-template.json` at the consumer root recording the
full commit SHA of the template consumed, the workflow used, the optional
bundles kept, and the template paths still tracked. Update mode SHALL diff only
those paths from that SHA and SHALL NOT advance the SHA past what was actually
applied.
