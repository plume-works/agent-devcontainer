---
type: architecture
description: How work that depends on an open pull request is built, kept current, and reconnected after a squash merge with merges only — no rebase, no force-push, no gh stack.
sources:
- resource: .agents/plugins/agentdev/bin/depends_on.py
- resource: .agents/plugins/agentdev/bin/pr_restack_all.py
- resource: .agents/plugins/agentdev/bin/check_depends_on.py
- resource: .agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py
- resource: .agents/plugins/agentdev/skills/pr-restack-all/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
---

# Manual stacked pull requests

Work that depends on an open pull request is an ordinary pull request whose base
is its predecessor's branch. No branch is ever rewritten: every update is a
merge and every push is a plain push. Behavior is specified in [Stacked
PRs](../../../spec/stacked-prs.md); the user-facing feature is [Manual stacked
pull requests](../../../features/manual-stacked-prs.md).

## Recording a dependency

A dependent branch records each predecessor three ways:

- **Ancestry** — `git-new-branch --depends-on <P>` cuts it from P's head branch
  and merges the heads of any further predecessors.
- **A trailer commit** — one empty commit per predecessor carrying
  `Depends-on: #<P>`. A branch's *own* dependencies are the trailers not
  reachable from any named predecessor's final head, so trailers inherited
  through a predecessor's branch are not counted twice.
- **The body** — the pull request's `## Depends on` section lists `- #<P>`
  entries in merge order; the last entry is the nearest predecessor.

`bin/depends_on.py` is the one parser of the section and the trailers. It
rewrites one entry's line and keeps every other byte of the body;
`check_depends_on.py` gates every body pr-open and pr-gen-description apply on
that parser, so a regenerated description cannot drop a merge record or make the
section unreadable.

## Base and diff

The pull request targets its predecessor's branch, so its diff is its own work
only. When the predecessor merges, GitHub retargets it to `main`. A branch may
wait on one unmerged predecessor at a time, since a pull request has one base;
pr-open refuses a branch with two.

## Reconnecting after a squash merge

A squash merge leaves the successor holding the predecessor's original commits,
which `main` does not have. The successor is reconnected rather than rebased:

1. HEAD is the predecessor's `headRefOid` and MERGE its `mergeCommit.oid`, both
   from its pull request metadata, never from a branch ref (the branch is
   usually deleted). `refs/pull/<P>/head` must equal HEAD.
2. MERGE is merged into a detached copy of HEAD, never pushed.
3. That copy is merged into the successor, which is pushed without force.

The copy carries `main` exactly up to the squash commit, so the successor takes
nothing from `main` beyond it; catching up with later `main` is a separate
update-branch run. The entry becomes
`- #<P> — merged as <MERGE> (head <HEAD>), reconnected`. A branch that holds
both HEAD and MERGE is already reconnected, which makes a rerun a no-op.

The reconnect merge is a normal `git merge`. A replay with `git merge-tree` of
merging the squash commit into the pull request's final head, over every
squash-merged pull request where `main` had moved before the squash — 145 in
plume-works/agent-devcontainer and 73 in Dr-QP/Dr.QP — was clean and equal to
the squash commit's tree every time.

## Restacking a chain

`pr_restack_all.py` takes the top pull request, walks down through each base to
the open pull request with that head until a base of `main`, and checks that
each link's last `## Depends on` entry is the pull request below it. Bottom to
top, each link acts only on its nearest predecessor: an open one's head is
merged in, a merged one is reconnected. It works in one fresh detached worktree
under `./.tmp/` built from remote refs and never checks out, creates, or moves a
local branch, so other sessions' worktrees are untouched. A session whose branch
it advanced sees an ordinary non-fast-forward rejection and merges.

pr-merge merges only a pull request based on `main`. pr-merge-stack loops: merge
the bottom through pr-merge, then restack the rest with one `pr_restack_all.py`
run of the top.

## Blocking merges into dependent branches

A ruleset on `refs/heads/iwe/**` that requires a status check nothing reports
refuses a merge into those branches unless a bypass actor forces it. Its bypass
list can name only repository roles and GitHub Apps that this repository or its
organization owns. The built-in GitHub Actions app, which `GITHUB_TOKEN` acts
as, is refused (HTTP 422). A workflow that pushes to an `iwe/` branch with
`GITHUB_TOKEN`, as the AI task responder does, is rejected until it pushes as an
owned App that the ruleset exempts.

## Rejected alternatives

- **GitHub native stacks driven by `gh stack`.** GitHub rebases every remaining
  layer on the server after a lower layer merges, and `gh stack rebase` rewrites
  them again locally before a force-push; a lease protects remote-only commits,
  not the consumers of a rewritten branch, and every local copy goes stale
  regardless of the tool.
- **Every pull request targets `main`.** Its diff includes every predecessor
  until they merge; basing on the predecessor gives a clean diff.
- **Resolving the reconnect merge with `-s ours`.** Correct by construction but
  silent; a normal merge lets git report a conflict.
- **Owners restacking their own pull requests, or a coordinator pausing its
  sessions.** More coordination than one restack from a detached worktree.
- **A required `base-is-main` check without bypass.** It also rejects the
  owners' own pushes and branch creation (GH013).
