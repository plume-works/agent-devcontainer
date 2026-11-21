---
type: adr
stage: accepted
---

# Plan work branches share one iteration counter

A plan work branch has the name `iwe/<slug>/iter-<N>-<phase>`. `N` counts the
work branches of the plan in all phases, so the names alone put the pull
requests of a plan in sequence. The repository squash-merges and deletes the
head branch on merge, so after a merge the branch list of the remote no longer
records which iteration comes next, and `N` also counts the pull requests in all
states.

## Considered Options

- One counter for each phase. Rejected: it could not say whether
  `impl/foo/iter-3` came before or after `ship/foo/iter-1`.
- `<slug>/iter-<N>-<phase>` without a prefix. Rejected: a branch with the name
  of the slug blocks all the work branches of that plan.
- The name `iwe/<slug>` alone for the first iteration. Rejected: git cannot hold
  a ref beside another ref that would nest under it, so a bare `iwe/<slug>`
  would block every later `iwe/<slug>/iter-<N>-<phase>`.
- A lower bound from branches alone when `gh` fails. Rejected: it can reuse the
  name of a merged iteration and mix the history of two pull requests.
