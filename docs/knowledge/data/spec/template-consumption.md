---
type: spec
description: How a project adopts this repository as a template — the normative requirements, with the full setup and update procedure owned by the agentdev template-consume skill.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/agent-code/check-updates.py
- resource: https://github.com/plume-works/agent-devcontainer/pull/65#discussion_r3794941822
- resource: .devcontainer/devcontainer.json
- resource: https://github.com/plume-works/vscode-expo-bridge
- resource: docker/base/agentdev-base.Dockerfile
- resource: .dockerignore
- resource: .agents/plugins/agentdev/bin/skill_common.py
- resource: .agents/plugins/agentdev/bin/python_lint_check.py
- resource: py_packages/validate_agent_files/tests
- resource: ansible/roles/validate_agent_files/tasks/main.yml
---

# Template consumption

The procedure for adopting this repository's development environment and
conventions in another project is owned by the `agentdev` catalog's
`/agentdev:template-consume` skill, at
`.agents/plugins/agentdev/skills/template-consume/`. Its
`references/consumption-guide.md` is the single step-by-step guide — Workflow A
(full repository copy), Workflow B (existing repository), the optional
custom-image bundle, and verification — and its `SKILL.md` defines setup mode,
update mode, the `template-consume` section of `.agent.metadata.json`, and the
progress document. Edit the guide, not this document, when a step, a
deleted-or-retained path, or a CI adaptation changes. The skill ships in the
plugin, so a consumer runs it from an installed catalog without this repository
checked out.

This document holds only the requirements the procedure must satisfy; the
path-by-path inventory is the guide's.

## Requirement: publisher-only source never survives adoption

A consumer SHALL delete `.agents/`, `.claude-plugin/`, and `py_packages/`, and
SHALL adapt every CI workflow, pre-commit hook, `pyproject.toml` entry, and path
filter that referenced them. Agent-file validation, when retained, SHALL run the
validator the digest-pinned image provides, never the deleted working-tree
package. The consumption guide does not name each such reference: [Bug: the
consumption guide leaves references to deleted publisher
source](../bugs/consumption-guide-keeps-publisher-source-references.md).

## Requirement: every template path has one class

The guide SHALL classify every tracked path of the template as Template,
Customize, Optional, Publisher, or Generated. A consumer SHALL keep Template
paths, keep Customize paths and edit their project identity and owned paths,
keep an Optional path only together with the rest of its bundle, delete every
Publisher path, and never take a Generated path as template input. The root
`AGENTS.md` and `CLAUDE.md` and the `.claude/` directory SHALL survive the
deletion of publisher-only source. The guide names the five classes but gives no
path a class, and it does not name each tracked path: [Bug: the consumption
guide does not give each template path a
class](../bugs/consumption-guide-classifies-no-path.md).

### Scenario: a full copy deletes publisher-only source

- **WHEN** Workflow A deletes `.agents/`, `.claude-plugin/`, and `py_packages/`
- **THEN** the root `AGENTS.md`, `CLAUDE.md`, and `.claude/` remain, and the
  instructions scoped under the deleted trees leave with them

### Scenario: an existing repository receives the runtime unit

- **WHEN** Workflow B copies `.devcontainer/` and
  `devcontainer-compose-pins.yml`
- **THEN** the consumer's `.gitignore` ignores `.devcontainer/.env` and
  `.devcontainer/local.env` before the first container start, so the generated
  host state never reaches a commit
