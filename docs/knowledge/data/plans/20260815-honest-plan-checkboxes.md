---
type: plan
created: 2026-08-15
description: Make a ticked plan checkbox carry the evidence that closed it, split tasks that bundle outcomes, teach verify to test ticked boxes, and gate the format mechanically.
generated:
  by: claude-code/opus-5
  at: 2026-08-15T00:00:00Z
sources:
- .claude/skills/plan/SKILL.md
- .claude/skills/implement/SKILL.md
- .claude/skills/verify/SKILL.md
- docs/knowledge/data/bugs/plan-checkbox-over-claiming.md
---

# Make plan checkboxes carry their evidence

## Context

[Plan checkbox over-claiming](../bugs/plan-checkbox-over-claiming.md) records a
plan that asserted work which never happened: eight boxes flipped in one edit,
in a docs commit landed after the code, one of them a task beginning "Push" with
nothing pushed. `48d0f79` fixed the instance and left both root causes standing.

The causes are that a tick carries no evidence — so a blanket substitution and
eight careful verifications produce identical bytes — and that
`.claude/skills/verify/SKILL.md:24` audits unchecked boxes while taking ticked
ones on faith, inverting the severity `implement` itself states at
`.claude/skills/implement/SKILL.md:47`.

This also unblocks
[Verification in the main loop](../features/verification-in-the-main-loop.md):
making ship invoke verify only helps if verify has something to say about a
ticked box. That feature stays proposed; this plan gives it teeth to inherit.

## Approach

Change the shape of the artifact, not just the prose about it. Every `- [x]`
gains a required child line naming what closed it:

``` markdown
- [x] **3. Sync with `--locked` and enforce the interpreter.** Replace …
  - **Evidence:** `uv sync --locked --all-groups --all-extras` exits 0 on a cold
    runner; `validate-agent-files.yml` green at `8ca1eff`.
```

A find-and-replace can flip eight boxes; it cannot write eight evidence lines.
That makes the cheap wrong edit structurally awkward rather than merely
forbidden, and it gives verify and a linter something concrete to test. The
alternative considered and rejected was another round of prose rules in
`implement` — the rules that would have prevented this incident were already
written there, in almost the words the retrospective used, and were violated
anyway.

Alongside it, `plan` gains a task-atomicity rule (one task, one outcome; a task
whose evidence is external — a CI run, a deploy, a review — always stands alone,
because the session writing the code cannot close it), and `verify` gains the
missing `- [x]` counterpart to its unchecked-box CRITICAL.

The gate is a pytest over `docs/knowledge/data/plans/`, not an extension of
`validate_agent_files`: `data/product.md` `## Constraints` requires that package
to stay installable "with zero knowledge of this repository", and plan documents
are this workspace's knowledge graph, not agent files. It enforces shape only —
that a tick is accompanied by a claim — and can never check whether the claim is
true. Shape is what failed here.

The prose changes and the gate are one plan because the gate enforces exactly
the format the prose defines; splitting them would leave a specified format with
no enforcement, or an enforced format with nothing specifying it.

## Implementation Steps

### Task 1: Verify tests ticked boxes

**Files:** Modify: `.claude/skills/verify/SKILL.md`

- [x] **1. Give the Completeness dimension a `- [x]` counterpart.** After the
  existing unchecked-box rule at `.claude/skills/verify/SKILL.md:25-31`, add its
  mirror: a ticked task whose `**Evidence:**` line is missing, or whose evidence
  cannot be traced to a commit, test run, or CI run, is a CRITICAL with the
  recommendation "untick it". State the asymmetry being corrected so the rule
  survives editing: the unchecked-but-done box is a nuisance, the
  checked-but-not-done box is what the next session builds on.
  - **Evidence:** `.claude/skills/verify/SKILL.md:31-38` now carries the
    ticked-box CRITICAL with recommendation "untick it" and the stated
    asymmetry; `uv run validate_agent_files --kind skills .claude/skills --ci`
    exits 0.

### Task 2: Plan constrains task granularity

**Files:** Modify: `.claude/skills/plan/SKILL.md`

- [x] **2. Add the task-atomicity rule.** Under `## Rules`
  (`.claude/skills/plan/SKILL.md:93`), next to the existing "One plan per topic"
  rule at lines 95-96: one task is one outcome — if the task could ever be
  described as half-done, split it. A task whose evidence is external (a CI run,
  a deploy, a review, a published artifact) is always its own task, because the
  session that writes the code cannot close it. Name the failure it prevents so
  the rule reads as a lesson rather than a preference.
  - **Evidence:** `.claude/skills/plan/SKILL.md:103-109` states one task / one
    outcome, the standalone-task rule for externally-evidenced work, and the
    bundled-tick failure it prevents;
    `uv run validate_agent_files --kind skills .claude/skills --ci` exits 0.

