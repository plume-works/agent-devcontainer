---
type: spec
description: The pre-commit hooks are the CI lint gate and each hook tool has one version owner — the commit range they check, when every file is checked, and how gitleaks scans a range.
sources:
- resource: .github/workflows/primary-checks.yml
- resource: .github/workflows/ci.yml
- resource: scripts/pre-commit-ci-range.py
- resource: ansible/roles/nodejs/tasks/main.yml
- resource: scripts/ci_runs.py
- resource: .pre-commit-config.yaml
- resource: devcontainer-compose-pins.yml
- resource: scripts/check-ship-records.py
- resource: scripts/tests/test_check_ship_records.py
- resource: .iwe/schemas/bug.yaml
- resource: pyproject.toml
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: .github/renovate.json
- resource: ansible/roles/nodejs/tasks/main.yml
- resource: Makefile
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: .devcontainer/devcontainer.json
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/agents/principal-engineer.agent.md
- resource: .agents/plugins/agentdev/bin/python_lint_check.py
---

# pre-commit gate

## Requirements

### Requirement: every commit path runs the hooks, merges included

`agentdev-runtime project hooks` SHALL install the `pre-commit`, `pre-push`, and
`pre-merge-commit` hook types, and `.pre-commit-config.yaml`'s `default_stages`
SHALL include `pre-merge-commit`, so a merge commit runs the same hooks as an
ordinary commit. `end-of-file-fixer` and `trailing-whitespace` set their own
`stages` without `pre-merge-commit`, so a merge that commits on its own skips
them: [Bug: a merge commit skips `end-of-file-fixer` and
`trailing-whitespace`](../bugs/merge-commit-skips-two-hooks.md).

#### Scenario: a merge commits on its own

- **WHEN** `git merge` completes without conflicts and creates a merge commit
- **THEN** the `pre-merge-commit` hook runs the hooks on the merged files before
  the commit is written

#### Scenario: a conflicted merge is concluded

- **WHEN** a conflicted merge is resolved and concluded with `git commit`
- **THEN** the `pre-commit` hook runs the hooks

#### Scenario: a hook rewrites a staged file

- **WHEN** a formatter hook rewrites a file in the commit
- **THEN** the commit stops, and succeeds once the rewritten file is staged and
  the commit retried
