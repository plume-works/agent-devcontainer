---
type: plan
created: 2026-09-03
description: Let a consuming repository capture its extra PR-template sections as instructions in a consumer-owned guidance file that pr-gen-description reads with precedence, via a template-consume evaluate/map/capture step.
generated:
  by: claude-code/opus-4-8
  at: 2026-09-03T19:10:00Z
---

# Consumer PR description guidance

## Context

`pr-gen-description` supersedes any repository pull request template with its
own Step 7 section structure. This repository's own
`.github/pull_request_template.md` is a pure
`<!-- pr-gen-description: no-template -->` stub, so the skill already handles
the template being absent as structure. Two gaps remain for a *consuming*
repository:

1. **`template-consume` is blind to a real existing template.** A Workflow B
   consumer (adopting the template into an existing repository) may already have
   a `.github/pull_request_template.md` full of real sections. The consumption
   guide's §4 today just says "copy or merge the pull request template" — it
   never evaluates the consumer's template against what `pr-gen-description`
   produces, so any consumer-specific sections are silently lost or silently
   left to drift.
2. **There is no customization channel for `pr-gen-description`.** A consumer
   cannot feed extra, repository-specific instructions into what the skill
   generates (for example "always link the Jira ticket in Related"). Step 7's
   structure is closed to the skill's own list.

The fix connects the two: `template-consume` evaluates the consumer's template,
maps each section against the skill's Step 7 list, and — for sections with no
skill equivalent — offers to capture them as **instructions** in a new
consumer-owned guidance file that `pr-gen-description` then reads at generation
time.

## Approach

Introduce one consumer-only artifact: `.github/pr-description-guidance.md`,
which holds **instructions**, not section headings. `pr-gen-description` reads
it when present and lets its instructions take precedence over the default
generation of the Step 7 sections — with one floor: the guidance may not
collapse or rename the Verification / Reviewer Handoff split, which Step 7 calls
load-bearing.

