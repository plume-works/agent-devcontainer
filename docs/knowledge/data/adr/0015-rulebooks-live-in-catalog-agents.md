---
type: adr
stage: accepted
description: The Plan, Implement, Verify, and Ship rulebooks are catalog agents, and the skills that start them hold no rules.
---

# The workflow rulebooks are catalog agents

Claude Code refuses an explicit-only skill to the Skill tool in each context,
and it does not preload one into an agent. For this reason, the rulebooks of
Plan, Implement, Verify, and Ship are the agents `iwe-planner`,
`iwe-implementer`, `iwe-verifier`, and `iwe-shipper`. Each entry skill only
starts its agent.

## Considered Options

- Keep the rulebook in the explicit-only skill and let a subagent read its file.
  Rejected: the refusal of the Skill tool tells the model not to do the workflow
  by a different route. A model can correctly refuse, and a model that does the
  workflow avoids the gate.
- Keep the Verify rulebook in the skill, behind a thin agent. Rejected: the
  skill is then also the entry point that must dispatch the agent. A session
  that loads it already has the rules and can do them itself.
