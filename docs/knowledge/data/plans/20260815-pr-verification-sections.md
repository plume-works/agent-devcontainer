---
type: plan
created: 2026-08-15
description: Replace How to Test with Verification and Reviewer Handoff across the PR template and the three agentdev skill sites that write or update it.
generated:
  by: claude-code/opus-5
  at: 2026-08-15T00:00:00Z
sources:
- .github/pull_request_template.md
- .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- .agents/plugins/agentdev/skills/code-review-standards/SKILL.md
---

# Split PR How to Test into Verification and Reviewer Handoff

## Context

[PR verification sections](../architecture/pr-verification-sections.md) decides
that a pull request body splits `## How to Test` into two sections:
`## Verification`, holding closed items as checked boxes with an `**Evidence:**`
child, and `## Reviewer Handoff`, holding open items as unchecked boxes with a
`**Closed by:**` child. Both sections omit what an automated check already
covers, and reference rather than restate what another document owns. This plan
carries that decision into the four places that define the section.

The decision records the failure that motivated it: PR #61's `## How to Test`
held six numbered items spanning three moods — a state to observe, commands
already run, and instructions for the reader — under one heading, four of them
restating work CI already performs. Applying the two filters collapses that
section to two items, both manual-only.

The underlying principle is
[evidence and outstanding work](../concept/evidence-and-outstanding-work.md).
The plan-document instance of the same defect is
[plan checkbox over-claiming](../bugs/plan-checkbox-over-claiming.md), whose
plan —
[Make plan checkboxes carry their evidence](20260815-honest-plan-checkboxes.md)
— establishes the `**Evidence:**` child-line vocabulary this reuses
deliberately.

## Approach

Change the template first, then the skills that fill it, so no intermediate
commit has a skill instructing a section the template does not contain.

The section format is the easy half. The hard half is the two filters, because
applying them requires knowing what CI covers — and the skill that generates the
body currently instructs the opposite. `pr-gen-description` Step 5 says "Assess
Testing Strategy: Unit tests, integration tests, manual testing, coverage
impact", which invites exactly the transcript of automated runs the decision
removes. Step 5 is therefore a fourth site, not merely a fourth mention: it must
tell the author to read `.github/workflows/` and treat everything CI runs as
excluded, keeping only the residue.

The rejected alternative is a rename-only edit at each site, leaving the prose
that feeds the sections untouched. That was already rejected at the decision
level (it leaves past and future in one list), and it fails harder here: the
sections would be correctly named and still filled with CI transcripts, because
Step 5 would still be asking for them.

Enforcement is prose only. Unlike the plan-checkbox format, no gate is possible
— PR bodies live on GitHub and are not in the graph — so the format must stay
simple enough to hold by hand, and each site must state the rule rather than
assume the neighbouring site does.

## Implementation Steps

### Task 1: Template

**Files:** Modify: `.github/pull_request_template.md`

- [ ] **1. Replace the `## How to Test` block with the two sections.** Swap
  lines 16-20 for `## Verification` and `## Reviewer Handoff`, each with a
  commented example showing one item in the required shape (`- [x]` +
  `**Evidence:**`; `- [ ]` + `**Closed by:**`). State in the template that
  `## Verification` is often empty when CI covers the change, so an author does
  not read emptiness as an omission to fill.

### Task 2: Generation skill

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md`

- [ ] **2. Rewrite Step 5 to select rather than inventory.** Replace the current
  "Assess Testing Strategy" line (`:88-90`) with instructions to read
  `.github/workflows/` for what CI already runs on the branch, then keep only
  what survives both filters — no linter, formatter, image build, or test suite
  CI executes, and no restatement of a plan's own verification record.
- [ ] **3. Replace the `How to Test` entry in the Step 7 section list.** At
  `:105`, substitute the two sections with one-line definitions distinguishing
  them by tense, so a repository with no template of its own gets the same
  structure.
- [ ] **4. Add the empty-section and unclosable-item edge cases.** In
  `## Edge Cases` (`:114-121`), record that an empty `## Verification` under
  green CI is the expected outcome rather than a gap to fill, and that an item
  no reviewer can close still belongs under `## Reviewer Handoff` with its
  closer named. Reconcile the existing "**No tests**: Warn incomplete testing
  section" bullet, which otherwise contradicts both.

### Task 3: Review standards skill

