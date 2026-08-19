---
name: pr-request-ai-review
description: 'Post the comment that triggers a fresh AI review on an open pull request, then confirm a run actually picked it up. Use when asked to request, re-request, or trigger an AI, Claude, or bot review of a PR, to ask for a re-review after new work landed, or to check whether a requested review ever started — including indirect phrasings such as "ping the reviewer again" or "get the bot to take another look". This is the posting playbook, not the judgment call: whether new work warrants a re-review belongs to pr-eval-review-needed, and merge-time review recovery belongs to pr-merge.'
---

# Request an AI Review

Post the comment that triggers a fresh AI review on an open pull request, then
confirm a run actually picked it up. Whether the newest work needs a review at
all is a separate call, owned by
[pr-eval-review-needed](../pr-eval-review-needed/SKILL.md); this skill starts
once that answer is yes.

## Post the request

The responder's preflight matches a mention that **opens** the comment body —
`startsWith`, not `contains`. A substring test cannot tell an invocation from a
discussion, so any comment quoting `@claude` while talking _about_ the
responder would start a container job. `@claude` therefore has to be the first
thing in the body, and a body that merely contains `@claude review` mid-sentence
triggers nothing.

Those opening words also select what runs: `@claude review` asks for the pull
request review, while `@claude` followed by anything else is dispatched as a
free-form task built from the rest of the body. Keep the first line exactly
`@claude review`, and put a one-line rationale under it:

```bash
gh pr comment <pr> --body '@claude review
<one-line rationale for the re-review>'
```

The rationale does not steer the review — the responder composes the reviewer's
prompt itself — so write it for the humans reading the thread later. One line
naming what the reviewer has not seen yet is enough, for example `Reworked the
retry backoff beyond the thread's ask; please re-check the new timer path.`

Skip the diff summary, the apology, and the roundup of resolved threads. The
review reports its own findings, and a status update wrapped around an
operational trigger makes the thread harder to read for everyone who comes
after it.

## Confirm it started

A posted comment is not a started review. Resolve the responder workflow and
list its `issue_comment` runs with
[pr-discover-ai-responder](../pr-discover-ai-responder/SKILL.md) rather than
assuming the workflow's filename: it differs between repositories, and a wrong
one returns an empty list that reads exactly like "no run started".

`gh pr checks` will not settle it either. Comment-triggered runs are filed
against the default branch rather than the PR head, so the PR's check list
routinely omits them even while the review is running.

Report the comment URL and the run you observed. When nothing turns up, the
shape of the gap points at the cause:

- **No run at all** — the mention never qualified. Re-read the comment as
  posted and confirm it truly opens with `@claude`.
- **A run that ends without a review** — the preflight rejected the request.
  These workflows commonly refuse pull requests from forks and requesters
  without write access; either one ends the run before a review happens, and
  both need a person rather than a retry.

If neither applies and the run is simply slow, say so plainly instead of
posting the comment again.

## Post at most once per head SHA

A review is a full container run against one commit, so the head SHA is the
unit: it is what makes an existing review stale, and it is what justifies the
next request. Push the work first, then request the review for the head that
push produced.

While a review of the current head is running or already published, another
mention buys noise rather than information. Responder concurrency is keyed to
the comment id, so a second mention does not supersede the first — both runs
proceed and both post findings.

Retrying by editing or deleting the trigger does not work either: the workflow
listens for `issue_comment: created` only, so an edit never re-triggers, and
deleting the comment just erases the thread's record of what was requested.
When a run genuinely fails without publishing a review, inspect its logs and
report that failure; wait for a new head SHA or explicit user direction before
triggering again.

## Related Skills

- [pr-eval-review-needed](../pr-eval-review-needed/SKILL.md) — decide whether
  pushed work warrants the request this skill posts.
- [pr-discover-ai-responder](../pr-discover-ai-responder/SKILL.md) — resolve the
  responder workflow's filename and find its runs.
- [pr-merge](../pr-merge/SKILL.md) — merge-time recovery when the AI-review gate
  is red, including when to trigger and when to escalate.
