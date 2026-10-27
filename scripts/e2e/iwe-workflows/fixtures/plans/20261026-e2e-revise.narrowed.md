---
type: plan
created: 2026-10-26
release: internal
description: Fixture plan whose spec outcome names a file no task writes, for checking that Implement revises its plan.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T12:00:00Z
---

# E2E revise fixture

## Context

A fixture plan for exercising Implement's evaluated revision end to end.

## Approach

Add `e2e/revise.txt` holding `revise`.

## Implementation Steps

### Task 1: Add the revise file

**Files:** Create: `e2e/revise.txt`

- [ ] Write `e2e/revise.txt` containing `revise`.

## Spec changes

`e2e-revise` — the fixture SHALL provide `e2e/revise.txt` containing exactly
`revise`.

## Verification

- `grep -qx revise e2e/revise.txt`

## Out of scope

- Any file the spec outcome does not name.
- `e2e/revise-notes.txt`.
