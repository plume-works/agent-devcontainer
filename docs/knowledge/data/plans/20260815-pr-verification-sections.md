---
type: plan
created: 2026-08-15
description: Replace How to Test with Verification and Reviewer Handoff, moving PR structure into the pr-gen-description skill and reducing the repository template to a pointer stub.
generated:
  by: claude-code/opus-5
  at: 2026-08-15T00:00:00Z
sources:
- resource: .github/pull_request_template.md
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: .agents/plugins/agentdev/skills/code-review-standards/SKILL.md
---

# Split PR How to Test into Verification and Reviewer Handoff

## Context

[PR verification sections](../architecture/pr-verification-sections.md) decides
that a pull request body splits `## How to Test` into two sections:
`## Verification`, holding closed items as checked boxes with an `**Evidence:**`
child, and `## Reviewer Handoff`, holding open items as unchecked boxes with a
`**Closed by:**` child. Both sections omit what an automated check already
covers, and reference rather than restate what another document owns. This plan
carries that decision into the places that define the section — and, while doing
so, reduces how many such places exist.

`.github/pull_request_template.md` stops carrying structure. Nobody opens a pull
request by hand in this project or in a consuming one, and `pr-open` always
passes `gh pr create --body-file`, so nothing reads the template's structure —
while the skill that generates the body is about to describe that structure
itself. Keeping both means keeping them in sync forever, which is the drift this
whole change exists to remove.

The file survives as a pointer stub rather than being deleted, so GitHub's
web-UI textarea is not blank and a human reader has something in-repo naming the
authority. The stub carries no sections, so there is nothing in it to drift.

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

