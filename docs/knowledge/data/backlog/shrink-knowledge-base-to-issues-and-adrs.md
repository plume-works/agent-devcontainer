---
type: task
created: 2026-11-12
stage: pending
priority: medium
description: After the single-home plan ships, reduce the knowledge base to an issue tracker and architecture decision records, with code and executable tests as the only statement of behaviour.
sources:
- resource: docs/knowledge/data/plans/20261112-knowledge-base-single-home.md
- resource: docs/knowledge/data/spec/firewall.md
- resource: docs/knowledge/data/spec/xpra-port-forwarding.md
---

# Shrink the knowledge base to an issue tracker and decision records

The repository owner decided on 2026-11-12 that code and executable tests are
the only source of truth for behaviour, and that the knowledge base keeps two
jobs: tracking work (bugs, tasks, plans) and recording architecture decisions.
Specs stop being a statement of behaviour.

Specs and code deviate. A comparison of three specs with the code they describe
found one that matched and two that stated behaviour the code does not have.
Specs rot, and a spec cannot be trusted over the code.

## Why

The repository owner's account of what a few months of use showed:

- Agents writing many documents produced a mess even with an enforced structure.
  The schemas, hubs, and workflow skills constrained each document's shape and
  did not keep its content true.
- People cause the same decay. Agents reach it far sooner, because they write
  far more.
- The cost falls differently. A person stops reading documents that have gone
  stale. An agent keeps reading every one of them, meets statements that
  contradict each other or the code, cannot tell which to trust, and asks the
  repository owner which is right.

## Design frame

The redesign treats an agent as a new developer joining the project: someone
capable, with no history here, who reads whatever the repository hands them and
takes it at face value. The repository owner set this as the frame for every
choice in the redesign. Each document that stays must be one a new developer
could act on without asking whether it is still true, and anything that fails
that test is removed instead of maintained.

## Order

This work starts after [One home for each kind of
knowledge](../archive/next-release/plans/20261112-knowledge-base-single-home.md)
ships. The repository owner wants that plan executed in full first, so the graph
holds a complete record of how the knowledge base deteriorated before it is
reduced.

## What to do

- Decide what replaces each requirement in `data/spec/`: an executable test
  where one can cover the behaviour, a decision record where the requirement
  states a choice and its reason, and deletion otherwise.
- Decide which document types remain and remove the schemas, hubs, and workflow
  skill steps that maintain the others.
- Write the plan with `/agentdev:iwe-plan`.
