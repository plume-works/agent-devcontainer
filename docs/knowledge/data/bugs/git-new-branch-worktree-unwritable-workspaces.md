---
type: bug
description: In a standalone agent-opencode deployment, git-new-branch --worktree defaults the worktree parent to /workspaces, which is root-owned and outside every persistent mount, so the worktree cannot be created and would not persist if it could.
generated:
  by: claude-code/opus-5
  at: 2026-10-25T16:42:02Z
sources:
- resource: .agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.sh
- resource: .agents/plugins/agentdev/tests/test_git_new_branch.py
- resource: docker/opencode/agent-opencode.Dockerfile
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: compose.opencode.yml
- resource: compose.opencode.bind.yml
---

# Bug: git-new-branch worktree mode fails on a standalone deployment's root-owned /workspaces

## Symptom

In a standalone agent-opencode container (`AGENTDEV_RUNTIME_MODE=standalone`),
`git-new-branch.sh --worktree <name>` exits `RESULT=CREATE_FAILED` with
`fatal: could not create leading directories of '/workspaces/project-<name>/.git': Permission denied`.
The branch is rolled back and nothing is created. Passing
`--worktree-root /workspaces/project/.worktrees` succeeds.

## Reproduction

1. Start the standalone image with its default checkout at
   `/workspaces/project`, running as the default agent user `1000:1000`.
2. From the checkout, run
   `.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.sh --worktree some-branch`.
3. The fetch succeeds, `git worktree add` fails with `Permission denied`, and
   the script prints `RESULT=CREATE_FAILED`.

`/workspaces` is `root:root 0755` there. The test that covers the `/workspaces`
default skips itself when the directory is not writable, so the suite does not
catch this.

## Root cause

The script picks the parent from the checkout's path alone: a main checkout
whose parent is `/workspaces` gets its worktree in `/workspaces`, with no check
that the directory is writable or persistent. The standalone image mounts only
`/workspaces/project`, as a named volume or a host bind. `/workspaces` itself is
created by the image's `WORKDIR` as root-owned and lives in the container layer.
So the agent user cannot write there, and a worktree created there would be lost
when the container is recreated.

## Fix

Not fixed. When worktree mode would default to `/workspaces`, it needs a
writable, persistent parent. Two candidates: fall back to
`<checkout>/.worktrees/` when `/workspaces` is not writable, or always use
`.worktrees/` in standalone mode. The `git-new-branch` spec's worktree
requirement changes with either. Workaround: pass
`--worktree-root <checkout>/.worktrees`.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.sh:211`
  — worktree parent default chosen by `dirname` alone
- `.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.sh:229`
  — `git worktree add`, which fails and triggers `CREATE_FAILED`
- `.agents/plugins/agentdev/tests/test_git_new_branch.py:581` — `skipif` on an
  unwritable `/workspaces` for
  `test_worktree_mode_under_workspaces_defaults_to_a_sibling`
- `docker/desktop/agent-desktop.Dockerfile:82` — `WORKDIR $WORKSPACE_FOLDER`
  creates root-owned `/workspaces`
- `docker/opencode/agent-opencode.Dockerfile:57` — `WORKDIR /workspaces/project`
- `compose.opencode.yml:44` — only `/workspaces/project` is a volume
- `compose.opencode.bind.yml:9` — the bind variant mounts the same single path
- [git-new-branch spec](../spec/git-new-branch.md) — the worktree-mode
  requirement that names `/workspaces` as the parent
