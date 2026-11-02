---
type: bug
description: A review that stopped at the PR metadata gate counts as the head's AI review, so after the author fixes the description request-review.py reports ALREADY_REVIEWED and offers no override; the full review cannot run without a new commit.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T01:51:21Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: docs/knowledge/data/spec/ai-review-refresh.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/602
rank: 1150
---

# Bug: a metadata-gate review blocks the re-review it asks for

## Symptom

The AI review's metadata gate stops a review before the in-depth passes when the
PR description is stale, and submits `REQUEST_CHANGES` asking the author to fix
the description and request a re-review. Once the description is fixed,
`request-review.py` refuses that request with `ALREADY_REVIEWED`, because the
gate's review names the head commit. The full review never runs on that head,
and `ai-review-present` stays red until someone pushes a new commit only to
unlock a review.

## Reproduction

1. Open a pull request whose description omits a material change.
2. Let the AI review run on the head. The metadata gate submits
   `REQUEST_CHANGES` naming that head and stops before the review passes.
3. Edit the description to fix the gap, without pushing.
4. Run `agent-code/request-review.py --pr <pr>` from `pr-request-ai-review`. It
   prints `RESULT=ALREADY_REVIEWED`, toggles nothing, and has no option to
   request anyway.

Seen on #602 at head `60f19c65`.

## Root cause

`reviewed()` in `request-review.py` counts any `APPROVED`, `CHANGES_REQUESTED`,
or `COMMENTED` review from the AI reviewer on the head as that head's review. It
cannot tell a metadata-gate stop, which reviewed no code, from a full review.
The script takes no argument to override the check. The rule it enforces is
specified that way: the "one AI review trigger per head commit" requirement in
[AI review refresh](../spec/ai-review-refresh.md) forbids a toggle for any head
an accepted AI review names, with no exception for a gate-only review.

## Fix

Not fixed. A fix needs the spec to allow a re-request on a head whose only AI
review stopped at the metadata gate, and either a way to recognize that review
or an explicit override argument on `request-review.py`.

## Key references

Verified anchor points (line numbers as of 2026-11-01):

- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py:132`
  — `reviewed`; `:210` — the `ALREADY_REVIEWED` return
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:116` — Step 3, the
  metadata gate that stops the review
- `docs/knowledge/data/spec/ai-review-refresh.md:45` — Requirement: one AI
  review trigger per head commit; `:69` — Scenario: the head is already reviewed
