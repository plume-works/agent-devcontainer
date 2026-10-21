---
type: bug
stage: done
description: Replay could justify a re-stamp with masked working-tree changes while omitting those changes and their hidden values from its evidence.
generated:
  by: codex/gpt-5
  at: 2026-10-21T06:23:54Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py
- resource: .agents/plugins/agentdev/tests/test_stale_map_docs_replay.py
- resource: https://github.com/plume-works/agent-devcontainer/pull/412#discussion_r4333348768
---

# Bug: Replay omits working-tree evidence

## Symptom

Replay could report `RESTAMP` with no `ABSORBED` or `HIDDEN` evidence when an
uncommitted mask alone absorbed an uncommitted source edit.

## Reproduction

Add an over-broad uncommitted mask and a matching uncommitted source edit to a
document that is otherwise fresh, then run `--replay`. The old report could
re-stamp the document without exposing the edit or matched value for review.

## Root cause

Working-tree comparisons participated in verdicts but did not participate in
evidence collection. A user-supplied `--since` could likewise omit commits that
the per-document verdict relied on.

## Fix

Replay emits `ABSORBED WORKTREE <path>` or `MOVED WORKTREE <path>`, collects
their hidden values, and unions all per-document ancestry windows into the
evidence report regardless of the optional `--since` value.

## Key references

Verified anchor points (line numbers as of 2026-10-21):

- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:699` —
  replay evidence windows
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:713` —
  working-tree evidence
- `.agents/plugins/agentdev/tests/test_stale_map_docs_replay.py:151` —
  `test_an_uncommitted_masked_edit_is_reported_as_absorbed`
