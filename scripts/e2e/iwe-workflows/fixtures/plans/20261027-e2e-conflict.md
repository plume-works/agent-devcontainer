---
type: plan
created: 2026-10-27
release: internal
description: Fixture plan whose spec outcome contradicts itself, so any revision that completes it narrows agreed behavior.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T12:00:00Z
---

# E2E conflict fixture

## Context

A fixture plan for exercising Implement's stop on a revision that would narrow
agreed behavior.

## Approach

Add `e2e/conflict.txt` holding `yes`.

## Implementation Steps

### Task 1: Add the conflict file

**Files:** Create: `e2e/conflict.txt`

- [ ] Write `e2e/conflict.txt` containing `yes`.

## Spec changes

`e2e-conflict` — `e2e/conflict.txt` SHALL be a single line containing exactly
`yes`, and `e2e/conflict.txt` SHALL be a single line containing exactly `no`.

## Verification

- `grep -qx yes e2e/conflict.txt`
- `grep -qx no e2e/conflict.txt`

## Out of scope

- Any other file.
