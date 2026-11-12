---
type: architecture
description: Plan task evidence is a free-form note whose only job is to stop a box being ticked for work that was not done; the plan-checkboxes gate is the only check on it, and Verify never checks ticks or their notes.
sources:
- resource: docs/knowledge/data/spec/plan-checkbox-evidence.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
---

# Task evidence is a note, not a check

## Decision

A ticked plan task's `- **Evidence:**` line is a short free-form note of what
was done and how it was checked — a test, a command, a file, a manual or live
check, a CI run, a PR, or a commit, in whatever words fit. Its one purpose is to
stop a box being ticked for work that was not done: writing the note forces the
implementer to state what it did, and the `plan-checkboxes` gate checks the
note is present.

Nothing else reads it. The `plan-checkboxes` gate is the only check on a tick
and its note: Verify reports nothing about a ticked task or its note, and never
re-runs, re-observes, or asks approval to repeat what the note records.

A task's code, its checkbox flip, and its evidence line land in one commit. One
edit ticks one box, and one task makes one commit.

## Why

Grading the note made it a second deliverable with its own failure modes. A
note naming a code anchor instead of a test, a check Verify could not repeat
without approval, or a live observation Verify could not re-observe each
blocked Ship although the code was done, and every fix to the note was another
Implement and Verify round with no change to the product.

## Alternatives rejected

- **Evidence by kind, re-run by Verify** — a test id or command for code, a
  file and anchor for docs, a CI run or PR for external work, with commit ids
  and "residue" rejected. Verify's judgment of the kind flipped between runs,
  and a recorded live check became an approval Ship could not get past.
- **No evidence line at all.** Nothing would then distinguish a careful tick
  from a blanket `- [ ]` → `- [x]` sweep.
