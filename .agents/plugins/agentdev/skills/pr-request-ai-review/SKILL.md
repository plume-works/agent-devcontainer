---
name: pr-request-ai-review
description: Use this skill to request an AI agent to review a pull request.
---

# Request an AI Review

Post the comment that triggers a fresh AI review on an open pull request, then
confirm the review actually started.

This is a playbook, not a judgment call: run it when a review has been asked
for, either by the user directly or by
[pr-eval-review-needed](../pr-eval-review-needed/SKILL.md), which decides when a
re-review is warranted. Do not evaluate here whether the request is justified.

## Post the request

The responder matches a mention that **opens** the comment body, so `@claude`
must be the first thing in it. A body that merely contains `@claude review`
while discussing it does not trigger anything.

Write the mention on the first line and a one-line rationale on the next, so a
later reader knows what changed since the previous review:

```bash
gh pr comment <pr> --body '@claude review
<one-line rationale for the re-review>'
```

Keep the rationale to a single line naming what the reviewer has not seen — for
example `Reworked the retry backoff beyond the thread's ask; please re-check the
new timer path.` Do not restate the diff, apologize, or summarize resolved
threads; the review itself reports findings.

## Confirm it started

A posted comment is not a started review. Confirm a run picked it up, and note
that comment-triggered runs are filed against the default branch rather than the
PR head — so `gh pr checks` routinely does not list them:

```bash
gh run list --workflow=ai-responder.yml --event issue_comment \
  --json databaseId,status,createdAt,url --limit 5
```

Report the comment URL and the run you observed. If no run appears within a
minute or two, say so plainly rather than posting the comment again — a
duplicate mention starts a second review.

## Rules

- Post the request **at most once per head SHA**. If more work lands afterward,
  that new head SHA is what justifies the next request.
- Never post the request while a review of the current head SHA is already
  running or already published.
- This comment is an operational trigger, not a status update. Do not bundle it
  with a resolution summary, a checklist, or review findings of your own.
- Never edit or delete a previously posted trigger to retry; push the work that
  justifies a new one.
