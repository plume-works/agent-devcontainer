---
type: spec
description: The language and import rules for every script the agentdev catalog ships under bin/ and skills/*/agent-code/ — standard-library-only Python that reaches the shared bin/ modules through a path resolved from its own file, never a sibling skill's code, and bash_quote for every command line handed to a shell — with bin/macos-bootstrap.zsh the one exception.
sources:
- resource: .agents/plugins/agentdev/bin/python_lint_check.py
- resource: .agents/plugins/agentdev/bin/result_codes.py
- resource: .agents/plugins/agentdev/bin/skill_common.py
- resource: .agents/plugins/agentdev/bin/pr_restack_all.py
- resource: .agents/plugins/agentdev/skills/extract-github-actions-logs/agent-code/parse-actions-url.py
- resource: .agents/plugins/agentdev/skills/skill-scripts/SKILL.md
- resource: .agents/plugins/agentdev/bin/macos-bootstrap.zsh
- resource: .agents/AGENTS.md
- resource: .pre-commit-config.yaml
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .agents/plugins/agentdev/skills/create-skill/SKILL.md
---

# Catalog scripts

## Purpose

Defines what a script shipped by the agentdev catalog may be written in and may
depend on. The catalog runs from the plugin cache of any consuming repository,
on whatever host runs the agent, so its scripts depend on `python3` and the
tools they drive and on nothing installed for them. The `RESULT=` output
contract the scripts follow belongs to the `skill-scripts` skill.

## Requirements

### Requirement: catalog scripts are standard-library Python

Every script under the agentdev plugin's `bin/` and `skills/*/agent-code/`,
except `bin/macos-bootstrap.zsh`, SHALL be Python started by
`#!/usr/bin/env python3` and SHALL import only the standard library, the
plugin's shared `bin/` modules, and modules beside it in its own `agent-code/`.
It SHALL depend on nothing installed for it beyond `python3` and the external
tools it drives, such as `git` and `gh`.

#### Scenario: a script needs a third-party parser

- **WHEN** a script needs a capability only a third-party package offers
- **THEN** the script implements it on the standard library instead of importing
  the package
