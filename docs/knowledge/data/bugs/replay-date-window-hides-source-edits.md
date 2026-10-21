---
type: bug
description: Replay could re-stamp a stale map document after omitting source edits that fell outside a commit-date window.
generated:
  by: codex/gpt-5
  at: 2026-10-21T06:23:54Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py
- resource: .agents/plugins/agentdev/tests/test_stale_map_docs_replay.py
- resource: https://github.com/plume-works/agent-devcontainer/pull/412#discussion_r4333348129
---

# Bug: Replay date window hides source edits

## Symptom

Replay could report `RESTAMP` even though a map document's sources contained a
real, unmasked edit that was absent from the date-bounded history walk.

## Reproduction

Record a map digest on a branch whose verification timestamp is later than a
source edit on another branch, merge that history, and run `--replay`. The plain
check reports the document stale while the old replay could report it as safe to
re-stamp.

## Root cause

The verdict used `verified.at` as a commit-date cutoff. Timestamps do not define
Git ancestry, so the history walk could omit commits that contributed to the
current source tree.

## Fix

Replay locates the first-parent commit that began the document's current
`source_digest` run and evaluates every later first-parent source change. The
optional `--since` date only widens the evidence report; it cannot narrow the
ancestry required by a verdict.

## Key references

Verified anchor points (line numbers as of 2026-10-21):

- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:619` —
  `digest_commit`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:638` —
  `replay_verdict`
- `.agents/plugins/agentdev/tests/test_stale_map_docs_replay.py:197` —
  `test_replay_uses_the_digest_commit_ancestry_even_when_since_is_later`
