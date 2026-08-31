---
type: plan
created: 2026-08-31
---

# Critical docs and durable-knowledge review in pr-review

## Context

The `pr-review` skill currently auto-approves docs-only diffs: its Step 1 Gate
lumps `docs-only` together with `version-only` and `generated-file-only` and
publishes a clean `APPROVE` without launching any review pass. Documentation and
skills therefore ship without scrutiny, and the durable-knowledge discipline
that `AGENTS.md` Best Practice 8 and the `/agentdev:iwe-audit` skill enforce
never runs at review time.

The maintainer wants docs and skills reviewed critically — with a special focus
on durable knowledge in the IWE graph — while keeping the fast-approve path for
genuinely mechanical diffs (Renovate digest bumps, generated files).

## Approach

The durable-knowledge criteria the docs review needs already live in
`/agentdev:iwe-audit`: the durable-vs-not test, the smell patterns (§1), the
verdicts DROP/MOVE/REWRITE/KEEP (§2), and the verify discipline (§3). Rather
than restate any of that in `pr-review`, teach `iwe-audit` a **diff scope** and
have `pr-review` invoke it.

- **iwe-audit gains a diff scope.** Its §4 flow is already two-phase — report a
  table, wait for approval, then apply. In diff mode the candidate set is the
  diff's changed lines (not a grep over `<TARGET>`), and the skill is
  **report-only**: it produces the §4 findings table and stops before applying.
  Every verdict stays a recommendation — MOVE names a destination, DROP/REWRITE
  quote the replacement — but the changed lines are left untouched; applying is
  the caller's decision. §1 patterns, §2 verdicts, §3 verify, and the §4 table
  format are all reused unchanged.
- **pr-review invokes iwe-audit diff mode.** The docs lens runs iwe-audit in
  diff mode over the changed docs/skills files, reads the returned
  `file:line | verdict | replacement | evidence` table, and maps each row to an
  inline review comment. The table is already `file:line`-anchored, so the
  mapping is mechanical. iwe-audit stays ignorant of GitHub; the review-pipeline
  coupling lives in pr-review.
- **pr-review adds only what is its own:** the quote-the-rule high-signal bar
  (iwe-audit audits exhaustively; a PR reviewer must clear the anti-nitpick
  threshold the rest of the skill enforces) and the row→comment/severity
  mapping.
- **Narrow the Step 1 gate** to `version-only` and `generated-file-only`; drop
  `docs-only`.
- **The lens follows the file, not the PR:** on a mixed docs+code diff, code
  files get the correctness lens and docs/skills files get the durable-knowledge
  lens, in the same review.
- **Fan-out stays a conditional 5th pass:** always 2 compliance + 2 correctness;
  add 1 durable-knowledge pass only when the diff contains docs/skills files,
  preserving full code-correctness coverage rather than repurposing a
  correctness slot.
- **Durable-knowledge findings are blocking (critical/P1)**, the same tier as
  correctness, so they win Step-4 dedup collisions. This does not change the
  submit event: Step 8 still caps at `COMMENT`, never `REQUEST_CHANGES`.

Rejected alternative: restate the durable-knowledge criteria inline in
`pr-review`. Rejected because it duplicates the durable-vs-not test, the smell
list, the verdicts, and the verify discipline that iwe-audit already owns — two
copies that drift. Teaching iwe-audit a diff scope keeps them in one place.

Rejected alternative: give iwe-audit a distinct "review" mode that emits GitHub
review comments directly. Rejected because it would put GitHub review mechanics
inside a durable-knowledge auditor. iwe-audit's report-only diff mode emits its
normal table; pr-review does the row→comment translation where the rest of the
review pipeline lives.

Rejected alternative: repurpose one of the two correctness passes for
durable-knowledge on mixed diffs. Rejected because it dilutes code-correctness
coverage on code-heavy PRs; a conditional 5th pass keeps both.

## Implementation Steps

