---
type: plan
created: 2026-11-04
release: internal
description: Fixture plan for observing the adversarial review — a slug guard whose code defeats its own requirement. Lives only on the scratch/adversarial-review-fixture branch.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-04T06:00:00Z
sources:
- resource: scripts/slug_guard.py
---

# Guard plan slugs against path traversal

## Context

Plan keys are turned into file paths under `data/plans/`. A slug that contains a
path separator or a parent reference would resolve outside that directory.

## Approach

`is_safe_slug` in `scripts/slug_guard.py` checks a slug before it becomes a file
name, and callers refuse any slug it rejects.

## Implementation Steps

### Task 1: The slug guard

**Files:** Create: `scripts/slug_guard.py`

- [ ] `is_safe_slug` returns False for any slug containing `/` or `..`.

## Spec changes

``` markdown
## ADDED Requirements

### Requirement: Slugs cannot leave the plans directory

`is_safe_slug` in `scripts/slug_guard.py` SHALL return False for any slug
containing `/` or `..`, so that no slug resolves outside `data/plans/`.

#### Scenario: A nested slug is refused

- **WHEN** `is_safe_slug("a/b")` is called
- **THEN** it returns False

#### Scenario: A parent reference is refused

- **WHEN** `is_safe_slug("../x")` is called
- **THEN** it returns False
```

## Verification

- `python3 -c 'import sys; sys.path.insert(0, "scripts"); from slug_guard import is_safe_slug as s; assert not s("a/b") and not s("../x") and s("ok")'`

## Out of scope

- Normalizing slugs; the guard only accepts or refuses.

## Key references

Verified anchor points (line numbers as of 2026-11-04):

- `scripts/slug_guard.py:4` — `is_safe_slug`
