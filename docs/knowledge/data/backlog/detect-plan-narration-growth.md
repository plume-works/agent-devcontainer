---
type: task
created: 2026-08-24
stage: planned
priority: low
description: Investigate whether a plan absorbing a working logbook can be detected mechanically, which the shape gate cannot do today because narration has no reliable shape.
generated:
  by: claude-code/opus-5
  at: 2026-08-24T00:00:00Z
sources:
- resource: docs/knowledge/tests/test_plan_checkboxes.py
- resource: docs/knowledge/data/plans/20260817-no-logbooks-in-the-graph.md
- resource: AGENTS.md
---

# Detect plan narration growth mechanically

[Never write a working logbook](../plans/20260817-no-logbooks-in-the-graph.md)
states the rule in wording — `AGENTS.md` Best Practice 8, the graph manual's
narrative exceptions, and the implement skill's `## Capturing`. Nothing enforces
it. A plan that absorbs a running account of an in-flight investigation is
caught by a reader, or not at all.

## Why the existing gate cannot do it

`docs/knowledge/tests/test_plan_checkboxes.py` is a shape gate: it matches
checkbox lines, indented `- **Evidence:**` children, fences, and headings, and
decides violations from structure alone. Narration has no such shape. It is
ordinary prose in `## Context`, `## Approach`, or task rationale — the same
constructs a legitimate plan uses for the same purpose.

The measurable proxies do not survive contact:

- **Line count or growth ratio.** A large plan is not a narrated one. This fires
  on legitimately long plans and misses a short, dense logbook.
- **Prose-to-task ratio.** Plans that carry approved wording verbatim, as
  [Never write a working logbook](../plans/20260817-no-logbooks-in-the-graph.md)
  does, are mostly prose by design.
- **Keyword matching** (run identifiers, "attempt", "failed"). A plan may
  legitimately quote a failure it is fixing, and a narrator need not use the
  vocabulary.

The distinguishing test — *would this still be true if the work had gone right
the first time?* — is semantic. It requires reading the claim, not the file.

## What to do

Establish first whether a mechanical signal exists that a maintainer would
trust, before writing a gate. Options worth evaluating:

- A diff-scoped check: flag growth in `## Context` or `## Approach` on a plan
  whose frontmatter shows implementation underway, and report rather than fail.
  This targets the one transition that matters and ignores plan size.
- An advisory LLM check in CI, reporting candidate passages for a human to
  judge, never blocking a merge.

A gate that fires on healthy plans will be silenced, taking the honest checks in
the same file with it. Report-only is the safer starting point.

## Why it is not urgent

The wording landed and the auditor covers the surfaces the rule reaches, so the
rule is stated and reviewable. What is missing is automation for a failure that
a reader currently does catch.
