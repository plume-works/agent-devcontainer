---
type: feature
stage: implemented
description: Approved wording survives the explore-to-plan handoff — persisted verbatim to .tmp/ at approval time and inlined as fenced blocks in the plan's tasks, so a cold session can reproduce the agreed bytes.
generated:
  by: claude-code/opus-5
  at: 2026-08-24T00:00:00Z
sources:
- resource: .claude/skills/explore/SKILL.md
- resource: .claude/skills/plan/SKILL.md
---

# Preserved approved wording

## Purpose

When a user approves specific text — wording for a document, a snippet, a
message — that text is the deliverable, not a description of one. Two distinct
failures can lose it between approval and application: a plan that reshapes the
text into a summary, and text that is never written outside the conversation at
all. The second is the more dangerous, because a paraphrase is at least visible
in review while unpersisted text is unrecoverable once the session ends.

`docs/knowledge/AGENTS.md` already states "Never keep project state only in
conversation." Approved wording did not count as project state, so the rule
never engaged.

## Behaviour

**Explore persists approved wording before continuing.** A `## Capturing`
destination sends it to `.tmp/approved-wording-<slug>.md`, written before the
conversation moves on, and requires the handoff itself to carry the text
verbatim and name the file. Naming it in the handoff is load-bearing beyond the
file: when Plan runs in the same session it may never read `.tmp/`.

**Both skills are bound against paraphrase.** Explore's rule states that
approved text survives verbatim or not at all. Plan's rule states that approved
text is copied, never described, and names the recovery routes — `.tmp/`, the
conversation, the transcript — when the text is not at hand.

**The task format distinguishes action from content.** A plan task may describe
an *action*; it may never paraphrase *approved content*. Text agreed as specific
wording is reproduced verbatim in a fenced block under the task that applies it,
and `.tmp/approved-wording-<slug>.md` is consulted before writing a task from
memory.

**Both rules share one falsifiable test:** whether a session starting cold from
the written plan could reproduce the approved bytes.

**The obligations are split across the handoff deliberately.** Explore writes;
Plan inlines. Neither half is sufficient alone — Explore can hand over perfect
text without binding Plan to copy rather than describe it, and approved wording
also reaches Plan directly in conversation without Explore ever running.

## Edge cases

- **`.tmp/` spans a deliberately short window.** Once the plan exists, its
  fenced task blocks are the durable copy.
- **The verbatim check cannot be automated in CI.** `.tmp/` is gitignored, so no
  gate can see the draft; the diff is a check a session runs, not a gate.

## Resolved decisions

- `.tmp/` is the carrier because root `AGENTS.md` already mandates it for
  temporary files and it is gitignored, avoiding the sandbox restrictions other
  temporary paths can hit.
- Rejected: a `data/drafts/` hub. The hub set is closed by design, a drafts hub
  would be the first whose contents are meant to be temporary and would need a
  deletion lifecycle nothing else has, and a separate copy would drift from the
  plan.
- Rejected: extending the rule to the plan→implement and implement→ship
  handoffs. Those carry no context by construction, so the written plan is
  already the sole channel and there is nothing for a carrier to preserve.
