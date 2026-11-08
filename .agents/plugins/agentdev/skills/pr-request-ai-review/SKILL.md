---
name: pr-request-ai-review
description: 'Request a fresh AI review of an open pull request by adding the request-ai-review label, then confirm a run actually picked it up. Use when asked to request, re-request, or trigger an AI, Claude, or bot review of a PR, to ask for a re-review after new work landed, or to check whether a requested review ever started — including indirect phrasings such as "ping the reviewer again" or "get the bot to take another look". This is the posting playbook, not the judgment call: whether new work warrants a re-review belongs to pr-eval-review-needed, and merge-time review recovery belongs to pr-merge.'
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
---

# Request an AI Review

Request a fresh AI review of an open pull request by adding the
`request-ai-review` label, then confirm a run actually picked it up. Whether the newest work needs a review at
all is a separate call, owned by
[pr-eval-review-needed](../pr-eval-review-needed/SKILL.md); this skill starts
once that answer is yes.

## Post the request

The responder reviews when the `request-ai-review` label is added, so the
bundled script requests a review by adding it. The responder removes the label
as soon as a run picks the request up, so a label still on the pull request is a
request no run has accepted yet. Assigning someone, requesting a reviewer, and an
`@claude review` comment request nothing. The script requests at
most once per head and title and description; see
[Post at most once per reviewed input](#post-at-most-once-per-reviewed-input).

```bash
agent-code/request-review.py --pr <pr> [--rationale '<one line>']
```

It prints `PR_NUMBER`, `HEAD_SHA`, `CHECK_URL` — the responder check already
covering this head — and `COMMENT_URL` — the posted rationale — and ends with a
`RESULT=` line:

| RESULT              | Exit                | What to do                                                                                                                                   |
| ------------------- | ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`           | 0                   | Report the added label and any `COMMENT_URL`, then confirm the review started.                                                               |
| `ALREADY_REVIEWED`  | 3                   | An accepted AI review newer than the last title or description edit names the head. Report it; request nothing.                              |
| `ALREADY_REQUESTED` | 4                   | The label is still on the pull request, or the responder check at `CHECK_URL` covers the head. Report it and confirm that one; do not retry. |
| `PR_NOT_OPEN`       | 5                   | The pull request is closed, merged, or not found. Stop and report.                                                                           |
| `GH_UNAVAILABLE`    | 6                   | `gh` is missing, unauthenticated, or failed, adding the label included. Stop and report stderr.                                              |
| `PREFLIGHT_ERROR`   | 2                   | Usage error: missing `--pr` or a multi-line rationale. Fix the call.                                                                         |
| `SCRIPT_FAILURE`    | 1                   | Unhandled error. Stop and report stderr.                                                                                                     |
| `SIGNAL_*`          | `129`, `130`, `143` | Interrupted by HUP, INT, or TERM. Stop; check the pull request's labels and checks before requesting again.                                  |

Run it with a token whose events start workflows, such as your own `gh` login.
A label added with an Actions `GITHUB_TOKEN` starts no run.

The rationale, when given, is posted as a plain comment,
`AI review requested for <sha>: <rationale>`. It does not steer the review —
the responder composes the reviewer's prompt itself — so write it for the
humans reading the thread later. One line naming what the reviewer has not seen
yet is enough, for example `Reworked the retry backoff beyond the thread's ask;
please re-check the new timer path.`

Skip the diff summary, the apology, and the roundup of resolved threads. The
review reports its own findings, and a status update wrapped around an
operational request makes the thread harder to read for everyone who comes
after it.

## Confirm it started

An added label is not a started review. The label starts a `pull_request`
run of `ai-responder.yml` on the head branch, and that run files
its checks on the head commit, so `gh pr checks` lists them:

```bash
gh pr checks <pr> --json name,state,link
```

A pending `Claude PR Review Responder` or `ai-review-present` check on the head
means the review started. Report that check. When neither appears, read the
`pull_request` run the label started on the head branch:

```bash
gh run list --workflow ai-responder.yml --event pull_request --branch <head-branch> \
  --json databaseId,status,conclusion,createdAt,url --limit 5
gh run view <run-id> --json jobs --jq '.jobs[] | {name, conclusion}'
```

The shape of that run points at the cause:

- **No run, label still on** — the label was added with a token whose events
  start no workflow, such as an Actions `GITHUB_TOKEN`.
- **Label still on after the run** — the pull request is bot-authored or comes
  from a fork, so no preflight ran to accept the request.
- **Preflight failed** — the person whose token added the label lacks write
  access.
- **Preflight passed, then the review job skipped** — the pull request is a
  draft.
- **A review check completed without a review** — report that review run's
  failure from its log.

The first four need a person rather than a retry. If none of these applies and
the check is simply still pending, say so plainly instead of requesting again.

## Post at most once per reviewed input

A review is a full container run against one commit and the title and
description it read, so that is the unit: a new head or an edit to either is
what makes an existing review stale, and what justifies the next request. Push
the work first, then request the review for the head that push produced. After
a metadata-gate stop, fix the title or description instead; the edit alone
lets the script request a review of the same head.

Request at most one review per head and title and description.
`request-review.py` enforces the rule whoever started the review: a
`Claude PR Review Responder` check on the head that is queued or in progress,
or started after the latest title or description edit and completed other than
skipped or cancelled, is that input's request. A run reads the title and
description when it starts, so a review submitted by a run that started before
the edit does not count either. A skipped responder is the gate-only run a
push to a reviewed pull request starts, so it does not count. No skill requests
a review any other way.

When a run genuinely fails without publishing a review, inspect its logs and
report that failure; wait for a new head, a title or description edit, or
explicit user direction before requesting again.

## Related Skills

- [pr-eval-review-needed](../pr-eval-review-needed/SKILL.md) — decide whether
  pushed work warrants the request this skill posts.
- [pr-merge](../pr-merge/SKILL.md) — merge-time recovery when the AI-review gate
  is red, including when to trigger and when to escalate.
