---
type: plan
created: 2026-11-13
release: internal
description: Write an ADR for each decision in the specs that passes the three ADR conditions, put each short invariant in a code comment, point the code comments at ADRs, and remove every Rationale section.
sources:
- resource: docs/spec-audit/rationale.jsonl
- resource: docs/spec-audit/requirements.jsonl
- resource: AGENTS.md
stage: done
completed: 2026-11-14
---

# Move the decisions from the specs into ADRs

## Context

The reasons behind the code are in the `## Rationale` sections of `data/spec/`
and in some requirements. [The spec usefulness
audit](../../../findings/spec-usefulness-audit.md) counted 189 `## Rationale`
entries, 21 requirements that hold a decision, and 13 requirements that hold a
short invariant. The labels are in `docs/spec-audit/`. Code comments cite a spec
as `spec/<key>`, as rule 3 in `AGENTS.md#comments` tells them to.

This plan is the second removal step of [Shrink the knowledge base to an issue
tracker and decision
records](../../../backlog/shrink-knowledge-base-to-issues-and-adrs.md). After
it, no reason is only in a spec.

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

- [x] Each `## Rationale` entry in `data/spec/` whose decision passes the three
  conditions has its decision and its reason in an ADR.
  - **Evidence:** All 186 entries were judged against the three conditions. 102
    of them are in ADR-0003 to ADR-0091, and the other 84 fail a condition. A
    script confirmed that each `###` entry under each `## Rationale` has a
    judgement.
- [x] Each requirement whose `fate` is `adr`, and whose decision passes the
  three conditions, has its decision and its reason in an ADR.
  - **Evidence:** 19 of the 21 requirements are in an ADR. One fails condition 2
    and condition 3. The code contradicts the other, "The plugin is published
    but not enabled by default", because the runtime enables the plugin.
- [x] Each ADR lists a rejected option only when the rejection is not obvious.
  - **Evidence:** Each draft dropped the spec's obvious rejections, and some
    ADRs have no `## Considered Options`. A full reading of ADR-0041, 0047,
    0055, 0059, 0066, 0070, and 0086 found no rejection that is obvious.
- [x] Each ADR is at `stage: accepted`, passes the schema, and has a link in
  `data/adr.md`.
  - **Evidence:** `iwe schema validate` passes, the hub links all 89 new ADRs,
    and `uv run pytest docs/knowledge/tests` passes (102 tests).
- [x] Each ADR agrees with the code. The entries whose `accurate` is not `true`
  in `docs/spec-audit/rationale.jsonl` were read against the code first.
  - **Evidence:** Each ADR was written from the code in the current checkout.
    Where an entry differs from the code, the ADR states what the code does or
    the entry gets no ADR, as for the agent metadata and the session ID file.

### Task 2: Put the short invariants in code comments

**Files:** Modify: the implementation file of each requirement whose `fate` is
`code-comment`

- [x] Each of the 13 requirements whose `fate` is `code-comment` has its
  invariant in a comment at its implementation, as its `fate_note` says.
  - **Evidence:** Added the comment that each `fate_note` names in 13 files. The
    macOS bootstrap already had its comment. The pre-commit hooks pass on the
    changed files, and `test_integrity.py` and `test_coder_agent_start.py` pass.
- [x] No such comment is longer than 3 lines.
  - **Evidence:** Each new comment has 1 or 2 lines. The two longest comment
    blocks have 3 lines, in the two Dockerfiles and in `devcontainer.json`.

### Task 3: Point the code comments at ADRs

**Files:** Modify: each file outside `docs/` that cites `spec/<key>`,
`AGENTS.md`, `docs/knowledge/AGENTS.md`

- [x] No file outside `docs/` cites `spec/<key>`.
  - **Evidence:** 112 citations in the `spec/<key>`, `Spec: <key>`, and link
    forms were changed. `git grep -E "spec/[a-z][a-z-]+|Spec:" -- ':!docs'` now
    finds only test fixtures and the `data/spec/` directory itself.
- [x] Each citation that replaced one names an ADR that states the cited
  decision.
  - **Evidence:** Each comment was read with its context and matched to the ADR
    of its decision. A comment whose decision got no ADR lost its citation. The
    pre-commit hooks and 291 tests pass on the changed files.
- [x] Rule 3 in `AGENTS.md#comments` names ADRs as the home of a decision and
  `ADR-NNNN` as the reference. It names no spec and no `## Rationale`.
  - **Evidence:** Removed the sentence that permitted a `spec/<key>` reference.
    The rule now names only ADRs.
- [x] `docs/knowledge/AGENTS.md#conventions` names no `## Rationale`.
  - **Evidence:** `grep Rationale docs/knowledge/AGENTS.md` finds nothing, so
    the section needed no change.

### Task 4: Remove the text that moved

**Files:** Modify: the documents under `docs/knowledge/data/spec/`,
`docs/knowledge/data/spec.md`

- [x] No spec has a `## Rationale` section.
  - **Evidence:** A script removed each `## Rationale` section, and
    `grep -l "## Rationale" docs/knowledge/data/spec/` finds nothing.
- [x] No requirement whose `fate` is `adr` or `code-comment` is in `data/spec/`.
  - **Evidence:** The same script removed the 34 requirements with their
    scenarios and reported no title that it did not find. One requirement has a
    new title in the spec, "The catalog publishes the plugin and the runtime
    enables it".
- [x] Each spec that has no requirement is deleted with `iwe delete`.
  - **Evidence:** `iwe delete` removed the 25 specs with no requirement. 15
    specs stay, and each has at least one requirement.
- [x] No document outside `data/archive/` links a spec that was deleted.
  - **Evidence:** `iwe delete` turned each link into text. The guide
    `claude-remote-control-setup` now links ADR-0077 and ADR-0078.
    `iwe schema validate` and `scripts/check-anchors.py` pass.

## Acceptance

None — no behavioral change

## Depends on

[Remove the spec text that is redundant or
wrong](20261113-remove-redundant-and-wrong-spec-text.md)

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

## Ship review

`iwe-ship-reviewer` did this review on 2026-11-14.

- [x] Verify found no CRITICAL problem — correct: Ready to ship —
  data/plans/20261113-move-decisions-into-adrs
- [x] Every ADR that the plan proposed is `stage: accepted` — not applicable:
  the plan proposed no ADR
- [x] Every ADR that the plan superseded is `stage: superseded` and in the
  archive — not applicable: the plan superseded no ADR
- [x] The plan is `stage: done` with `completed` and no `rank` — correct:
  2026-11-14
- [x] Every feature in `release` is `stage: implemented` — not applicable:
  `release` lists no feature
- [x] Every bug in `release` is `stage: done` with no `rank` — not applicable:
  `release` lists no bug
- [x] Every bug in `release` has a `## Fix` that links this plan — not
  applicable: `release` lists no bug
- [x] The plan and every feature and bug that it completed are in the archive,
  and no hub links them — correct:
  data/archive/next-release/plans/20261113-move-decisions-into-adrs
