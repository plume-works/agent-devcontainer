---
type: feature
stage: implemented
description: Implement runs a fresh-context Verify itself, acts on its findings, and revises its own plan once an independent evaluator approves the revision, leaving the user only the decisions that narrow, drop, or re-word what was agreed.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T05:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
---

# Autonomous Implement loop

## Purpose

Implement carries a plan to a zero-CRITICAL Verify without the user relaying
each finding back. When Verify shows that the plan, not the code, is what's
wrong, Implement revises the plan itself. Before any revision lands, an
independent evaluation checks it. The user still makes every decision that
narrows, drops, or re-words what they agreed to.

## Behaviour

- **One orchestrator runs the loop, and every agent in it is a leaf.** For
  `/agentdev:iwe-implement` the orchestrator is the user's session. For
  `/agentdev:iwe-implement-all` it is the coordinator, once per plan. Neither
  `iwe-implementer`, `iwe-verifier`, nor `iwe-revision-evaluator` dispatches
  another agent.

- **Verify after the tasks.** Once the plan's last task closes, the orchestrator
  dispatches `iwe-verifier`. A zero-CRITICAL report with no actionable WARNING
  ends the run, and the run suggests `/agentdev:iwe-ship`.

- **Act on findings.** The orchestrator acts on every CRITICAL and on every
  WARNING that names a concrete route. A SUGGESTION goes only into the report. A
  code or evidence finding is fixed under the Implement rules, then Verify runs
  again.

- **Revise behind an evaluator.** Some findings call for a plan revision: a
  finding about the plan's intent, or a material deviation the run hits. The
  orchestrator drafts the revision in the working tree under the `iwe-planner`
  revise rules, including the plan audit and validation, and leaves it
  uncommitted. It then dispatches `iwe-revision-evaluator`. That prompt carries
  the plan key and the finding the revision answers, quoted as reported, and
  nothing else.

  - The evaluator compares the plan at `HEAD` with the uncommitted diff. It
    judges whether the revision answers that finding and keeps the plan's
    outcome, rather than restating the plan to match the code.
  - On `APPROVE` the revision commits and work resumes.
  - On `REJECT` or `ESCALATE` the diff is reverted and the run stops with a
    report.

- **What escalates no matter what.** The orchestrator never drafts, and the
  evaluator never approves, a revision that:

  - drops, narrows, or defers specified behavior;
  - accepts an exception to specified behavior;
  - changes `release`;
  - changes text the user approved.

  These wait for the user, as a material deviation does today.

- **Bounds.** The run stops when a finding comes back after a fix attempt. It
  also stops after 3 Verify rounds or 1 approved revision, whichever comes
  first.

## Edge cases

- **A deviation found mid-task** takes the same revision route without waiting
  for Verify.
- **In `/agentdev:iwe-implement-all`**, a dispatched `iwe-implementer` that hits
  a material deviation stops and reports it, as it does today. The coordinator
  then takes the revision route and re-dispatches the Implementer once the
  revision commits.
- **A Verify command that needs an approval** stops the loop with
  `Needs decision`, and the user re-runs the skill granting it.
- **On Codex**, every dispatch in the loop forwards no conversation turns, so
  the verifier and the evaluator start from a fresh context.

## Open questions

None — the scope, the findings acted on, the bound, and the escalation list were
settled with the maintainer.
