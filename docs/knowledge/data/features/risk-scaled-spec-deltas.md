---
type: feature
stage: implemented
description: Plans state spec impact in one of three risk-scaled forms, so a behavior-changing plan carries a reviewable contract before implementation without importing OpenSpec's change bundles or a delta application engine.
generated:
  by: codex
  at: 2026-08-31T17:36:33Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
---

# Risk-scaled spec deltas

## Purpose

A plan's `## Spec changes` states intended post-change contract because Verify
evaluates implementation before Ship merges durable specs. Naming a spec locates
the contract; the plan must also state what the contract is intended to say once
the work ships.

## Behaviour

**`## Spec changes` has three forms, and Plan owns the threshold.**

1. `None — no behavioral change` — refactors, tooling, docs-only work.
2. A linked spec plus a concise **normative outcome** — one unambiguous low-risk
   behavior, where a scenario block would add ceremony without resolving
   anything.
3. A fenced `ADDED` / `MODIFIED` / `REMOVED Requirements` delta — required when
   the change touches compatibility, acceptance criteria,
   security/privacy/data-loss behavior, or a requirement's scenario set.

`ADDED` and `MODIFIED` carry the complete post-change requirement including
*every* surviving scenario; a scenario omitted from a MODIFIED block reads as
one the plan deliberately dropped, and Verify treats it that way. `REMOVED`
names the requirement and why the behavior is retired. There is no `RENAMED` — a
rename is an explicit removal plus an addition, because identity semantics would
imply a parser.

**What a plan records is intent, not a second durable truth.** The durable spec
keeps describing released behavior until Ship merges the change. That single
distinction resolves the boundary conflict: Verify now judges implementation
against the *effective contract* — the current durable spec plus the plan's
recorded intent — so a back-ticked not-yet-created spec is valid whenever the
plan introduces it and supplies its planned contract.

**Each skill has one job against the form.** Implement loads it alongside the
durable spec and may make tactical corrections only while the recorded outcome
holds exactly as written; any change to a normative outcome, operation,
requirement, or scenario is material by definition and returns to Plan revise
mode. Verify checks per form and raises a CRITICAL when the form is too weak for
the risk, the implementation contradicts recorded intent, or a delta would
silently drop an unaffected scenario. Ship merges only what intent and the
zero-CRITICAL report both support.

## Edge cases

- **Nothing applies the delta.** No parser, no fixed operation order, no
  conflict rules, no executable postconditions. Ship performs an intelligent
  merge and must account for every operation; a merge that lands most of the
  delta is a failed merge, not a partial success.
- **Intent and implementation disagree.** Ship stops, makes no lifecycle
  transition, and never rewrites the intent from the code — the reviewed
  contract is the thing worth keeping.
- **The fence survives normalization.** `iwe normalize` rewrites the opening
  fence as ```` ``` markdown ````; the Requirement/Scenario headings inside stay
  at their canonical levels rather than being absorbed into the plan's own
  hierarchy.
- **`REMOVED` is specified but still tracked for an end-to-end worked
  instance.** No plan has retired a requirement yet. Tracked as
  [Exercise REMOVED delta blocks end to end](../backlog/exercise-removed-delta-blocks.md).

## Resolved decisions

- Deltas are conditional, not mandatory. Requiring one per plan would conflict
  with the workspace's progressive-rigor rule and tax every refactor.
- No separate change bundle, store, delta-spec document, or archive move. The
  delta lives inside the one plan document; a second lifecycle would duplicate
  the plan's own.
- Determinism is not claimed. Earlier work
  ([Strengthen the workflow skill contracts](../plans/20260815-strengthen-workflow-skill-contracts.md))
  rejected OpenSpec's delta machinery wholesale; this separates the two ideas it
  had grouped — the notation is adopted, the application engine is not.
- A stale delta is never silently reconciled from the implementation. That would
  erase the reviewed contract, so a material mismatch returns to Plan revision.
