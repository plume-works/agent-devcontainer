---
type: plan
created: 2026-11-13
release: internal
description: Write an ADR for each decision in the specs that passes the three ADR conditions, put each short invariant in a code comment, point the code comments at ADRs, and remove every Rationale section.
sources:
- resource: docs/spec-audit/rationale.jsonl
- resource: docs/spec-audit/requirements.jsonl
- resource: AGENTS.md
---

# Move the decisions from the specs into ADRs

## Context

The reasons behind the code are in the `## Rationale` sections of `data/spec/`
and in some requirements. [The spec usefulness
audit](../findings/spec-usefulness-audit.md) counted 189 `## Rationale` entries,
21 requirements that hold a decision, and 13 requirements that hold a short
invariant. The labels are in `docs/spec-audit/`. Code comments cite a spec as
`spec/<key>`, as rule 3 in `AGENTS.md#comments` tells them to.

This plan is the second removal step of [Shrink the knowledge base to an issue
tracker and decision
records](../backlog/shrink-knowledge-base-to-issues-and-adrs.md). After it, no
reason is only in a spec.

## Approach

Each `## Rationale` entry and each requirement whose `fate` is `adr` is judged
against the three conditions for an ADR: hard to reverse, surprising without
context, and the result of a real trade-off. A decision that passes gets an ADR
in the short format. A decision that fails gets no ADR, and its text is removed.
One ADR can hold several entries that record one decision.

The ADRs are written at `stage: accepted` by the session that does the tasks.
Each one records a decision that is in force already, so Plan does not propose
it and Ship does not accept it. The pull request review is the check.

A requirement whose `fate` is `code-comment` becomes a comment of 3 lines or
fewer at its implementation.

A code comment that cites `spec/<key>` cites the ADR as `ADR-NNNN`. If the
decision got no ADR, the citation is removed.

## Implementation Steps

### Task 1: Write the ADRs

**Files:** Create: the documents under `docs/knowledge/data/adr/`; Modify:
`docs/knowledge/data/adr.md`

- [ ] Each `## Rationale` entry in `data/spec/` whose decision passes the three
  conditions has its decision and its reason in an ADR.
- [ ] Each requirement whose `fate` is `adr`, and whose decision passes the
  three conditions, has its decision and its reason in an ADR.
- [ ] Each ADR lists a rejected option only when the rejection is not obvious.
- [ ] Each ADR is at `stage: accepted`, passes the schema, and has a link in
  `data/adr.md`.
- [ ] Each ADR agrees with the code. The entries whose `accurate` is not `true`
  in `docs/spec-audit/rationale.jsonl` were read against the code first.

### Task 2: Put the short invariants in code comments

**Files:** Modify: the implementation file of each requirement whose `fate` is
`code-comment`

- [ ] Each of the 13 requirements whose `fate` is `code-comment` has its
  invariant in a comment at its implementation, as its `fate_note` says.
- [ ] No such comment is longer than 3 lines.

### Task 3: Point the code comments at ADRs

**Files:** Modify: each file outside `docs/` that cites `spec/<key>`,
`AGENTS.md`, `docs/knowledge/AGENTS.md`

- [ ] No file outside `docs/` cites `spec/<key>`.
- [ ] Each citation that replaced one names an ADR that states the cited
  decision.
- [ ] Rule 3 in `AGENTS.md#comments` names ADRs as the home of a decision and
  `ADR-NNNN` as the reference. It names no spec and no `## Rationale`.
- [ ] `docs/knowledge/AGENTS.md#conventions` names no `## Rationale`.

### Task 4: Remove the text that moved

**Files:** Modify: the documents under `docs/knowledge/data/spec/`,
`docs/knowledge/data/spec.md`

- [ ] No spec has a `## Rationale` section.
- [ ] No requirement whose `fate` is `adr` or `code-comment` is in `data/spec/`.
- [ ] Each spec that has no requirement is deleted with `iwe delete`.
- [ ] No document outside `data/archive/` links a spec that was deleted.

## Acceptance

None — no behavioral change

## Depends on

[Remove the spec text that is redundant or
wrong](../archive/next-release/plans/20261113-remove-redundant-and-wrong-spec-text.md)

## Verification

``` bash
iwe normalize && iwe schema validate
uv run scripts/check-anchors.py
uv run pytest docs/knowledge/tests
```

## Out of scope

- The requirements that wait for a test.
- The removal of `data/spec/`, its schema, and its hub.
- A decision that no spec records.

## Key references

- `docs/spec-audit/rationale.jsonl` — one row for each `## Rationale` entry,
  with `kind`, `accurate`, and `rejected_count`.
- `docs/spec-audit/requirements.jsonl` — the rows whose `fate` is `adr` or
  `code-comment`, with `fate_note`.
- `AGENTS.md#comments` — rule 3, which sends a comment to a spec.
- `docs/knowledge/AGENTS.md#conventions` — the home of each kind of knowledge.
- `docs/knowledge/data/spec.md` — the hub that loses the deleted specs.