`template-consume` is where the file gets written. In both setup mode (Workflow
B with an existing template) and update mode (when the tracked PR-template path
changed upstream), the agent proposes a mapping of each of the consumer's
template sections onto a Step 7 section, presents the two buckets (covered vs.
extras) for the user to correct, and then batch-offers to capture the extras.
Capturing means translating each extra *heading* into an *instruction* and
writing it into the guidance file, then reducing the PR template to the
`no-template` stub. The user may instead drop the extras or keep their template
as-is (in which case `pr-gen-description`'s existing report-only path applies).

Alternatives rejected:

- **A guidance block inside the PR template file** (three-state overloading of
  one file). Rejected in favor of a separate file: the template stays a pure
  two-state pointer, and the guidance path can be tracked independently by
  update mode.
- **Guidance carrying section headings.** Rejected in favor of instructions: a
  headings list is a structure file by another name, which is exactly what Step
  7 supersedes. The capture step translates a consumer heading like
  `## Rollback plan` into an instruction ("always include a Rollback plan
  section describing how to revert this change").
- **Full precedence with no floor.** Rejected: guidance is the customization
  point and takes precedence, but preserving the Verification / Reviewer Handoff
  tense split is the one invariant a consumer may not override, because that
  split is what makes each item's state readable.
- **Shipping an empty example guidance file in this repository.** Rejected: this
  repository has no extras, so the file is consumer-only. `template-boundary`
  classifies the path, but this repository does not carry the file.

## Implementation Steps

### Task 1: Teach `pr-gen-description` Step 7 to read the guidance file

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md`

Add a branch to Step 7, before the existing template-reporting paragraph, that
reads `.github/pr-description-guidance.md` when it exists and applies its
instructions with precedence over the default section generation, subject to the
tense-split floor. The existing rule that the skill never reads structure out of
the PR template itself is unchanged — guidance comes only from the guidance
file.

- [x] Step 7 gains a guidance-file paragraph stating: when
  `.github/pr-description-guidance.md` exists, its instructions take precedence
  over the default generation of the sections in this step, but SHALL NOT
  collapse or rename the `## Verification` / `## Reviewer Handoff` split.
  - **Evidence:** `pr-gen-description/SKILL.md` Step 7 gains the paragraph "When
    a consumer-owned guidance file `.github/pr-description-guidance.md` exists…"
    placed before the template-reporting paragraph, with the SHALL NOT
    collapse/rename floor. Committed on `consumption-review`.
- [x] The guidance file is described in prose (per `.agents/AGENTS.md`, no
  plugin-relative link out to a per-repository file), and named as an
  instructions file, not a structure/section file.
  - **Evidence:** The paragraph names the file in prose backticks (no markdown
    link) and states "It holds instructions … not section headings; a heading
    list would be a structure file, which this step supersedes." Committed on
    `consumption-review`.
- [x] The existing three-way template-reporting logic (no-template marker →
  silent; real structure → report "not consulted"; else use structure) is left
  intact; the guidance branch is additive to it.
  - **Evidence:** The "Check whether the repository has its own pull request
    template…" paragraph and its `no-template` exception are unchanged; the new
    guidance paragraph precedes them and closes with "the skill still never
    reads structure out of the pull request template itself." Committed on
    `consumption-review`.
- [x] The `## Related Resources` list mentions the guidance file as the consumer
  customization point.
  - **Evidence:** `## Related Resources` gains the bullet "The consumer
    customization point: `.github/pr-description-guidance.md`…".
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    → 46/46 skills valid, 0 errors. Committed on `consumption-review`.

### Task 2: Give the consumption guide the evaluate → map → capture procedure

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

Replace the guide's §4 one-liner about the PR template with the full procedure:
evaluate the consumer's existing `.github/pull_request_template.md`, have the
agent propose a section-by-section mapping onto `pr-gen-description`'s Step 7
list, present the covered/extras buckets for user correction, and batch-offer
the extras' disposition (capture / drop all / keep template as-is). Capture
writes the extras as translated instructions into
`.github/pr-description-guidance.md` and reduces the template to the
`no-template` stub.

- [x] §4 states the mapping is agent-proposed then user-confirmed, showing both
  buckets (covered vs. extras) before anything is written.
  - **Evidence:** consumption-guide.md §4 "The pull request template" step 1
    ("Map, then confirm.") proposes the mapping, presents covered/extras
    buckets, and states "Nothing is captured or deleted until the user confirms
    the buckets." Committed on `consumption-review`.
- [x] §4 makes the heading→instruction translation explicit (a consumer heading
  becomes an instruction telling `pr-gen-description` to emit that content), so
  a future agent does not paste headings verbatim and recreate a structure file.
  - **Evidence:** §4 step 3 ("Capture translates headings into instructions.")
    translates `## Rollback plan` into an emit instruction and warns "A guidance
    file full of pasted headings is a structure file by another name." Committed
    on `consumption-review`.
- [x] §4 presents the extras' disposition as one batch decision with a
  recommended default of capture, and enumerates the three outcomes: capture as
  guidance, drop all, keep template as-is.
  - **Evidence:** §4 step 2 ("Decide the extras as one batch.") defaults to
    capture and enumerates Capture as guidance / Drop all / Keep template as-is.
    Committed on `consumption-review`.
- [x] §4 notes that "keep template as-is" leaves the consumer's real template in
  place, which `pr-gen-description` then reports as not consulted.
  - **Evidence:** §4 step 2's "Keep template as-is" outcome states it "leave[s]
    the consumer's real template in place. `pr-gen-description` then reports it
    as not consulted on every run." Committed on `consumption-review`.
- [x] The procedure names the guidance-file precedence floor (may add/override
  but not collapse or rename the Verification / Reviewer Handoff split), so
  captured instructions never encode a forbidden override.
  - **Evidence:** §4 step 4 ("Respect the precedence floor.") states guidance
    "may not collapse or rename the Verification / Reviewer Handoff split" and
    "Never capture an instruction that would merge or rename those two
    sections." Committed on `consumption-review`.

### Task 3: Extend `template-consume` update mode and template surface

**Files:** Modify: `.agents/plugins/agentdev/skills/template-consume/SKILL.md`

Update mode gains a conditional: when `CHANGED_PATHS` includes the PR-template
path, re-run the §4 evaluation against the consumer's current template (which
may itself already carry a guidance file to preserve). Record
`.github/pr-description-guidance.md` as a tracked path when it is created so
update mode preserves it, and note that it is consumer-created rather than part
of the default copied surface.

- [ ] Update Mode step 2 (or a new adjacent step) directs the agent to re-run
  the guide's §4 PR-template evaluation when the PR-template path is among the
  changed paths.
- [ ] The marker/`tracked_paths` guidance says to add
  `.github/pr-description-guidance.md` to `tracked_paths` when setup created it,
  so update mode preserves consumer guidance.
- [ ] The Default Template Surface note records that
  `.github/pr-description-guidance.md` is consumer-created (not in the default
  copied list) but is tracked once it exists — consistent with
  `template-boundary` classifying it as Customize.

### Task 4: Add the normative requirement to the template-consumption spec

**Files:** Modify: `docs/knowledge/data/spec/template-consumption.md`

Add a Requirement making the guidance-file contract normative: setup/update
evaluate the consumer's PR template, extras may be captured as instructions in
`.github/pr-description-guidance.md`, and that guidance takes precedence over
`pr-gen-description`'s default section generation except that it SHALL preserve
the Verification / Reviewer Handoff tense split.

- [ ] A new `## Requirement` covers PR-template evaluation and the guidance-file
  precedence floor, in the spec's existing SHALL style.
- [ ] Its `sources:` / prose reference the two skills that implement it
  (`pr-gen-description`, `template-consume`).

### Task 5: Classify the guidance path in the template-boundary architecture doc

**Files:** Modify: `docs/knowledge/data/architecture/template-boundary.md`

Add `.github/pr-description-guidance.md` to the GitHub surface table as
**Customize**, consumer-created, noting it holds `pr-gen-description`
instructions and does not exist in this publisher repository.

- [ ] The GitHub surface table (or an adjacent note) classifies
  `.github/pr-description-guidance.md` as Customize / consumer-created and
  explains its relationship to the `pull_request_template.md` stub row.

### Task 6: Validate the graph and skill catalog

**Files:** (no source files) — validation only

- [ ] `iwe normalize` and `iwe schema validate` both pass.
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes for the edited skills.

## Spec changes

`data/spec/template-consumption` — **ADDED requirement.** The change adds a new
customization channel and a precedence rule with a load-bearing floor, so it
warrants the fenced form.

``` markdown
## ADDED Requirements

### Requirement: a consumer may customize generated PR descriptions through a guidance file

Template setup and update SHALL evaluate a consuming repository's existing
`.github/pull_request_template.md` against the section structure the
`pr-gen-description` skill generates, proposing a section-by-section mapping for
the user to confirm. Sections with no equivalent in that structure MAY be
captured, at the user's choice, as instructions in a consumer-owned
`.github/pr-description-guidance.md`; capturing SHALL translate a template
section into a generation instruction rather than copying its heading verbatim.

When `.github/pr-description-guidance.md` exists, `pr-gen-description` SHALL apply
its instructions with precedence over the default generation of its own sections,
except that the guidance SHALL NOT collapse or rename the Verification /
Reviewer Handoff split. `pr-gen-description` SHALL NOT read description structure
from the pull request template itself.

#### Scenario: an extra template section is captured as guidance

- WHEN a Workflow B consumer's `.github/pull_request_template.md` contains a
  section with no equivalent in the `pr-gen-description` structure, and the user
  chooses to capture it
- THEN the section is written as an instruction in
  `.github/pr-description-guidance.md`, the template is reduced to the
  `<!-- pr-gen-description: no-template -->` stub, and the guidance path is added
  to the marker's tracked paths.

#### Scenario: guidance may not break the tense split

- WHEN `.github/pr-description-guidance.md` carries an instruction that would
  merge or rename the Verification and Reviewer Handoff sections
- THEN `pr-gen-description` preserves the two sections and their `- [x]` / `- [ ]`
  tense split regardless of the guidance.
```

## Verification

- `iwe normalize` and `iwe schema validate` exit clean.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
- Read-through: Step 7 of `pr-gen-description` and §4 of the consumption guide
  agree on the guidance-file name, the heading→instruction translation, and the
  tense-split floor; the spec requirement and `template-boundary` classification
  match both.

## Out of scope

- No change to the `<!-- pr-gen-description: no-template -->` marker or the
  existing three-way template-reporting logic in Step 7 — the guidance branch is
  additive.
- No guidance file is added to this repository; it is consumer-created only.
- No change to how `pr-gen-description` renders any specific instruction (for
  example the exact placement of a "link Jira in Related" note) beyond the
  precedence rule and the tense-split floor.
- No automated parser or schema for `.github/pr-description-guidance.md`; it is
  agent-read prose instructions.

## Key references

Verified anchor points (line numbers as of 2026-09-03):

- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:112` —
  `### Step 7: Generate The Description`
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:133` —
  template-reporting paragraph ("Check whether the repository has its own pull
  request template")
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:141` —
  `no-template` marker exception
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:171` —
  `## Related Resources`
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:615`
  — `### 4. Merge GitHub configuration`
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:617`
  — "Copy or merge the pull request template" one-liner
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:110` — Update Mode
  step 2 ("For each changed path")
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:128` —
  `## Default Template Surface`
- `docs/knowledge/data/spec/template-consumption.md:77` — last `## Requirement`
  (append point)
- `docs/knowledge/data/architecture/template-boundary.md:149` —
  `### GitHub surface`
- `docs/knowledge/data/architecture/template-boundary.md:155` —
  `pull_request_template.md` row
