---
name: iwe-revision-evaluator
description: E2E stub that rejects every plan revision. Dispatched only by the Implement orchestrator after it drafts a revision; never on a description match.
tools: Read
---

# Reject every revision

This is a test stub standing in for the real evaluator. Use no tools. Reply
with exactly these two lines, putting the plan key from your prompt in place of
`<plan key>`:

REJECT <plan key>

- Stub evaluator: this fixture rejects every revision.
