---
type: bug
stage: done
severity: medium
description: git-new-branch chose its worktree fallback on AGENTDEV_RUNTIME_MODE=standalone, a value no image sets, so a deploy runtime defaulted to the root-owned /workspaces, and a non-root Dev Container would too.
sources:
- resource: .agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py
- resource: .agents/plugins/agentdev/tests/test_git_new_branch.py
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
---

# Bug: git-new-branch worktree fallback checks a runtime mode no image sets

## Symptom

In a deploy container with its checkout at `/workspaces/project`,
`git-new-branch --worktree` targets `/workspaces`, which is root-owned, so the
worktree cannot be created by the runtime account. This is the failure [Bug:
git-new-branch worktree mode fails on a standalone deployment's root-owned
/workspaces](../../2.0.0/bugs/git-new-branch-worktree-unwritable-workspaces.md)
set out to remove.

## Reproduction

Call `worktree_parent('/workspaces/project', 'deploy', '')`. It returns
`/workspaces`, not `/workspaces/project/.worktrees`.

## Root cause

`worktree_parent` compared the mode with `standalone`. The deploy image sets
`AGENTDEV_RUNTIME_MODE=deploy`, the Dev Container image sets `devcontainer`, and
the bootstrap refuses any other value, so the comparison never matched in an
image. The tests passed `standalone` directly, so they did not show it.

The fallback also depended on the mode alone, so a non-root Dev Container, which
cannot write `/workspaces` either, had no fallback.

## Fix

`worktree_parent` keeps `.worktrees/` under `AGENTDEV_RUNTIME_MODE=deploy`, and
uses `/workspaces` only when the account can write it. The tests pass the value
the deploy image sets.
