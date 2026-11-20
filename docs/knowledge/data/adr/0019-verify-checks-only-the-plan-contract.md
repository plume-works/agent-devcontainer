---
type: adr
stage: accepted
description: Verify reports only what contradicts the plan, CI stays with pr-merge, and the Implement session stops at a fixed limit.
---

# Verify checks only what the plan promised

Verify is a conformance check. Each `CRITICAL` or `WARNING` result cites the
requirement, scenario, task, or verification step of the plan that the code
contradicts, and CI belongs to `pr-merge`, which gates every merge on it. As a
result, the Implement session converges once the code meets the plan's contract,
and the run is bounded: it stops on a recurring result, after three Verify
rounds, or when it would need a second revision.

## Considered Options

- Delta-scoped Verify rounds, which examine only the change since the last
  round. Rejected: they treat the symptom. Restricting findings to the plan's
  contract and leaving CI to the merge gate remove its causes, CI timing and
  unbounded probing.
- Verify treats an outstanding observation as `CRITICAL` only when Ship calls
  it. Rejected: the saved report would then differ by caller, and Ship reuses
  the report of the Implement session.
