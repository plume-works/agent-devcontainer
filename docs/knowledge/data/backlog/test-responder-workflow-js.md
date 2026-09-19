---
type: task
created: 2026-09-19
stage: planned
priority: medium
description: Give the responder workflow's inline github-script logic executable regression coverage, which no test harness in this repository currently reaches.
generated:
  by: claude-code/opus-5
  at: 2026-09-19T00:00:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .agents/plugins/agentdev/tests/
- resource: https://github.com/plume-works/agent-devcontainer/pull/163
---

# Test the responder workflow's inline JavaScript

`.github/workflows/ai-responder.yml` carries decision logic in
`actions/github-script` blocks: which events want a review, the
`[ci:skip-ai-review]` and `[ci:review-effort=…]` body markers, the effort tier's
comment-over-marker precedence, the prompt the responder receives, and the
bridge's review-versus-task classification. None of it is reachable by a test
today.

Both pytest suites in `testpaths` test *scripts* — Python and bash under
`.agents/plugins/agentdev/`. `test_discover_ai_responder.py` tests the
discover-ai-responder skill script, not the workflow. No harness in this
repository loads a workflow file, extracts a `script:` block, or runs it against
a synthetic `context`/`payload`, so a regression in any of the logic above
surfaces only as a wrong review on a real pull request.

## What to do

Decide the boundary first, because it determines whether this is a test task or
a refactor:

- **Extract, then test.** Move each `script:` body into a `.mjs` module the
  workflow loads, and test the modules directly with `bun test`. Costs a layer
  of indirection in the workflow and a decision about how a composite action
  ships JavaScript; buys ordinary unit tests.
- **Test in place.** Parse the workflow YAML, pull the `script:` string, and
  evaluate it against a stubbed `context`, `core`, and `github`. No production
  change, but the harness owns a copy of the action's contract and drifts when
  that contract moves.

Whichever is chosen, the cases worth covering are the ones a reviewer asked
about on [PR 163](https://github.com/plume-works/agent-devcontainer/pull/163): a
comment tier outranking a body marker, a body marker with no comment, an
unresolved tier emitting the empty value, an unrecognized label falling through,
and the responder model each tier produces.

## Why it is not urgent

The logic is small, and its current behavior was checked case by case before
merge — the marker and comment regexes against 14 inputs, the composed
`claude_args` against both branches. What is missing is the *regression* half:
nothing re-runs those checks when someone edits the workflow next. The risk is
therefore drift over time rather than a defect now, and it grows with each
further change to the responder rather than sitting still.
