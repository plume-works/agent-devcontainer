---
type: adr
stage: accepted
description: The Ship and Plan entry skills are explicit-only; the Implement, Verify, adversarial review, and Capture skills are model-invocable.
---

# Only the Ship and Plan entry skills are explicit-only

`/agentdev:iwe-ship` and `/agentdev:iwe-plan` set
`disable-model-invocation: true`, because a Ship run that the user did not start
changes the remote repository. `/agentdev:iwe-implement`,
`/agentdev:iwe-verify`, `/agentdev:iwe-adversarial-review`, and
`/agentdev:iwe-capture` are model-invocable, because the Implement session must
start them without a stop for the user.

## Considered Options

- Ship without the gate, and use only the skill description as the control.
  Rejected: each harness shows the description of a model-invocable skill to the
  model. A description match can start Ship from Explore.
- A skill that checks who started it, or a `PreToolUse` hook. Rejected: a model
  can find an argument against a check in a prompt. The input of the hook names
  the tool call, not the request behind it, and each harness needs its own hook.
- An explicit-only Implement skill. Rejected: Implement needs a named active
  plan whose dependencies are done or in review, so a wrong match has nothing to
  build. Plan and Explore never name the skill.
- An explicit-only `/agentdev:iwe-verify`. Rejected: Verify changes nothing, and
  the Implement loop must start it, so the explicit-only setting stops the
  Implement loop and protects nothing.

## Consequences

- Claude Code also refuses an explicit-only skill to a dispatched subagent. As a
  result, a subagent whose prompt names `/agentdev:iwe-ship` cannot start it.
