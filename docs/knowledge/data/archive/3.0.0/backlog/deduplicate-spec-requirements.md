---
type: task
stage: done
priority: medium
created: 2026-11-09
description: Give every rule in every durable spec one home requirement, and drop each scenario that only restates its own requirement.
sources:
- resource: docs/knowledge/data/spec/iwe-workflow-skills.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/skills/semantic-refactor-audit/SKILL.md
completed: 2026-11-12
---

# Remove redundancy from the durable specs

A spec is the second copy of the behaviour its code or rulebook carries, the way
tests are for code; that duplication is intended. Redundancy *inside* a spec is
not: it multiplies the edits every behaviour change needs and lets copies of one
rule drift apart. Two kinds are in scope, across every document under
`data/spec/`:

- **A rule restated across requirements.** One rule written into several
  requirements, typically once per phase it touches. In [IWE workflow
  skills](../../../spec/iwe-workflow-skills.md), for example, "Explore and Plan
  never start Implement" appears in five places, "a narrowing deviation waits
  for the user" in five, and "a dispatch prompt carries only the key and the
  user's approvals quoted verbatim" in seven.
- **A scenario that only restates its requirement.** A WHEN/THEN that re-renders
  a SHALL clause and adds no case the clause leaves open, such as the single
  scenario under
  `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-ship-waits-for-post-merge-observations`.

Out of scope: statements of how the catalog is wired (which agent is dispatched,
what its prompt carries). They are behaviour a rulebook must exhibit, so they
keep their copy in the spec.

## What to do

- Give each rule exactly one home requirement; other requirements reference it
  instead of restating it.
- Keep a scenario only when it covers a case its requirement's wording does not
  already settle.
- Change no rulebook or code: the plan's `## Spec changes` carries only
  `MODIFIED` and `REMOVED` operations, and is the first real exercise of
  [Exercise REMOVED delta blocks end to
  end](../../../backlog/exercise-removed-delta-blocks.md).
- Prove nothing was lost with `/agentdev:semantic-refactor-audit`: every
  behaviour the specs state before the change has exactly one home after it.

Land [Stop the planner from adding spec
redundancy](planner-spec-redundancy-check.md) first, so the cleaned specs do not
grow back.