**Files:** Modify:
`.agents/plugins/agentdev/skills/code-review-standards/SKILL.md`

- [ ] **5. Rewrite the worked example.** Replace step 4 of
  `### Recommended Template` (`:75-83`) — the `## How to Test` heading and its
  three-command example — with both sections in the required shape. The example
  is what most readers copy, so it must show an `**Evidence:**` line and a
  `**Closed by:**` line rather than describe them.
- [ ] **6. Update the feedback-loop instruction.** At `:180`, "Update 'How to
  Test' if testing changes" becomes an instruction naming both sections, and
  states the direction items travel: work closed since the last review moves
  from `## Reviewer Handoff` to `## Verification` with its evidence, never the
  reverse.

### Task 4: Breaking-change record

**Files:** Modify: `docs/knowledge/data/log.md`

- [ ] **7. Record the change as a downstream break.** The `agentdev` plugin
  ships to template consumers, so a consuming repository's own
  `pull_request_template.md` keeps `## How to Test` while its skills instruct
  two different sections. Note the mismatch and that consumers adopt by copying
  the new template, in the same register as the `setup-python-venv` activation
  break.

## Spec changes

None. No `data/spec/` document covers pull request body structure:
`template-consumption.md` governs what a consuming repository copies and adapts,
not the shape of a PR description. The contract here is prose in the plugin's
skills, and the decision it derives from is
[PR verification sections](../architecture/pr-verification-sections.md) — a
`data/architecture/` document, which is where this belongs.

If a spec is ever wanted for this, it would be a new `data/spec/` document about
the plugin's authored-artifact formats, covering the plan-checkbox format
alongside this one. That is out of scope here and worth doing only if a third
such format appears.

## Depends on

None.
[Make plan checkboxes carry their evidence](20260815-honest-plan-checkboxes.md)
shares this plan's vocabulary but not its files: that plan changes
`.claude/skills/` and adds a pytest over `data/plans/`; this one changes
`.github/` and `.agents/plugins/agentdev/skills/`. They can ship in either
order.

## Verification

- `rg -n "How to Test|How to test" --glob '!.tmp' .` returns no hits outside
  `docs/knowledge/data/` — the knowledge documents quote the old heading when
  describing the defect and must keep it.
- `rg -n "Reviewer Handoff" .github/ .agents/plugins/agentdev/skills/` returns
  hits in all three files, confirming no site was missed.
- `.agents/plugins/agentdev/bin/super-linter-local.sh` passes — the edits are
  Markdown, and Prettier is the gate that will reformat the example blocks.
- `uv run pytest .agents/plugins/agentdev/tests` passes, confirming no bundled
  script asserted on the old heading.
- Read the resulting `## Edge Cases` and Step 5 together and confirm they do not
  contradict: Step 5 excludes CI-covered work, and no edge case asks for it
  back.

Applying the format to this plan's own PR is the honest end-to-end check, but it
cannot be closed by the session doing the work — see `## Out of scope`.

## Out of scope

- **Rewriting PR #61's body.** The decision was derived from that body's
  failure; retrofitting it is a separate judgement call about an open PR, and
  the branch is already large.
- **Any mechanical gate.** Recorded in the decision as impossible for PR bodies;
  do not add a check that only inspects `./.tmp/pr-body.md`, which is a scratch
  artifact and not the published body.
- **The reviewing agent appending to `## Reviewer Handoff`.** Left as an open
  question in the decision; it changes who authors the section and deserves its
  own exploration.
- **`data/spec/` coverage for authored-artifact formats.** See
  `## Spec changes`.

## Key references

Verified anchor points (line numbers as of 2026-08-15):

- `.github/pull_request_template.md:16` — `## How to Test` heading
- `.github/pull_request_template.md:18-20` — the three numbered instructions
  that mix "commands you actually ran" with coverage gaps
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:88-90` — Step 5,
  "Assess Testing Strategy"
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:105` — the
  `**How to Test**: Actual verification performed` entry in the Step 7 fallback
  section list
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:114-121` —
  `## Edge Cases`, including the `**No tests**` bullet
- `.agents/plugins/agentdev/skills/code-review-standards/SKILL.md:75-83` — step
  4 of `### Recommended Template`, the worked `## How to Test` example
- `.agents/plugins/agentdev/skills/code-review-standards/SKILL.md:180` —
  `Update "How to Test" if testing changes`, in
  `## Responding To Review Feedback`
