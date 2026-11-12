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

### Requirement: pr-merge merges explicitly

The pr-merge skill SHALL NOT enable auto-merge. It SHALL disable an existing
auto-merge request when it starts and SHALL merge with a squash only after
conflicts, checks, AI review, and review feedback are resolved for the current
head SHA.

#### Scenario: Auto-merge already enabled

- **WHEN** pr-merge starts on a PR whose `autoMergeRequest` is non-null
- **THEN** it disables auto-merge before monitoring
- **AND** reports that it did so

#### Scenario: Requirements met

- **WHEN** every completion criterion holds for the current head SHA
- **THEN** pr-merge squash merges the PR explicitly and confirms `MERGED`

### Requirement: No branch is rewritten

Agent skills SHALL NOT force-push, SHALL NOT rebase or reset a branch that has
been pushed, SHALL NOT run `gh stack`, and SHALL NOT create a GitHub native
stack. Another branch's history SHALL be brought in with a merge.

#### Scenario: Remote moved

- **WHEN** a skill's push is rejected as non-fast-forward
- **THEN** it merges the remote branch and pushes again without force

### Requirement: A dependent branch records its predecessors

`git-new-branch --depends-on <P>`, repeatable, SHALL require every named pull
request to be open and its head to be a branch of the remote, SHALL cut the
branch from the first one's head branch and merge the others' heads, SHALL add
an empty commit with a `Depends-on: #<P>` trailer for each, and SHALL push.

#### Scenario: Predecessor without an open pull request

- **WHEN** a named pull request is not open
- **THEN** it stops before creating a branch

#### Scenario: Predecessor in a fork

- **WHEN** a named pull request's head is in a fork
- **THEN** it stops before creating a branch

### Requirement: pr-open bases a dependent pull request on its predecessor

For a branch with `Depends-on:` trailers, pr-open SHALL run
`pr-restack-all <branch>` before creating or updating the pull request, SHALL
refuse while more than one dependency is unmerged, SHALL set a new pull
request's base to the unmerged predecessor's head branch, or `main` when none is
unmerged, SHALL write its first `## Depends on` section with one `- #<P>` entry
per dependency in merge order, and SHALL open the pull request ready for review
unless the user asks for a draft.

#### Scenario: Two unmerged dependencies

- **WHEN** a branch depends on two unmerged pull requests
- **THEN** pr-open refuses and creates nothing

### Requirement: The Depends on section stays machine-editable

pr-gen-description and pr-open SHALL write the `## Depends on` section only when
the pull request is created and SHALL keep it byte-for-byte when a body is
regenerated. Before a body is applied they SHALL check it with the parser
`pr-restack-all` uses, and SHALL NOT apply a body whose section that parser
cannot find or edit.

#### Scenario: Regenerated body

- **WHEN** a pull request whose section carries a merge record is synced
- **THEN** the new body carries the same section

### Requirement: pr-restack-all restacks a chain with merges

pr-restack-all SHALL take a top pull request or a branch. For a pull request it
SHALL find the chain by walking each pull request's base to the open pull
request whose head is that branch, down to a base of `main`, and SHALL stop when
a pull request's last `## Depends on` entry is not the pull request below it, or
when a pull request in the chain or an open predecessor has its head in a fork.
For a branch it SHALL read the dependencies from its own `Depends-on:` trailers:
those on commits not reachable from any named predecessor's final head, so a
trailer inherited through a predecessor's branch is not counted. It SHALL work
in one fresh detached worktree under `./.tmp/` built from remote refs, and SHALL
NOT check out, create, or move a local branch. Bottom-up, for each pull request
it SHALL act only on the nearest predecessor P: when P is open, merge P's head
branch; when P is merged and P's merge commit is already in the branch, do
nothing; when P is merged otherwise, take HEAD as P's `headRefOid` and MERGE as
P's `mergeCommit.oid`, require `refs/pull/<P>/head` to equal HEAD, merge MERGE
into a detached copy of HEAD, and merge that copy into the branch; when P is
closed unmerged, stop. It SHALL push and, after the push lands, replace the
`- #<P>` entry with `- #<P> — merged as <MERGE> (head <HEAD>), reconnected`,
keeping every other byte of the body. It SHALL NOT merge `main` and SHALL stop
on a merge conflict, printing the worktree path.

#### Scenario: Predecessor open

- **WHEN** a pull request's predecessor is open
- **THEN** the predecessor's head branch is merged in and pushed, and no record
  is written

#### Scenario: Two predecessors already merged

- **WHEN** X and X+1 have merged and X+2 is restacked
- **THEN** only X+1 is reconnected, and X+2 contains `main` up to X+1's merge
  commit and nothing later

#### Scenario: Rerun after a conflict

- **WHEN** a restack stopped on a conflict that was resolved and it runs again
- **THEN** pull requests already restacked are skipped

#### Scenario: Branch without a pull request

- **WHEN** pr-restack-all runs on a branch whose trailers name one merged and
  one open pull request
- **THEN** the merged one is reconnected and the branch is pushed

#### Scenario: Local branches

- **WHEN** pr-restack-all runs while another worktree has a chain branch checked
  out
- **THEN** no local branch or worktree other than its own is changed

#### Scenario: Head in a fork

- **WHEN** a pull request in the chain, or its open predecessor, has its head in
  a fork
- **THEN** it stops before any push

### Requirement: pr-merge merges only into main

pr-merge SHALL refuse a pull request whose base is not `main` and SHALL NOT pass
`--admin`.

#### Scenario: Dependent pull request

- **WHEN** pr-merge is asked to merge a pull request based on another branch
- **THEN** it stops without merging

### Requirement: pr-merge-stack merges a chain bottom-up

pr-merge-stack SHALL take the top pull request and repeat until it has merged:
find the chain as pr-restack-all does, merge the bottom pull request through
pr-merge, confirm that GitHub retargeted the next pull request's base to `main`,
then restack the rest with one `pr-restack-all` run of the top.

#### Scenario: Chain of three

- **WHEN** pr-merge-stack runs on the top of a chain of three open pull requests
- **THEN** each merges in order, with a restack after each of the first two

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
