---
type: spec
description: How the git-new-branch skill starts a work branch at the fetched remote base, and how git-commit and pre-commit keep commits off the default branch.
sources:
- resource: .agents/plugins/agentdev/skills/git-new-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py
- resource: .agents/plugins/agentdev/bin/git_default_branch.py
- resource: .agents/plugins/agentdev/skills/pr-open/agent-code/find-branch-pr.py
- resource: .agents/plugins/agentdev/skills/git-commit/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-commit/agent-code/git-commit.py
- resource: .pre-commit-config.yaml
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: compose.opencode.yml
---

# git-new-branch

## Purpose

Defines how work gets onto its own branch: created at the freshly fetched remote
base, tracking its own upstream, with uncommitted changes and stray
default-branch commits carried onto it, and never committed on the default
branch.

## Rationale

### The branch tracks its own upstream from creation

The branch is created with `--no-track` and pushed at once. A branch made with
`git switch -c X origin/main` tracks the base, so `git pull` pulls the base and
`pr-open`'s `find-branch-pr.py` refuses it as `PROTECTED_BRANCH`, since its
upstream is the default branch.

Rejected:

- **Pushing at the first commit.** The upstream stays unset in between, and
  `pr-open` has to finish the setup.

### Deploy worktrees live inside the checkout

The deploy image mounts only `/workspaces/project`, as a named volume or a host
bind. `/workspaces` itself is created root-owned by the image's `WORKDIR` and
lives in the container layer, so a worktree there would be unwritable for the
agent user and lost when the container is recreated. Deploy mode therefore puts
worktrees in the checkout's ignored `.worktrees/`.
