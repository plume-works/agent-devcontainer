---
name: exec-summary
description: Translate whatever is in focus — the current thread, a plan, bug, feature, or PR — into a one-minute, non-technical executive summary. Use when asked for an executive view, a plain-language summary, a "1 minute version", or a non-technical explanation of the work. Technical PR descriptions belong to /agentdev:pr-gen-description and the graph-wide weekly digest to /agentdev:iwe-weekly.
---

# Executive summary

Translate the target into a summary a non-technical reader can absorb in about
a minute. Print it in the conversation; write nothing to disk.

## Target

- No argument: the current conversation's work.
- A graph key, PR, or issue: read it fresh before summarizing — never from
  memory.

## Shape

Bold lead-ins, in this order, omitting any that are genuinely empty:

**The problem** · **The fix** (or **The decision**) · **Why this approach** ·
**What's involved** · **What's not included** · **Risk** · **Status**

## Rules

- 150–200 words. No file paths, function names, or tool names.
- Outcome first: what users experience, not how the code works.
- Risk and status only as the source supports them — "planned" never reads as
  "done", and "low risk" needs a reason.
