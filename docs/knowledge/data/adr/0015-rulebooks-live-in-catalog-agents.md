---
type: adr
stage: accepted
description: The Plan, Implement, Verify, and Ship rulebooks are catalog agents; the Verify and Ship skills dispatch theirs, and the Plan and Implement skills follow theirs in place.
---

# The workflow rulebooks are catalog agents

Claude Code refuses an explicit-only skill to the Skill tool in each context,
and it does not preload one into an agent. For this reason, the rulebooks of
Plan, Implement, Verify, and Ship are the agents `iwe-planner`,
`iwe-implementer`, `iwe-verifier`, and `iwe-shipper`. The Verify and Ship skills
dispatch their agent. The Plan and Implement skills tell the session of the user
to follow the agent file in place, so that the session can ask the user. No
skill holds the rules of its workflow.

## Considered Options

- Preload the explicit-only skill into the agent through its `skills:` list.
  Rejected: Claude Code does not preload an explicit-only skill into an agent,
  so the agent starts without its rulebook.
- Keep the rulebook in the explicit-only skill and let a subagent read its file.
  Rejected: the refusal of the Skill tool tells the model not to do the workflow
  by a different route. A model can correctly refuse, and a model that does the
  workflow avoids the gate.
- Keep the Verify rulebook in the skill, behind a thin agent. Rejected: the
  skill is then also the entry point that must dispatch the agent. A session
  that loads it already has the rules and can do them itself.

## Consequences

- The `description` of each agent names the callers that start it and says that
  a description match never starts it.
- The agent file is the rulebook on both harnesses. The Claude Code plugin loads
  it, and the OpenCode bridge registers it as a subagent.
- A dispatched agent cannot ask the user. When its rulebook needs a decision, it
  stops before the step and reports the decision that it needs.
- The Implement session follows `iwe-planner` only in revise mode. Only create
  mode closes an issue, so
  `.agents/plugins/agentdev/skills/iwe-plan/agent-code/close-issue.py` stays in
  the Plan skill.
- `iwe-verifier` has the `Write` tool. Report-only is a rule of its rulebook,
  not a tool limit.
