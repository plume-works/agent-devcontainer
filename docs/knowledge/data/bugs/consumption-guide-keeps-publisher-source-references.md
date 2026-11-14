---
type: bug
description: After a full-copy adoption that follows the consumption guide, pyproject.toml and the agent-file validation workflow still reference the deleted agentdev_runtime package, self-improve tests, and scripts/tests.
stage: pending
severity: medium
sources:
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: pyproject.toml
- resource: .github/workflows/validate-agent-files.yml
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: the consumption guide leaves references to deleted publisher source

## Symptom

Publisher-only source must not stay after adoption: each CI workflow, hook,
`pyproject.toml` entry, and path filter that refers to a deleted tree must be
adapted. The guide removes only the `validate_agent_files` entries. A consumer
who follows it keeps entries that name trees the guide told them to delete, and
`uv sync` or CI fails.

## Reproduction

1. Follow
   `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#workflow-a-start-from-a-full-repository-copy`
   in a copy of this repository.
2. After step 4, `pyproject.toml#dependency-groups.dev` still holds
   `agentdev_runtime`, and `pyproject.toml#tool.uv.sources.agentdev_runtime`
   still exists.
3. `pyproject.toml#tool.pytest.ini_options.testpaths` still holds
   `.agents/plugins/self-improve/tests` and `scripts/tests`.
4. `.github/workflows/validate-agent-files.yml#jobs.macos-bootstrap` and its
   self-improve and `bun` steps stay.

## Root cause

`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#4-adapt-the-uv-project`
names only `validate_agent_files`, `pydantic`, `python-frontmatter`, and two
`testpaths` entries.
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#agent-file-validation`
does not name the `macos-bootstrap` job. The guide did not change when the
template tree got these entries.
