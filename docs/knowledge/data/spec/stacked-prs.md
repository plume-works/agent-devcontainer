---
type: spec
description: How the PR skills merge pull requests explicitly and only into main, never rewrite a branch, record a dependent branch's predecessors, keep the Depends on section machine-editable, and restack a chain of dependent pull requests with merges through pr-restack-all.
sources:
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-restack-all/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py
- resource: .agents/plugins/agentdev/bin/pr_restack_all.py
- resource: .agents/plugins/agentdev/bin/depends_on.py
- resource: .agents/plugins/agentdev/bin/check_depends_on.py
- resource: AGENTS.md
---

# Stacked PRs

## Purpose

Defines how the PR skills merge and how work that depends on an open pull
request is stacked: every PR is merged explicitly, never through auto-merge, and
only into `main`; no branch is ever rewritten; a dependent pull request is a
normal pull request based on its predecessor's branch, and after a squash merge
its successors are reconnected with merges by one `pr-restack-all` run.

## Requirements

### Requirement: Merges into dependent branches are blocked

The repository SHALL have a ruleset on `refs/heads/iwe/**` requiring the status
check `base-is-main`, with the Write, Maintain, and Admin repository roles as
bypass actors, and no workflow SHALL report that check.

#### Scenario: Pull request into an iwe branch

- **WHEN** a pull request based on an `iwe/` branch is merged without `--admin`
- **THEN** GitHub refuses the merge

#### Scenario: Owner push

- **WHEN** a user with Write access pushes to an `iwe/` branch
- **THEN** the push is accepted
