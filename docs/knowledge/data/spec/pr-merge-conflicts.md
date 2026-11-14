---
type: spec
description: How pr-feedback-resolution and pr-merge detect a pull request's merge conflicts and resolve them through update-branch against the PR's own base branch.
sources:
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.py
---

# PR merge conflicts

## Purpose

Defines how the PR skills handle a pull request that conflicts with its base:
detected from GitHub's merge state, resolved before any feedback work by merging
the PR's own base branch, and pushed at once so CI runs on the resolved head.

## Rationale

### Conflicts are resolved and pushed before any feedback work

A pull request that conflicts with its base gets no `pull_request` workflow
runs, so its CI picture is missing or stale until the resolved merge is pushed.
That is why the conflict step runs before feedback work and why `pr-merge`
cannot wait on checks for a conflicted pull request. Resolving first also keeps
the working tree clean, which `update-branch` requires.

Rejected:

- **Pushing the merge together with the feedback fixes.** It saves one CI cycle
  but leaves CI blind while the feedback is worked.

### The conflict step merges the pull request's own base

The conflict step passes the pull request's `baseRefName`, not `update-branch`'s
`main` default, so a pull request based on a predecessor's branch merges its
real base. `update-branch` names a calling skill as a legitimate source of
`--remote` and `--base`, so the override is not read as unrequested. The step
keeps `update-branch`'s `origin` default, so a fork pull request whose base
branch lives on another remote is not handled.
