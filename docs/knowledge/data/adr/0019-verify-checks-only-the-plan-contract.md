---
type: adr
stage: accepted
description: Verify reports only what contradicts the plan, CI stays with pr-merge, and the Implement loop stops on a fixed bound.
---

# Verify checks only what the plan promised

Verify is a conformance check. Each `CRITICAL` or `WARNING` result names the
part of the plan that the code contradicts, and CI stays with `pr-merge`, which
gates each merge on it. As a result, the Implement loop ends when the code
agrees with the plan. It also stops on a result that occurs again, after three
Verify rounds, or when it needs a second revision.

## Considered Options

- Verify rounds that examine only the change since the last round. Rejected:
  they do not correct the cause. The causes are the time that CI takes and the
  checks without an end, and the limit to the contract of the plan removes both.
- Verify reports a stricter result when Ship calls it. Rejected: the saved
  report then changes with the caller, and Ship uses the report of the loop
  again.

## Consequences

- Ship, not Verify, refuses a plan while a task with a Closed by line is
  unticked. Verify lists that task as an outstanding observation.
- A plan has no step that only says that CI passes, and a search for leftover
  text examines only the files that the plan changes.
