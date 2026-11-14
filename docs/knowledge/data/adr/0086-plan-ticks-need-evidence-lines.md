---
type: adr
stage: accepted
description: Each ticked task of an active plan needs an evidence line in any form, which a knowledge-base test checks for shape and Verify never reads.
---

# A ticked plan task needs an evidence line that only a shape test checks

A find-and-replace can tick each box in a file, but it cannot write the evidence
line that each tick needs. As a result, each ticked task of an active plan has
an evidence line in any form. `docs/knowledge/tests/test_plan_checkboxes.py`
checks its shape on each commit that changes a plan, and Verify does not read
it.

## Considered Options

- More prose rules in the Implement rulebook. Rejected: the rules against false
  ticks were there already, and a find-and-replace does not obey them.
- Evidence that names a check that Verify does again. Rejected: Verify cannot do
  a live, manual, or external check again, so the rule stops Verify or removes
  such work from plans.
- The check in `validate_agent_files`. Rejected: that package validates the
  agent files of any repository and must not know the graph of this repository.

## Consequences

- Verify reports no finding on a ticked task or on the form of its evidence
  line.
