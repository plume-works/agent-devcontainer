---
type: plan
created: 2026-08-17
description: Make approved wording survive the explore-to-plan handoff by writing it to .tmp/ at approval time and forbidding paraphrase, so a cold session starting from the written plan can reproduce the agreed bytes.
generated:
  by: claude-code/opus-5
  at: 2026-08-17T00:00:00Z
sources:
- .claude/skills/explore/SKILL.md
- .claude/skills/plan/SKILL.md
- AGENTS.md
- docs/knowledge/AGENTS.md
- docs/knowledge/data/spec/iwe-workflow-skills.md
---

# Preserve approved wording across the explore handoff

## Context

An exploration produced three finished edits — a replacement bullet for the plan
skill, a `## Capturing` section for implement, a prohibition for the operating
manual — and the maintainer approved them as text. The plan written immediately
afterwards recorded a *description* of each instead: "routing a durable design
fact to `data/architecture/`, a pre-existing defect to `data/bugs/`" in place of
wording that had named which document owns a finding before a new one is
created, and had spelled out the bug-document shape. The specifics were gone,
and the drafts existed nowhere but the conversation.

Recovery worked only by grepping the session transcript on disk, after two
context compactions had already passed. That is luck, not a mechanism.
[Keep working logbooks out of the knowledge graph](20260817-no-logbooks-in-the-graph.md)
was corrected by inlining the recovered text, but nothing prevents a repeat.

Two distinct failures sit behind that outcome. The plan reshaped approved text
to fit a checkbox template, and the approved text was never persisted at all.
The first is now fixed in that plan's own tasks. The second is the handoff, and
it is the more dangerous of the two: a paraphrase is at least visible in review,
while text that was never written down is unrecoverable once the session ends.

`docs/knowledge/AGENTS.md` already states "Never keep project state only in
conversation." Nothing makes approved wording count as project state, so the
rule never engaged.

The handoff that matters is narrow. The maintainer runs `/clear` or starts a new
session before `/implement` in roughly nine cases out of ten, so plan→implement
and implement→ship deliberately carry no conversational context — implement
follows the written plan, and ship has nothing to take from implement. That
makes the plan document the sole channel to implementation, and the
approval-to-plan window the only gap a carrier can close.

## Approach

Two edits, both in `.claude/skills/explore/SKILL.md`, reproduced verbatim in
Tasks 1 and 2 from `.tmp/approved-wording-explore-handoff.md`.

A new `## Capturing` bullet gives approved wording a destination —
`.tmp/approved-wording-<slug>.md`, written before the conversation continues —
and requires the handoff itself to carry the text verbatim and name the file. A
new `## Rules` bullet states the prohibition on paraphrase and supplies the
falsifiable test: whether a session starting cold from the written plan could
reproduce the agreed bytes.

`.tmp/` is the carrier rather than a new graph location because root `AGENTS.md`
already mandates it for temporary files, it is gitignored (`.gitignore:11`), and
the maintainer notes it avoids the sandbox restrictions that other temporary
paths can hit. The window it spans is short by design: once the plan exists, its
fenced task blocks are the durable copy.

The obligations split deliberately. Explore writes the file and reproduces the
text; the inlining obligation reaches plan through the handoff rather than
through a second edit to the plan skill. This matches the existing precedent —
"the exploration becomes the plan's `## Context` and `## Approach`" is stated
from explore's side only — and the maintainer scoped this work to explore.

Rejected: a `data/drafts/` hub. The hub set is closed by design
(`docs/knowledge/AGENTS.md` `## Conventions` requires a `data/index.md` entry
plus a `[schemas.*]` binding), a drafts hub would be the first whose contents
are meant to be temporary and would need a deletion lifecycle nothing else has,
and once the plan exists a separate copy of the same bytes would drift from it.

Rejected: extending the rule to plan→implement and implement→ship. Those
handoffs carry no context by construction, so there is nothing for a carrier to
preserve; the written plan already is the channel, and
[Keep working logbooks out of the knowledge graph](20260817-no-logbooks-in-the-graph.md)
governs what it may contain.

## Implementation Steps

The wording below was approved before this plan was written and is stored at
`.tmp/approved-wording-explore-handoff.md`. It is reproduced verbatim rather
than described. Apply the blocks exactly as given.

### Task 1: Give approved wording a destination in `## Capturing`

**Files:** Modify: `.claude/skills/explore/SKILL.md`

- [ ] Insert this bullet verbatim after the "Ready to build" bullet
  (`.claude/skills/explore/SKILL.md:66-67`) and before the `After any capture:`
  line at `:69`

``` markdown
- Approved wording → `.tmp/approved-wording-<slug>.md`, written before the
  conversation continues. When the user approves specific text — wording for a
  document, a snippet, a message — that text is the deliverable, not a
  description of one. Reproduce it verbatim in the handoff and name the file, so
  the plan skill inlines the approved bytes instead of re-deriving something
  merely equivalent. `.tmp/` is the repo-root scratch directory `AGENTS.md`
  mandates; it is gitignored, and the plan that absorbs the wording becomes its
  durable home.
```

