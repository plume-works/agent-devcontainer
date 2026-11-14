---
type: adr
stage: accepted
description: Plan work branches have the name iwe/<slug>/iter-<N>-<phase>, with one counter N for all phases that counts branches and pull requests in all states.
---

# Plan work branches share one iteration counter

A plan work branch has the name `iwe/<slug>/iter-<N>-<phase>`. `N` counts the
work branches of the plan in all phases, so the names alone put the pull
requests of a plan in sequence. The repository deletes a head branch when it
merges, so `N` also counts the pull requests in all states.

## Considered Options

- One counter for each phase. Rejected: it cannot show if `impl/foo/iter-3` came
  before or after `ship/foo/iter-1`.
- `<slug>/iter-<N>-<phase>` without a prefix. Rejected: a branch with the name
  of the slug blocks all the work branches of that plan.
- A bare `iwe/<slug>` for the first iteration. Rejected: git cannot keep a
  reference next to a reference below it, so it blocks each later work branch.
- A lower limit from branches alone when `gh` fails. Rejected: it can use again
  the name of a merged iteration and mix the history of two pull requests.

## Consequences

- Two checkouts can take the same `N` in different phases. The next name is
  still after both.
- The counter ignores branches in the earlier `impl/<slug>/iter-<N>` and
  `ship/<slug>/iter-<N>` shapes.
- `iwe-branch-name.py next` stops with `GH_UNAVAILABLE` when `gh` fails.
