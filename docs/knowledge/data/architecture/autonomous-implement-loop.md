---
type: architecture
description: Why the Implement verify, fix, and revise loop runs in one orchestrator whose every dispatched agent is a leaf, why the Plan rulebook moved into the iwe-planner agent, and why a revision is drafted, audited, and evaluated before it commits.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T13:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
---

# Autonomous Implement loop

## Decision

**One orchestrator runs the loop, and every agent is a leaf.** The user's
session is the orchestrator for `/agentdev:iwe-implement`; the
`/agentdev:iwe-implement-all` coordinator is the orchestrator once per plan.
`iwe-implementer`, `iwe-verifier`, and `iwe-revision-evaluator` never dispatch,
so the loop runs on Claude Code, Codex, and OpenCode without OpenCode's
experimental depth setting ([Nested subagent
dispatch](nested-subagent-dispatch.md)).

**The loop is written once, in the `iwe-implementer` rulebook,** as
`## Running the loop`, a section only an orchestrator runs. The session already
follows the rulebook in place; the coordinator reads the same file for that
section, so the two never drift. A dispatched Implementer that meets a material
deviation stops and reports it, and the coordinator takes the route.

**The Plan rulebook is the `iwe-planner` catalog agent,** which
`/agentdev:iwe-plan` follows in place, the pattern Implement already uses.
`/agentdev:iwe-plan` is explicit-only, and reading a gated skill's file to get
around the gate is rejected in [Explicit-only workflow
agents](explicit-only-workflow-agents.md). The orchestrator follows
`iwe-planner` in its revise mode only, so issue closing — reachable only from
create mode — keeps its script bundled with the skill.

**A revision is drafted, audited, evaluated, then committed.** The orchestrator
drafts it under the `iwe-planner` revise rules, including the Durable Knowledge
Auditor gate and validation, and leaves it uncommitted. `iwe-revision-evaluator`
then judges the final text: its prompt carries only the plan key and the quoted
finding, and it reads `git show HEAD:<plan>` and `git diff -- <plan>`. It
returns:

- `APPROVE` — the revision answers the finding and keeps every specified
  behavior; the orchestrator commits it and resumes.
- `REJECT` — the revision does not answer the finding, or restates the plan to
  match the code.
- `ESCALATE` — the revision drops, narrows, defers, or accepts an exception to
  specified behavior, changes `release`, or changes text the user approved.

On `REJECT` or `ESCALATE` the orchestrator restores the plan from `HEAD` and
stops. The evaluator's tools are `Bash, Read, Grep, Glob`, so the Codex
installer gives it a `read-only` sandbox.

**The run is bounded.** It stops when a finding recurs after a fix attempt,
after three Verify rounds, or when a second revision would follow one approved
revision.

## Rejected alternatives

- **Let `iwe-verifier` judge the revision.** Verify checks code against the
  plan; whether a new plan still serves the old one's outcome is a different
  question with its own rubric.
- **Reuse `Principal Engineer` as the evaluator.** It is advisory and can
  dispatch agents; the gate needs a leaf that returns a fixed verdict.
- **Evaluate before the audit.** The audit may rewrite the text, so the
  evaluator would approve bytes that never land.
- **Run the loop inside a dispatched `iwe-implementer`.** It would need nested
  dispatch, and the coordinator could no longer see what its Implementer
  dispatched.
