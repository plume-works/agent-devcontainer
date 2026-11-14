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

## Rationale

### Dependent work is stacked with merges only

Work that depends on an open pull request is an ordinary pull request based on
its predecessor's branch, so its diff is its own work only, and no branch is
ever rewritten: every update is a merge and every push is a plain push. After a
squash merge the successor still holds the predecessor's original commits, so it
is reconnected by merging the squash commit into a detached copy of the
predecessor's final head and merging that copy in; the copy carries `main`
exactly up to the squash commit, and catching up with later `main` stays a
separate update-branch run. The reconnect is a normal `git merge`, so git
reports a conflict instead of hiding one. One restack from one detached worktree
built from remote refs moves no local branch, so another session whose branch it
advanced sees an ordinary non-fast-forward rejection and merges.

Merges into `iwe/` branches are blocked by a ruleset requiring a status check
nothing reports, with repository roles as bypass actors. A ruleset bypass list
accepts only repository roles and GitHub Apps owned by the repository or its
organization, not the built-in GitHub Actions app that `GITHUB_TOKEN` acts as,
so a workflow pushing to an `iwe/` branch must push as an owned App the ruleset
exempts.

Only branches of the remote are cut from or restacked, so a pull request whose
head lives in a fork is refused: its head names a branch that the remote may
also hold under the same name.

Rejected:

- **GitHub native stacks driven by `gh stack`.** GitHub rebases every remaining
  layer on the server after a lower layer merges, and `gh stack rebase` rewrites
  them again locally before a force-push; a lease protects remote-only commits,
  not the consumers of a rewritten branch, and every local copy goes stale.
- **Every pull request targets `main`.** Its diff includes every predecessor
  until they merge.
- **Resolving the reconnect merge with `-s ours`.** Correct by construction but
  silent; a normal merge lets git report a conflict.
- **Owners restacking their own pull requests, or a coordinator pausing its
  sessions.** More coordination than one restack from a detached worktree.
- **A required `base-is-main` check without bypass.** It also rejects the
  owners' own pushes and branch creation.