### Task 2: Forbid paraphrase of approved text in `## Rules`

**Files:** Modify: `.claude/skills/explore/SKILL.md`

- [ ] Append this bullet verbatim to the `## Rules` list
  (`.claude/skills/explore/SKILL.md:71-80`), after the existing three bullets

``` markdown
- **Approved text is never paraphrased.** Once the user has agreed to specific
  wording, it survives verbatim or not at all — into `.tmp/` at approval time
  and into the plan's tasks as fenced blocks. Conversation is not storage: a
  session ends, a context compacts, and the agreed bytes are gone. The test is
  whether a session starting cold from the written plan could reproduce them.
```

### Task 3: Update the workflow skills spec

**Files:** Modify: `docs/knowledge/data/spec/iwe-workflow-skills.md`

- [ ] Apply the `## Spec changes` delta below, and confirm the surrounding
  Explore and Plan requirements still read true beside the modified one

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — the durable contract for
these skills. `Requirement: Explore remains an adaptive thinking mode`
(`iwe-workflow-skills.md:25-46`) already covers capture and handoff, so this
work modifies it rather than adding a peer. Both existing scenarios are
unchanged and reproduced below; one scenario is added.

```
MODIFIED Requirement: Explore remains an adaptive thinking mode

The Explore skill SHALL investigate the project graph and codebase without
editing application code, SHALL remain adaptive and patient as the problem takes
shape, and SHALL offer capture or a phase handoff without pressuring the user to
formalize unfinished thinking. When the user approves specific text, Explore
SHALL persist it verbatim outside the conversation and reproduce it verbatim in
the handoff, and SHALL never paraphrase it.

#### Scenario: Exploration starts from an open-ended idea

- **WHEN** the user asks to explore an idea without committing to implementation
- **THEN** Explore follows relevant questions and tradeoffs, grounds claims in
  current project evidence, and ends with the current understanding and an
  optional next step

#### Scenario: Exploration starts during implementation

- **WHEN** the user invokes Explore because an active implementation task
  exposed a complication
- **THEN** Explore reads the active plan and task, investigates without editing
  code, and hands any resulting decision, scope change, or new work back to the
  skill that owns plan execution

#### Scenario: The user approves specific wording

- **WHEN** the user agrees to specific text — wording for a document, a snippet,
  a message — that a later plan or edit will apply
- **THEN** Explore writes it verbatim to `.tmp/approved-wording-<slug>.md`
  before continuing, names that file in the handoff, and reproduces the text
  verbatim rather than describing it
```

## Verification

- `uv run pytest docs/knowledge/tests/test_plan_checkboxes.py` — the plan-shape
  gate stays green over this plan
- `iwe normalize && iwe schema validate` — both clean, run from the repo root.
  Confirm normalize leaves the fenced block contents byte-identical; it
  reformats fence markers only
- Diff each applied block against `.tmp/approved-wording-explore-handoff.md` and
  confirm byte equality — the plan's own subject matter is that this check is
  the one that fails silently
- Read `.claude/skills/explore/SKILL.md` end to end and confirm the new
  `## Capturing` bullet and `## Rules` bullet do not contradict the existing
  no-code boundary or the capture-once instruction

## Out of scope

- Any edit to `.claude/skills/plan/SKILL.md`. The inlining obligation reaches
  plan through explore's handoff, matching the existing one-sided precedent; the
  maintainer scoped this work to explore
- Rules for the plan→implement and implement→ship handoffs. Both carry no
  conversational context by construction, so there is nothing to preserve across
  them
- A durable graph home for drafts. Rejected in `## Approach`; `.tmp/` spans the
  only window that needs a carrier
- Automating the verbatim check. Whether applied text matches an approved draft
  is a diff a session can run today, and `.tmp/` is gitignored, so no gate in CI
  could see the draft

## Key references

Verified anchor points (line numbers as of 2026-08-17):

- `.claude/skills/explore/SKILL.md:47` — `## Capturing`, the section Task 1
  extends
- `.claude/skills/explore/SKILL.md:66-67` — the "Ready to build" bullet Task 1
  inserts after
- `.claude/skills/explore/SKILL.md:69` — the `After any capture:` line that
  bounds the insertion
- `.claude/skills/explore/SKILL.md:71-80` — `## Rules`, the three-bullet list
  Task 2 appends to
- `docs/knowledge/data/spec/iwe-workflow-skills.md:25-46` —
  `Requirement: Explore remains an adaptive thinking mode`, the requirement Task
  3 modifies
- `AGENTS.md:4` — the mandate to use `./.tmp` for temporary files
- `.gitignore:11` — `.tmp/`, confirming the carrier is untracked
- `docs/knowledge/AGENTS.md:74` — `## Conventions`, which closes the hub set and
  grounds the rejection of a `data/drafts/` hub
