---
type: adr
stage: accepted
---

# Only the Ship and Plan skills are explicit-only

`/agentdev:iwe-ship` sets `disable-model-invocation: true`, because a stray Ship
run reaches the remote repository; `/agentdev:iwe-plan` is explicit-only too.
`/agentdev:iwe-implement` is model-invocable: it needs a named active plan and
asks when the plan is ambiguous, so a stray match has nothing to build.
`/agentdev:iwe-verify`, `/agentdev:iwe-adversarial-review`, and
`/agentdev:iwe-capture` are model-invocable because the Implement session must
start them without stopping for the user: it runs Verify, runs a planned
adversarial review task, and files a deferred task or a defect mid-run.

## Considered Options

- Drop the gate on Ship and rely on the skill description. Rejected: every
  harness lists a model-invocable skill to the model with its description, so a
  description match can start Ship from Explore, for example after a partial
  answer closes a plan's open question.
- A skill that checks who started it, or a `PreToolUse` hook. Rejected: a skill
  that checks who invoked it is a prompt-level check that a model can argue
  past. A hook's input names the tool call, not the skill or request behind it,
  so it cannot tell a requested dispatch from a stray one without parsing the
  transcript, and it needs one implementation per harness.
- An explicit-only Implement skill. Rejected: Implement needs a named active
  plan whose dependencies are done or in review, so a stray match has nothing to
  build, and Plan and Explore, the sessions where a stray start could happen,
  never name the skill.
- An explicit-only `/agentdev:iwe-verify`. Rejected: Verify mutates nothing and
  the Implement session must start it, so the gate would block the Implement
  session and protect nothing.

## Consequences

- Claude Code refuses an explicit-only skill to subagents too, so a subagent
  whose prompt names `/agentdev:iwe-ship` cannot run it.
