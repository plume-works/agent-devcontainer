---
type: bug
description: Ship's release-link rule assumes every plan links a feature or bug, so for a plan that links neither, one model ships without an unreleased entry and another stops for a decision.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-09T14:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
---

# Bug: Ship's release-link rule is undefined for a plan with no feature or bug

## Symptom

Shipping a fully implemented plan that links no feature or bug takes a different
path depending on the model running the Shipper. Claude Code (Opus 5.5) marks
the plan done and adds no `data/releases/unreleased.md` entry. OpenCode with
`openai/gpt-6-astra` returns a zero-CRITICAL Verify verdict, then stops with
"Needs decision: identify the feature or bug this work should link to" and makes
no transition.

## Reproduction

1. Create a plan whose only task is ticked with evidence, whose
   `## Spec changes` is `None — no behavioral change`, and which links no
   feature or bug and does not ask for a new feature. Link it under `## Active`.
2. Run `/agentdev:iwe-ship <plan>`, granting approval for any verification
   command with effects beyond the working tree.
3. On Claude Code the plan ships with no unreleased entry; on OpenCode with
   `openai/gpt-6-astra` it stops before any lifecycle transition.

## Root cause

Step 6 of the Ship rulebook sets "the linked feature" or "the linked bug" and
ensures `data/releases/unreleased.md` holds "exactly one inclusion link for the
work: a feature … or a bug". It has no branch for tooling or docs-only work that
links neither. Its feature-creation clause applies only "if the plan requires a
new feature", so nothing says whether such a plan ships without a release entry
or needs one created.

## Fix

Unfixed. Step 6 should state what a plan linking neither a feature nor a bug
does — for example, that it adds no unreleased entry — so every model takes the
same path.

## Key references

Verified anchor points (line numbers as of 2026-10-09):

- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:115` — set the linked
  feature or bug; new-feature clause
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:119` — exactly one
  unreleased inclusion link for a feature or a bug
