---
type: feature
stage: accepted
description: Work that depends on an open pull request is a normal pull request based on its predecessor's branch, kept current with merges and never rewritten, restacked after a squash merge by one pr-restack-all run.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/git-new-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md
- resource: AGENTS.md
---

# Manual stacked pull requests

## Purpose

A chain of dependent pull requests is a set of normal pull requests, each based
on the branch of the one it depends on. No branch is ever rewritten: every
update is a merge and every push is a plain push, so a stale copy of a branch is
rejected instead of overwriting newer work. This replaces GitHub native stacks
and the `gh stack` extension, whose rebases rewrote branches other sessions were
working on.

## Behaviour

**Cutting a dependent branch.** `/agentdev:git-new-branch <name> --depends-on

**Opening its pull request.** `/agentdev:pr-open` reads the trailer, sets the
pull request's base to P's head branch so GitHub shows only this work's diff,
writes the first `## Depends on` section listing the predecessors, and opens it
ready for review. It refuses while more than one dependency is unmerged. When P
merges, GitHub deletes P's branch and retargets the pull request to `main`.

**Restacking.** `/agentdev:pr-restack-all` takes a top pull request, walking the
chain down through each pull request's base, or a branch, reading its trailer.
In one fresh detached worktree built from remote refs, it restacks each pull
request onto its nearest predecessor, bottom-up:

- an open predecessor's branch is merged in;
- a merged predecessor is reconnected: its final head and its squash commit are
  read from the pull request's metadata, the squash commit is merged into a
  private copy of that head, the copy is merged into the dependent branch, and
  the `## Depends on` line becomes
  `- #591 — merged as d66fdf4d (head 7a8c22c2), reconnected`.

It never merges `main`, never checks out or moves a local branch, and pushes
without force.

```
main   m0───o──────Sx──────q──────Sy───r
        \           \              \
         x1──x2──────Bx             \
               \       \             \
                y1──y2──Ry────────────By
                      \   \             \
                       z1──Rz1───────────Rz2   ← X+2
```

**Merging a chain.** `/agentdev:pr-merge-stack` takes the top pull request and
repeats: merge the bottom one, whose base is `main`, through
`/agentdev:pr-merge`; restack the rest with one `pr-restack-all` run; until the
top has merged. `pr-merge` refuses a pull request whose base is not `main`.

**Merges into a dependent branch are blocked.** A repository ruleset on
`refs/heads/iwe/**` requires a `base-is-main` status check that no workflow
reports, with the Write, Maintain, and Admin roles allowed to bypass. Owners
push to their branches; merging a pull request into one is blocked unless
someone deliberately overrides it.

## Edge cases

- **The predecessor has no pull request.** `git-new-branch --depends-on` stops;
  open the predecessor's pull request first.
- **A conflict while restacking.** Git reports it and `pr-restack-all` stops,
  printing its worktree; after resolving there, a rerun skips the pull requests
  already restacked.
- **The session owning a restacked branch has local commits.** Its next push is
  rejected as non-fast-forward; `update-branch` merges the new remote commits
  in. Nothing is lost on either side.
- **A branch depends on two open pull requests in different chains.** It is
  based on both, with one trailer line each, and has no pull request until at
  most one of them is unmerged.
- **A person overrides the ruleset** and merges a pull request into a dependent
  branch. The ruleset allows it deliberately; agents never pass `--admin`.

## Open questions

- Whether the AI responder pushes to pull request branches as a GitHub App; if
  it does, the App needs its own bypass entry in the `iwe/**` ruleset.
