---
type: architecture
description: Why adversarial review is a separate report-only agent outside Verify, what its two targets are, who may start it, and the alternatives rejected.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-adversarial-reviewer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-adversarial-review/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
---

# Adversarial review

## Decision

**Adversarial review is its own agent, outside Verify.** Verify is a conformance
check: it reports only against the plan's contract, so the [Autonomous Implement
loop](../../2.0.0/architecture/autonomous-implement-loop.md) converges once the
code meets that contract. Looking for ways to defeat a design or its code asks a
different question with its own rubric, and its findings have no fixed end. The
maintainer decided it lives in `iwe-adversarial-reviewer`, a report-only leaf
agent run from a fresh context, which `/agentdev:iwe-adversarial-review`
dispatches with a prompt carrying only the plan key, the target, and the user's
approvals quoted verbatim.

**It has two targets.**

- `plan` — claims the design cannot keep, scenarios the plan misses, and limits
  a promise does not state.
- `code` — ways to defeat the implemented behaviour. Each finding names the plan
  claim it defeats, or `none`, so the caller can tell a broken promise from a
  weakness the plan never claimed to cover.

**It runs only when asked.** A person may run it, on the plan before the plan is
finalized or on the code. The planner may add one closing or near-closing task
that runs it against the code, for a plan whose claims are worth attacking.
Planning itself never invokes it. In the Implement loop the Implement session
runs that task once per plan: a finding that defeats a plan claim takes the code
route, and any other finding is filed through `/agentdev:iwe-capture`. The skill
is model-invocable so that loop can run a planned task.

## Rejected alternatives

- **Extend the Durable Knowledge Auditor.** It would hold two unrelated rubrics:
  durable text and design attacks.
- **Run it inside every Verify round.** Findings outside the plan's contract
  would keep the loop from converging, the failure that making Verify a
  conformance check removes.
- **Make the skill explicit-only.** The Implement loop could not run a planned
  review task.
