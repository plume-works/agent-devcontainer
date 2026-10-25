---
name: pr-request-ai-review
description: 'Post the comment that triggers a fresh AI review on an open pull request, then confirm a run actually picked it up. Use when asked to request, re-request, or trigger an AI, Claude, or bot review of a PR, to ask for a re-review after new work landed, or to check whether a requested review ever started — including indirect phrasings such as "ping the reviewer again" or "get the bot to take another look". This is the posting playbook, not the judgment call: whether new work warrants a re-review belongs to pr-eval-review-needed, and merge-time review recovery belongs to pr-merge.'
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
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
free-form task built from the rest of the body. The bundled script posts a
body whose first line is exactly `@claude review`, with a one-line rationale
under it:

```bash
agent-code/request-review.sh --pr <pr> --rationale '<one line>'
```

It prints `PR_NUMBER`, `HEAD_SHA`, and `COMMENT_URL` — the posted trigger, or the
one already requesting this head — and ends with a `RESULT=` line:

| RESULT              | Exit | What to do                                                                                    |
| ------------------- | ---- | --------------------------------------------------------------------------------------------- |
| `SUCCESS`           | 0    | Report `COMMENT_URL`, then confirm the review started.                                        |
| `ALREADY_REVIEWED`  | 3    | An accepted AI review already names the head. Report it; post nothing.                        |
| `ALREADY_REQUESTED` | 4    | A trigger for the head exists at `COMMENT_URL`. Report it and confirm that one; do not retry. |
| `PR_NOT_OPEN`       | 5    | The pull request is closed, merged, or not found. Stop and report.                            |
| `GH_UNAVAILABLE`    | 6    | `gh` is missing, unauthenticated, or failed. Stop and report the blocker.                     |
| `PREFLIGHT_ERROR`   | 2    | Usage error: missing `--pr`, a multi-line rationale, or no `jq`. Fix the call.                |
| `SCRIPT_FAILURE`    | 1    | Unhandled error. Stop and report stderr.                                                      |

The rationale does not steer the review — the responder composes the reviewer's
prompt itself — so write it for the humans reading the thread later. One line
naming what the reviewer has not seen yet is enough, for example `Reworked the
retry backoff beyond the thread's ask; please re-check the new timer path.`

Skip the diff summary, the apology, and the roundup of resolved threads. The
review reports its own findings, and a status update wrapped around an
operational trigger makes the thread harder to read for everyone who comes
after it.

## Confirm it started

A posted comment is not a started review. The trigger dispatches the responder
on the pull request's head branch, so the review's checks attach to the head
commit and `gh pr checks` lists them:

```bash
gh pr checks <pr> --json name,state,link
```

A pending `Claude PR Review Responder` or `ai-review-present` check on the head
means the review started. Report the comment URL and that check. When neither
appears, read the `issue_comment` run the comment started on the default branch,
the one created just after it:

```bash
gh run list --workflow ai-responder.yml --event issue_comment \
  --json databaseId,status,conclusion,createdAt,url --limit 5
gh run view <run-id> --json jobs --jq '.jobs[] | {name, conclusion}'
```

The shape of that run points at the cause:

- **Every job skipped** — the mention never qualified. Re-read the comment as
  posted and confirm it truly opens with `@claude`.
- **Preflight failed, or the bridge (`Dispatch on the pull request branch`)
  skipped or failed** — no review was dispatched: the requester lacks write
  access, the pull request comes from a fork, or its head branch has no
  `ai-responder.yml`. Each needs a person rather than a retry.
- **The bridge succeeded, then a review check completed without a review** —
  report that review run's failure from its log.

If none of these applies and the check is simply still pending, say so plainly
instead of posting the comment again.

## Post at most once per head SHA

A review is a full container run against one commit, so the head SHA is the
unit: it is what makes an existing review stale, and it is what justifies the
next request. Push the work first, then request the review for the head that
push produced.

Post at most one trigger per head SHA. Responder concurrency is keyed to the
comment ID, so a second comment starts a separate run instead of superseding
the first. `request-review.sh` enforces the rule for every trigger on the head,
whoever posted it: a trigger it posts carries a `review-head` marker naming its
commit, and a hand-typed one counts when it was created after the head's
earliest check suite. No skill posts a trigger any other way.

The workflow listens for `issue_comment: created` only, so editing a trigger does
not start another run. Do not delete the trigger comment.
When a run genuinely fails without publishing a review, inspect its logs and
report that failure; wait for a new head SHA or explicit user direction before
triggering again.

## Related Skills

- [pr-eval-review-needed](../pr-eval-review-needed/SKILL.md) — decide whether
  pushed work warrants the request this skill posts.
- [pr-merge](../pr-merge/SKILL.md) — merge-time recovery when the AI-review gate
  is red, including when to trigger and when to escalate.