### Task 3: Evidence gets a specified home

**Files:** Modify: `.claude/skills/plan/SKILL.md`

- [x] **3. Specify the evidence format and the results section.** In the section
  list at `.claude/skills/plan/SKILL.md:52-67`: extend the
  `## Implementation Steps` bullet (line 57) to state that each `- [ ]` carries
  an indented `- **Evidence:**` child once ticked, and add
  `## Verification results` to the ordered list, after `## Verification` —
  narrative evidence for the plan as a whole, written as the work happens. The
  section is already being improvised by sessions; this makes it specified
  rather than invented per plan.
  - **Evidence:** `.claude/skills/plan/SKILL.md:57-61` requires the indented
    `- **Evidence:**` child on a ticked box;
    `.claude/skills/plan/SKILL.md:68-70` adds `## Verification results` after
    `## Verification`;
    `uv run validate_agent_files --kind skills .claude/skills --ci` exits 0.

### Task 4: Implement ticks one box at a time

**Files:** Modify: `.claude/skills/implement/SKILL.md`

- [x] **4. Make the tick an evidence-writing step.** Rewrite step 5
  (`.claude/skills/implement/SKILL.md:30-34`) so ticking means writing the
  `- **Evidence:**` line in the same edit, and add to `## Rules` (line 55) that
  a single edit never changes more than one checkbox — a blanket `- [ ]` →
  `- [x]` substitution across the file is itself the defect, not a shortcut to
  the same result. Keep the existing same-commit rule at lines 61-62 and point
  it at the evidence line too.
  - **Evidence:** `.claude/skills/implement/SKILL.md:30-39` makes the tick and
    its evidence line one edit; `:66-70` adds the one-checkbox-per-edit rule;
    `:71-72` extends the same-commit rule to cover evidence lines;
    `uv run validate_agent_files --kind skills .claude/skills --ci` exits 0.

### Task 5: The convention reaches every session

**Files:** Modify: `docs/knowledge/AGENTS.md`

- [ ] **5. Record the evidence convention in the operating manual.** Add a
  `## Conventions` entry next to the existing "Code anchors" bullet: a ticked
  task carries the evidence that closed it. `AGENTS.md` loads every session
  while a skill loads only when invoked, so the convention needs to live in both
  or it binds only sessions that happen to run the skill.

### Task 6: The mechanical gate

**Files:** Create: `docs/knowledge/tests/test_plan_checkboxes.py`. Modify:
`pyproject.toml`

- [ ] **6a. Add the checkbox linter as a test.** Walk
  `docs/knowledge/data/plans/*.md` and assert two rules. **Evidence**: in a plan
  with no `stage` in frontmatter, every `- [x]` task line under
  `## Implementation Steps` is followed by an indented `- **Evidence:**` line
  with non-empty content. **Completeness**: a plan with `stage: done` has no
  `- [ ]` task lines. Closed plans are exempt from the evidence rule — they are
  historical records, and backfilling evidence into them would be inventing it,
  which is the sin under repair. Report every violation with `path:line`, not
  just the first. Cover both rules with fixture plans built in `tmp_path`, so
  the test does not depend on what this repository's own plans currently say.
- [ ] **6b. Register the new test path.** Add `docs/knowledge/tests` to
  `testpaths` in `pyproject.toml:29-32` so `uv run pytest` from the root picks
  it up.

### Task 7: Wire the gate into the local hooks

**Files:** Modify: `.pre-commit-config.yaml`

- [ ] **7. Add a `repo: local` hook.** Alongside the existing local hooks at
  `.pre-commit-config.yaml:68`, run the checkbox test with
  `entry: uv run pytest docs/knowledge/tests`, `language: system`,
  `pass_filenames: false`, filtered to
  `files: '^docs/knowledge/data/plans/.*\.md$'`. `uv run` on purpose, matching
  the reasoning already recorded above the `validate-agent-files` hook.

### Task 8: Wire the gate into CI

**Files:** Modify: `.github/workflows/validate-knowledge-base.yml`

- [ ] **8. Run the checkbox test in the knowledge-base job.** Add
  `./.github/actions/setup-python-venv` and a
  `uv run pytest docs/knowledge/tests` step after the normalization check at
  `.github/workflows/validate-knowledge-base.yml:80`. The job currently installs
  only `iwe`, so it needs the Python provisioning step; the existing
  `docs/knowledge/**` paths filter already covers the new test directory.

### Task 9: Close the loop on the related feature

**Files:** Modify:
`docs/knowledge/data/features/verification-in-the-main-loop.md`

