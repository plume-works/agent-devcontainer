---
type: finding
description: What iwe-verifier and the pr-review flow each catch on a plan's change, measured on one plan — Verify finds code that contradicts the plan, pr-review finds a plan whose specified behaviour is itself wrong — so neither replaces the other.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: docs/knowledge/data/plans/20261031-model-invocable-implement.md
- resource: docs/knowledge/data/plans/20261102-adversarial-review.md
- resource: docs/knowledge/data/plans/20261102-autonomy-loop.md
---

# What Verify and pr-review each catch

## Question

Can the `pr-review` flow replace `iwe-verifier` as the gate before Ship, or
catch real defects Verify misses, given that Verify blocks on plan bookkeeping
whose fix costs a full revision round?

## Measurement

One plan, [Let any session asked to implement a named plan start
Implement](../plans/20261031-model-invocable-implement.md), at the commit where
its tasks closed. Verify ran once on its own route. `pr-review` ran at full
effort over the plan's own diff, with the plan standing in for the pull request
description, the metadata gate and posting left out, and each surviving
candidate checked by its own validator. Each finding was labelled a real defect
or not before the `pr-review` results were read.

| Finding                                                                                        | Real defect             | Verify     | `pr-review`             |
| ---------------------------------------------------------------------------------------------- | ----------------------- | ---------- | ----------------------- |
| A `## Verification` command broken by its own invocation                                       | no — the plan's command | CRITICAL   | not raised              |
| An unchanged Explore line offering "return to implementation", against a new requirement       | yes                     | WARNING    | missed                  |
| A planned scenario without a test                                                              | no — coverage           | WARNING    | not raised              |
| CI still running at the head; a task's file list missing a file                                | no                      | SUGGESTION | not raised              |
| [A relayed approval taken without authentication](../bugs/relayed-approval-unauthenticated.md) | yes                     | missed     | blocking, confirmed     |
| A docstring one character over the line limit, which CI does not enforce                       | nit                     | not raised | non-blocking, confirmed |

`pr-review` cost several times the tokens of the Verify run.

## What is known

- **Verify catches code that contradicts the plan**, including a line the diff
  never touched, because it maps each requirement to the code. `pr-review` reads
  the diff and the code the diff touches, so an untouched line that a new
  requirement makes wrong is outside its reach.
- **`pr-review` catches a plan whose specified behaviour is wrong.** Verify
  judges conformance, so behaviour the plan itself specifies can never be a
  finding, however unsafe. That is the question [Adversarial review of a plan or
  its code](../plans/20261102-adversarial-review.md) assigns to a separate
  agent.
- **`pr-review` ignores plan bookkeeping.** It raised none of the findings that
  were not defects. Verify's cost on them comes from two rules — every failing
  verification command is a CRITICAL, and a corrected verification step is a
  material deviation — which [Fix a broken verification command as a tactical
  correction](../backlog/verification-command-fix-is-tactical.md) addresses.
  [Make the Implement loop converge](../plans/20261102-autonomy-loop.md) removes
  the work that WARNINGs create but keeps both rules.

## Eliminated

- **`pr-review` replaces Verify.** Eliminated: it missed the one real defect
  Verify found, and it does not run the plan's verification commands or check
  task evidence, which Ship relies on.

## What would settle the rest

The measurement is one plan. Whether the security and logic correctness pass
finds design defects on other plans, and how often it raises ones a validator
drops, needs the same comparison on plans of other kinds. The comparison counts
as settled once it has run on plans that touch authority, a workflow rulebook,
and runtime code. If those agree with this one, the decision is to run an
adversarial or `pr-review`-style pass beside Verify, not in its place. If they
show the pass rarely finds a real defect, the decision is that it is not worth
its cost and Verify stands alone.

## Closing

Open. It closes when the comparison has run on plans that touch authority, a
workflow rulebook, and runtime code, and the maintainer decides whether a
`pr-review`-style pass runs beside Verify or is not worth its cost.
