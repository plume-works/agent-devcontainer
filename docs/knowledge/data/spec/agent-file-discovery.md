---
type: spec
description: validate_agent_files directory discovery uses git ignore rules inside work trees and caller-supplied directory pruning outside work trees, and agent tooling reads its own namespaced key from `.agent.metadata.json` files.
sources:
- resource: py_packages/validate_agent_files/validate_agent_files/loaders.py
- resource: py_packages/validate_agent_files/tests/test_gitignore_discovery.py
- resource: .agents/plugins/agentdev/skills/template-consume/agent-code/check-updates.py
- resource: .agents/plugins/agentdev/tests/test_template_consume_check_updates.py
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: py_packages/validate_agent_files/validate_agent_files/validators/bundled_markdown.py
- resource: py_packages/validate_agent_files/validate_agent_files/core.py
- resource: py_packages/validate_agent_files/validate_agent_files/main.py
- resource: py_packages/validate_agent_files/validate_agent_files/cli.py
---

# Agent file discovery

## Purpose

`validate_agent_files` discovers skill, agent, and prompt markdown files from
either explicit file paths or directory walks. Directory discovery must avoid
validating generated, vendored, or scratch files that the repository has already
excluded from ownership, while still working in plain directories that have no
git ignore rules.

Agent tooling also finds per-directory metadata in `.agent.metadata.json` files,
each a JSON object whose top-level keys belong to one consumer apiece.

## Requirements

### Requirement: Git failures do not abort discovery

Discovery SHALL continue when git is unavailable, reports that a root is not
inside a work tree, or cannot classify ignore status for candidate paths. A
failure to identify a work tree SHALL use plain-directory discovery; a failure
while classifying candidates inside an identified work tree SHALL treat those
candidates as not ignored.

#### Scenario: Git cannot classify ignored candidates

- **WHEN** ignore classification fails for candidate directories or files inside
  an identified work tree
- **THEN** discovery keeps those candidates and continues