- [ ] **9. Record what ship-invokes-verify does and does not catch.** Add to
  that feature's `## Behaviour` or `## Open questions` that the coupling only
  bites for defects verify can name, and that ticked-box over-claiming was
  invisible to it until Task 1 landed. Leave `stage: proposed` — this plan does
  not implement that feature.

## Spec changes

- `data/spec/plan-checkbox-evidence.md` — new. The contract the linter enforces:
  a ticked task carries an `**Evidence:**` line; a plan marked done has no
  unchecked tasks; closed plans are exempt from the evidence rule. Written at
  ship time, per the ship skill's spec-sync step.

## Verification

- `uv run pytest docs/knowledge/tests` passes, and its fixture cases prove the
  linter fails on a ticked box with no evidence line and on a `stage: done` plan
  with an unchecked box.
- `uv run pre-commit run --all-files` passes, including the new hook.
- `iwe normalize` followed by `git diff --exit-code` is clean — this is the real
  test of whether the nested `- **Evidence:**` bullet survives normalization.
- `iwe schema validate` exits 0.
- `actionlint` and `zizmor` pass on the changed workflow.
- Dogfood: this plan's own boxes are ticked with evidence lines as the work
  happens, so the gate runs against the format's first user before it runs
  against anything else. A plan that cannot satisfy its own rule is the rule
  failing, not the plan.

## Out of scope

- Making ship invoke verify — that is
  [Verification in the main loop](../features/verification-in-the-main-loop.md),
  still `stage: proposed`. This plan only removes the reason it would have been
  toothless.
- Backfilling evidence lines into `stage: done` plans. The four closed plans
  stay as written. The two other live plans
  ([PR verification sections](20260815-pr-verification-sections.md),
  [structured spec deltas](20260816-structured-plan-spec-deltas.md)) have no
  ticked task, so nothing needs migrating — checked 2026-08-16.
- Checking whether an evidence claim is *true*. The gate reads shape. Judging
  the claim is verify's job, and a human's.
- The `agentdev` catalog skills under `.agents/plugins/agentdev/skills/` — they
  do not use plan checkboxes and are validated by a different gate.

## Key references

Verified anchor points (line numbers as of 2026-08-16, at `1d3021f`; the
2026-08-15 numbers were taken at `8ca1eff`, before the
[workflow skill contracts](20260815-strengthen-workflow-skill-contracts.md) and
[handoff routes](20260816-skill-handoff-routes.md) plans shipped into the same
four files):

- `.claude/skills/verify/SKILL.md:25-31` — the unchecked-box CRITICAL and its
  three routes, with no ticked-box counterpart
- `.claude/skills/verify/SKILL.md:71` — `## Rules`
- `.claude/skills/plan/SKILL.md:57` — the `## Implementation Steps` section
  description
- `.claude/skills/plan/SKILL.md:63` — the `## Verification` section description,
  where `## Verification results` follows
- `.claude/skills/plan/SKILL.md:93-96` — `## Rules`, "One plan per topic"
- `.claude/skills/implement/SKILL.md:30-34` — step 5, where ticking happens
- `.claude/skills/implement/SKILL.md:57-60` — "a checked box that isn't done is
  a lie the next session builds on"
- `.claude/skills/implement/SKILL.md:61-62` — checkbox flips share the code's
  commit
- `pyproject.toml:29-32` — `testpaths`
- `.pre-commit-config.yaml:68` — `repo: local` hooks
- `.github/workflows/validate-knowledge-base.yml:80` — the normalization check,
  where the pytest step follows

## Risks

- **~~`iwe normalize` may flatten the nested evidence bullet.~~ Retired during
  planning.** Checked on 2026-08-15 by adding an indented `- **Evidence:**`
  bullet under a task checkbox in this document and running `iwe normalize`: it
  came back byte-identical, at the same indentation. The format is safe for the
  CI normalization check. Should a future `iwe` version change this, the
  fallback is a `**Evidence:**` continuation paragraph inside the task block,
  matched by the linter with the same rule minus the list marker.
- **A shape gate invites shape compliance.** Nothing stops an evidence line that
  says "done". The linter cannot help there; Task 1 is what makes an empty claim
  a CRITICAL, which is why the verify change leads the plan rather than trailing
  it.
- **The knowledge-base workflow grows a Python dependency.** It currently
  installs only `iwe` and runs in well under a minute. Adding
  `setup-python-venv` makes it slower and couples it to the provisioning path
  that [Finish uv-run-only in CI](20260815-uv-run-in-ci.md) has just changed.
  Accepted: the alternative is a gate that only runs on machines with hooks
  installed.
