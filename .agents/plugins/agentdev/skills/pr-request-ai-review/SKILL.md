---
name: pr-request-ai-review
description: 'Post the comment that triggers a fresh AI review on an open pull request, then confirm a run actually picked it up. Use when asked to request, re-request, or trigger an AI or Claude review of a PR, to ask for a re-review after new work landed, or to check whether a requested review started. This is a playbook, not a judgment call: deciding whether a re-review is warranted belongs to pr-eval-review-needed, and merge-time review recovery belongs to pr-merge.'
---

# Request an AI Review

Post the comment that triggers a fresh AI review on an open pull request, then
confirm the review actually started.

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

A posted comment is not a started review. Confirm a run picked it up, using
[pr-discover-ai-responder](../pr-discover-ai-responder/SKILL.md) to resolve the
responder workflow and list its `issue_comment` runs. Do not assume the
workflow's filename — it differs between repositories, and a wrong one returns
an empty list that reads exactly like "no run started".

Note that comment-triggered runs are filed against the default branch rather
than the PR head, so `gh pr checks` routinely does not list them.

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

## Related Skills

- [pr-discover-ai-responder](../pr-discover-ai-responder/SKILL.md) — resolve the
  responder workflow's filename and find its runs.
- [pr-eval-review-needed](../pr-eval-review-needed/SKILL.md) — decide whether
  pushed work warrants the request this skill posts.