### Task 1: Teach iwe-audit a report-only diff scope

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md`

Add a diff scope to iwe-audit as two insertions into the existing structure — no
new top-level mode taxonomy. Near `## Scope`, state that in diff mode the
candidate set is the diff's changed lines rather than a grep over `<TARGET>`,
and that §1's patterns are the smell list applied to those added lines. In
`## 4. Report, then apply`, state that diff mode stops at the report table and
does not apply: every verdict is a recommendation (MOVE names the destination,
DROP/REWRITE quote the replacement) and the changed lines are left untouched,
because applying is the caller's decision made outside this skill. Leave
§"Durable vs not", §1 patterns, §2 verdicts, and §3 verify unchanged and shared
by both scopes.

- [x] iwe-audit documents a report-only diff scope: candidates = changed lines,
  stops at the §4 table, applies nothing; shared criteria/verdicts/verify
  untouched.
  - **Evidence:** Two additive insertions in
    `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md` — a "Diff scope"
    paragraph under `## Scope` (candidates = added lines; §"Durable vs
    not"/§2/§3 shared) and a "Diff scope stops here" paragraph under `## 4`
    (report-only, changed lines untouched). `validate_agent_files` passes 43/43,
    0 errors.

### Task 2: Add the Documentation focus lens invoking iwe-audit diff mode

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

Add a **Documentation focus** block to the Review Focus section (after
Correctness focus, currently ending at line 65). It applies to docs under
`data/`, `README.md`, `AGENTS.md`, skill and agent definitions (`SKILL.md`,
`*.agent.md`), and docstrings. Instead of restating criteria, it directs the
lens to run `/agentdev:iwe-audit` in diff mode over the changed docs/skills
files, take the returned `file:line | verdict | replacement | evidence` table,
and map each row to an inline review comment. State the pr-review-specific
high-signal bar: flag a finding only when you can quote the added line and name
the specific rule it breaks — the same anti-nitpick threshold the compliance
lens uses — so exhaustive iwe-audit findings are filtered to review-worthy ones.

- [x] A **Documentation focus** block invokes iwe-audit diff mode, maps its
  table rows to inline comments, and states the quote-the-rule high-signal bar;
  it restates no durable-knowledge criteria.
  - **Evidence:** New **Documentation focus** block in
    `.agents/plugins/agentdev/skills/pr-review/SKILL.md` after the Correctness
    material — runs `/agentdev:iwe-audit` in diff mode over changed docs/skills
    files, maps each `file:line | verdict | replacement` row to an inline
    comment, and states the quote-the-line/name-the-rule bar. No criteria
    restated. `validate_agent_files` 43/43, 0 errors.

### Task 3: Place durable-knowledge findings in the severity taxonomy

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

In the Severity tiers block (lines 67–70), add durable-knowledge findings to the
**Blocking (critical/P1)** tier alongside correctness. Clarify — reusing the
existing Step-8 wording — that the tier governs Step-4 dedup priority and inline
emphasis only, and never changes the submit event (still `COMMENT`, never
`REQUEST_CHANGES`).

- [x] Blocking tier lists durable-knowledge findings; the note that tier does
  not change the submit event is present.
  - **Evidence:** The **Blocking (critical/P1)** tier in
    `.agents/plugins/agentdev/skills/pr-review/SKILL.md` now names the
    durable-knowledge pass alongside correctness, with the note that the tier
    governs Step-4 dedup and inline emphasis only and never changes the submit
    event (stays `COMMENT`, never `REQUEST_CHANGES`, per Step 8).

### Task 4: Make Step 3 fan-out conditional and file-following

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

Update Step 3 (lines 81–86): keep the always-on 2 compliance + 2 correctness
passes, and add a **durable-knowledge pass that runs only when the diff contains
docs/skills files**. State the file-following rule: correctness passes scan code
files, the durable-knowledge pass scans docs/skills files, each ignoring files
outside its lens; on a mixed diff both lenses run against their own file subsets
in the same review. Update the "four independent" framing to "four or five".

- [x] Step 3 documents the conditional 5th durable-knowledge pass and the
  per-file lens split.
  - **Evidence:** Step 3 in `.agents/plugins/agentdev/skills/pr-review/SKILL.md`
    reframed to "four or five" passes: 2 compliance + 2 correctness always, plus
    1 durable-knowledge pass only when the diff contains docs/skills files. The
    "lens follows the file" rule splits code files to correctness and
    docs/skills to durable-knowledge, each ignoring files outside its lens. Step
    1 gate also narrowed to version-only/generated-only (docs-only no longer
    fast-approved).

### Task 5: Update the parallel-pass budget wording

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

In "Waiting on Parallel Passes" (lines 100–117), extend the pass-count language
from "4" to "4 or 5" (line 117 completion-count status line; the "per Step-3
pass" budget at line 116). The durable-knowledge pass gets the same 16-minute
ceiling as the other Step-3 passes.

- [x] Budget and completion-count wording accommodate the optional 5th pass at
  the same 16-minute ceiling.
  - **Evidence:** "Waiting on Parallel Passes" in
    `.agents/plugins/agentdev/skills/pr-review/SKILL.md` — per-pass budget now
    states the durable-knowledge pass gets the same 16-minute ceiling, and the
    completion-count status line reads "4 or 5 initial passes".

### Task 6: Request an AI review of the change

**Files:** none (external action)

Once Tasks 1–5 land and the PR is open, request an AI review so the edited
`pr-review` and `iwe-audit` skills are themselves exercised under the new docs
lens (per `/agentdev:pr-request-ai-review`). This closes the loop and is why the
new prose in Tasks 1–5 must be free of session residue by its own rule.

- [ ] AI review requested and a responder run confirmed picked it up.

## Spec changes

None — no behavioral change to any `data/spec/` contract.
`data/spec/ai-review-gate` governs whether a review is *present* and whether the
responder may act; a pr-review that emits `APPROVE` or `COMMENT` still satisfies
that gate unchanged. This plan changes only the pr-review skill's internal
review policy and adds a report-only scope to iwe-audit — neither of which any
`data/spec/` doc specifies.

## Verification

- Read the edited `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md` and
  confirm: a diff scope with changed-lines candidates is documented near
  `## Scope`; `## 4` states diff mode is report-only and applies nothing;
  §"Durable vs not", §1, §2, §3 are unchanged.
- Read the edited `.agents/plugins/agentdev/skills/pr-review/SKILL.md` end to
  end and confirm: Step 1 fast-approves only version-only/generated-only; a
  Documentation focus block invokes iwe-audit diff mode and maps its table to
  inline comments with the quote-the-rule bar, restating no criteria;
  durable-knowledge is in the Blocking tier with the no-event-change note; Step
  3 documents the conditional 5th pass and file-following split; the budget
  wording says "4 or 5".
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes (catalog validation, per `.agents/AGENTS.md`).
- The new prose in both skills passes its own durable-knowledge lens: grep the
  added lines with the `/agentdev:iwe-audit` seed patterns and confirm no
  session residue.

## Out of scope

- Any change to `version-only` / `generated-file-only` fast-approve behavior.
- Any change to `data/spec/ai-review-gate` or the require-ai-review / responder
  workflows.
- Changing the submit-event rule (`COMMENT`/`APPROVE`/never `REQUEST_CHANGES`).
- Changing iwe-audit's existing local-tree behavior, its criteria, verdicts, or
  verify discipline — diff mode adds a scope and a report-only stop, nothing
  more.
- Having iwe-audit emit GitHub review comments itself; pr-review owns the
  table→comment translation.

## Key references

Verified anchor points (line numbers as of 2026-08-31):

- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:22` — `## Scope`
  (diff-mode candidate-set note goes here)
- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:34` —
  `## 1. Collect candidates` (grep patterns shared by both scopes)
- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:88` —
  `## 4. Report, then apply` (report-only stop for diff mode)
- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:90` — "Output a table
  before editing anything" — the report/apply phase boundary
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:74` — Step 1 Gate
  (draft/closed check)
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:75` — "docs-only,
  version-only, or generated-file-only" enumeration to narrow
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:46` — Correctness focus
  block (new Documentation focus follows)
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:67` — Severity tiers block
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:80` — Step 2
  convention-source selection (per-file skill mapping)
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:81` — Step 3 "four
  independent initial-review passes"
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:92` — Step 8 event rule
  (APPROVE/COMMENT)
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:116` — per-pass 16-minute
  budget
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:117` — "4 initial passes"
  completion-count status line
- `docs/knowledge/data/spec/ai-review-gate.md:14` — ai-review-gate requirement
  (unchanged by this plan)
