---
type: adr
stage: accepted
description: Implement can start on a plan whose dependency has an open pull request, but Ship refuses a plan while a dependency is not done.
---

# Implement can stack on a dependency in review; Ship cannot

Implement can build a plan on a dependency that has an open pull request.
`bin/plan_predecessors.py` finds that pull request, and the work branch stacks
on it. Ship refuses a plan while a plan that its `## Depends on` links is not
`stage: done`.

## Considered Options

- Implement waits until each dependency is done. Rejected: each dependent plan
  then waits for the full implement, review, merge, and ship cycle of its
  dependency.