Invert the authority. Today `pr-gen-description` *defers* to a discovered
template ("start from it… when the repository has no template, use the section
list below"), which is what creates the sync problem: two documents describing
one structure, either able to drift. After this change the skill states the
structure unconditionally and looks for no template at all.

A consuming repository that has its own `pull_request_template.md` is therefore
no longer honored — so the skill must **say so** rather than ignore it in
silence. Step 7 gains an instruction to check for one and, when found, tell the
caller plainly that the skill's structure was used instead and their template
was not consulted. A consumer discovering that from a diff is a bug; a consumer
told during the run can decide whether to keep the file, delete it, or ask for
the structure to change.

The section format is the easy half. The hard half is the two filters, because
applying them requires knowing what CI covers — and the skill currently
instructs the opposite. `pr-gen-description` Step 5 says "Assess Testing
Strategy: Unit tests, integration tests, manual testing, coverage impact", which
invites exactly the transcript of automated runs the decision removes. Step 5 is
a site in its own right, not merely another mention: it must tell the author to
read `.github/workflows/` and treat everything CI runs as excluded, keeping only
the residue.

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

### Task 1: Skill owns the structure

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md`

- [x] **1. Make the Step 7 section list authoritative and add the two
  sections.** Rewrite `:100` so the skill states the structure rather than
  discovering one: drop "Locate the repository's pull request template … start
  from it" and the no-template fallback wording. In the list at `:105`, replace
  the `How to Test` entry with `Verification` (closed items, `- [x]` +
  `**Evidence:**`) and `Reviewer Handoff` (open items, `- [ ]` +
  `**Closed by:**`), each defined by tense, and note that `## Verification` is
  often empty when CI covers the change.
  - **Evidence:** `pr-gen-description/SKILL.md` Step 7 now opens "This section
    list is the structure"; the list carries `Verification` and
    `Reviewer Handoff` defined by tense with their child-line vocabulary, and
    Step 8 no longer syncs against a template.
    `validate_agent_files --recommend .agents --require-marketplace claude codex`
    → 35/35 skills valid, 0 errors.
- [x] **2. Warn when a consuming repository has its own template.** Still check
  for `.github/pull_request_template.md` and `.github/PULL_REQUEST_TEMPLATE/`,
  but only to report: when one exists, tell the caller the skill's structure was
  used and their template was not consulted. Never silently ignore it, and never
  merge the two structures.
  - **Evidence:** Step 7 closes with a paragraph instructing the skill to check
    both template paths "only in order to report it", tell the caller the
    skill's structure was used and their template was not consulted, and never
    merge or silently ignore. Validator clean (35/35).
- [x] **3. Rewrite Step 5 to select rather than inventory.** Replace the "Assess
  Testing Strategy" line (`:88-90`) with instructions to read
  `.github/workflows/` for what CI already runs on the branch, then keep only
  what survives both filters — no linter, formatter, image build, or test suite
  CI executes, and no restatement of a plan's own verification record.
  - **Evidence:** Step 5 is now "Select What Needs Stating" — reads
    `.github/workflows/`, states both filters (no CI-executed linter, formatter,
    image build or test suite; reference rather than restate a plan's record),
    and sorts the residue by tense into the two Step 7 sections.
- [x] **4. Add the empty-section and unclosable-item edge cases.** In
  `## Edge Cases` (`:114-121`), record that an empty `## Verification` under
  green CI is the expected outcome rather than a gap to fill, and that an item
  no reviewer can close still belongs under `## Reviewer Handoff` with its
  closer named. Reconcile the existing "**No tests**: Warn incomplete testing
  section" bullet, which otherwise contradicts both.
  - **Evidence:** `## Edge Cases` gains **Empty `## Verification`** (expected
    under green CI, not a gap) and **An item nobody reviewing can close** (stays
    in `## Reviewer Handoff` with its closer named). The contradicting **No
    tests** bullet is replaced by **No test covers a change**, which routes to
    `## Reviewer Handoff` and drops the warn-on-thin-section instruction.
- [x] **5. Update the skill's own template references.** The intro at `:9` and
  the `## Related Resources` entry at `:125` both name the repository template
  as the source of structure; both must instead point at the Step 7 list.
  - **Evidence:** the intro now says the structure is "defined by Step 7 below,
    which is this skill's own and does not come from any repository file", and
    the `## Related Resources` template bullet is replaced by "The section
    structure: the list in Step 7 of this skill".

### Task 2: Reduce the template to a pointer stub

**Files:** Modify: `.github/pull_request_template.md`

- [x] **6. Replace the template body with a pointer stub.** Delete all 34 lines
  of structure and leave only a short note that PR descriptions are generated by
  the `agentdev:pr-gen-description` skill, which is where the structure lives.
  The stub **must not name, list, or example any section** — the moment it
  describes structure it is a second copy that can drift, which is the defect
  this plan removes. Its only job is to keep GitHub's web-UI textarea non-empty
  and point a human reader at the authority. Do this after Task 1, so no commit
  leaves the skill deferring to a file that no longer carries a structure.
  - **Evidence:** `.github/pull_request_template.md` is four lines of prose
    naming `agentdev:pr-gen-description` as the authority and no sections.
    `rg -c "^##|- \[[ x]\]" .github/pull_request_template.md` exits 1 with no
    matches and `rg -q "pr-gen-description"` succeeds — the plan's own stub
    check. Landed after Task 1's commit 3c9a913, so no commit left the skill
    deferring to a structureless file.

Rejected: deleting the file outright (the textarea goes blank and a human reader
has nothing in-repo pointing anywhere), and symlinking it to the skill (nothing
reads the template — `pr-open` always passes `gh pr create --body-file` — so the
link would preserve an unread file, the skill's structure is a section list
inside `SKILL.md` rather than a standalone file to point at, and this repository
tracks no symlinks, having just removed its only one for the reasons in
[uv environment location](../architecture/uv-environment-location.md)).

### Task 3: Review standards skill

**Files:** Modify:
`.agents/plugins/agentdev/skills/code-review-standards/SKILL.md`

- [x] **7. Rewrite the worked example.** Replace step 4 of
  `### Recommended Template` (`:75-83`) — the `## How to Test` heading and its
  three-command example — with both sections in the required shape. The example
  is what most readers copy, so it must show an `**Evidence:**` line and a
  `**Closed by:**` line rather than describe them.
  - **Evidence:** step 4 of `### Recommended Template` now shows both headings
    with a real `- [x]` + `**Evidence:**` item and a real `- [ ]` +
    `**Closed by:**` item, followed by the rule that neither section may hold
    the other's box type. `validate_agent_files` 35/35, 0 errors;
    `uv run pytest .agents/plugins/agentdev/tests` 14 passed.
- [x] **8. Update the feedback-loop instruction.** At `:180`, "Update 'How to
  Test' if testing changes" becomes an instruction naming both sections, and
  states the direction items travel: work closed since the last review moves
  from `## Reviewer Handoff` to `## Verification` with its evidence, never the
  reverse.
  - **Evidence:** the bullet in `## Responding To Review Feedback` now names
    both sections and states the one-way direction of travel — closed work moves
    to `## Verification` with its evidence, never back.

### Task 4: Template boundary

**Files:** Modify: `docs/knowledge/data/architecture/template-boundary.md`

- [ ] **9. Reclassify the template row in the GitHub surface table.** The
  `.github/pull_request_template.md` row at `:137` currently reads
  `Template | General pull request structure`. It is no longer structure: change
  its coupling text to say it is a stub pointing at the `agentdev` catalog,
  where PR structure now lives. A consumer copying it gets a pointer, not a
  format, so the `Template` class still holds — say why, since this is one of
  only two `Template`-class rows in that table.

### Task 5: Downstream record

**Files:** Modify: `docs/knowledge/data/log.md`

- [ ] **10. Record the change as a downstream break.** A consuming repository
  that copied `.github/pull_request_template.md` still has the old structural
  version, and its updated `agentdev` skills will now ignore it — reporting that
  it was ignored, per task 2. Note that adopting means replacing the copied file
  with the stub, or deleting it, in the same register as the `setup-python-venv`
  activation break.

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
- `rg -n "Reviewer Handoff" .agents/plugins/agentdev/skills/` returns hits in
  both skill files, confirming no site was missed.
- `rg -n "pull_request_template|PULL_REQUEST_TEMPLATE" --glob '!.tmp' .` returns
  only the knowledge documents and the task-2 warning path in
  `pr-gen-description` — no skill still treats a template as the source of
  structure.
- `.github/pull_request_template.md` still exists, contains no `##` heading and
  no checkbox, and names `pr-gen-description` —
  `rg -c "^##|- \[[ x]\]" .github/pull_request_template.md` returns no matches
  and `rg -q "pr-gen-description" .github/pull_request_template.md` succeeds.
  This is the check that the stub never grew back into a structure.
- `.agents/plugins/agentdev/bin/super-linter-local.sh` passes — the edits are
  Markdown, and Prettier is the gate that will reformat the example blocks.
- `uv run pytest .agents/plugins/agentdev/tests` passes, confirming no bundled
  script asserted on the old heading or read the template.
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

- `.github/pull_request_template.md:16` — `## How to Test` heading, in the file
  this plan deletes
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:9` — intro naming
  the repository template as what the skill fills
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:88-90` — Step 5,
  "Assess Testing Strategy"
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:100` — Step 7's
  "Locate the repository's pull request template … start from it", the deference
  this plan inverts
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:105` — the
  `**How to Test**: Actual verification performed` entry in the Step 7 section
  list
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:125` —
  `## Related Resources` entry pointing at the repository template
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:114-121` —
  `## Edge Cases`, including the `**No tests**` bullet
- `.agents/plugins/agentdev/skills/code-review-standards/SKILL.md:75-83` — step
  4 of `### Recommended Template`, the worked `## How to Test` example
- `.agents/plugins/agentdev/skills/code-review-standards/SKILL.md:180` —
  `Update "How to Test" if testing changes`, in
  `## Responding To Review Feedback`
- `docs/knowledge/data/architecture/template-boundary.md:137` — the
  `.github/pull_request_template.md` row in the GitHub surface table, classed
  `Template`
