---
type: feature
stage: accepted
description: The iwe-branch-name skill names a plan's work branches as <impl|ship>/<plan-slug>/iter-<N> and reads a plan's state at the remote default branch, so callers create the next branch through git-new-branch.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-25T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/git-new-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/skill-scripts/SKILL.md
---

# iwe-branch-name

## Purpose

A plan rarely lands in one pull request: implementation can take several, and
shipping takes one more. Each needs a fresh branch off the default branch, and
the merged ones are deleted on the remote, so nothing records which iteration
comes next. Hand-picked names drift (`impl-<slug>-iter2`, `<slug>-impl`) and
cannot be traced back to their plan mechanically. One skill owns the name and
the lookup, so every caller — the implementer today, post-merge cleanup next —
gets the same answer.

## Behaviour

- **Name shape.** `<phase>/<slug>/iter-<N>`, where `phase` is `impl` or `ship`,
  `slug` is the plan key's file name without its `YYYYMMDD-` prefix, and `N`
  starts at 1. The suffix is always present, so no name is a path prefix of
  another and Git never refuses one for nesting under an existing ref.
- **Next iteration.** `N` is one more than the highest iteration of that phase
  and slug found among local branches, the remote's branches, and the pull
  requests in any state of the repository the remote names. Only names matching
  the shape exactly count.
- **Plan state.** The plan is read at the fetched remote default branch and
  reported as missing, cancelled, done, complete (no stage, at least one task,
  every task ticked), or incomplete.
- **Next name from state.** Done, cancelled, or missing → the default branch;
  complete → the next `ship` name; incomplete → the next `impl` name.
- **Parse.** A branch name is split into phase, slug, and iteration; a name off
  the shape is reported as such, never guessed at.
- **Names only.** The skill creates no branch; callers run
  `/agentdev:git-new-branch` with the name.
- **Implementer.** On the default branch, the implementer names its work branch
  with the next `impl` name instead of the bare slug.

## Edge cases

- The pull request lookup is unavailable (`gh` missing or unauthenticated): the
  lookup fails rather than return a number that may already be taken.
- Two plans share a slug under different dates: the slug is ambiguous and the
  lookup refuses it.
- A plan written on a branch but not yet on the default branch reads as missing
  there; a caller that already knows the phase asks for the name by phase.
- Branches named before this shape (`<slug>`) are ignored by the count.

## Open questions

None.
