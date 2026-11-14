---
type: bug
description: On a detached HEAD the git-commit script refuses with PREFLIGHT_ERROR, and the skill only reports the error, so the skill does not send the user to git-new-branch.
stage: pending
severity: low
sources:
- resource: .agents/plugins/agentdev/skills/git-commit/agent-code/git-commit.py
- resource: .agents/plugins/agentdev/skills/git-commit/SKILL.md
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: the git-commit skill's detached-`HEAD` refusal names no skill

## Symptom

Each refusal of the git-commit skill to commit off a work branch, a detached
`HEAD` included, must send the user to `/agentdev:git-new-branch`. On a detached
`HEAD`, the skill reports "HEAD is detached; commit on a feature branch
instead." and names no skill.

## Reproduction

1. `git checkout --detach`.
2. Run the git-commit skill.
3. The script exits with `PREFLIGHT_ERROR`, and the report does not name
   `/agentdev:git-new-branch`.

## Root cause

`.agents/plugins/agentdev/skills/git-commit/agent-code/git-commit.py::run`
answers a detached `HEAD` with `PREFLIGHT_ERROR`, and the message names no
skill. The `PREFLIGHT_ERROR` row in
`.agents/plugins/agentdev/skills/git-commit/SKILL.md#create-the-commit-through-the-script`
says "Report the error verbatim". Only the `PROTECTED_BRANCH` row names
`/agentdev:git-new-branch`.
