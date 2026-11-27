# Publishing a review

Publish every review as a GitHub **pull request review**, never as a plain
issue or PR comment.

## Verdict

- No findings, or only findings that do not block → `APPROVE`.
- Any finding that blocks, inline or not, including the metadata gate →
  `REQUEST_CHANGES`.
- GitHub rejects `APPROVE` or `REQUEST_CHANGES` because the account owns the
  PR → retry once as `COMMENT`, and say in the body that the account cannot
  approve or request changes on its own PR. This is the only `COMMENT` review.

## Body

- A short overall summary only; per-finding detail goes in inline comments.
- An `APPROVE` with no findings states plainly that no issues were found.
- Name any blocking finding that has no inline anchor, such as a metadata
  gate finding.

## Inline comments

- Publish only findings that survived validation.
- Every finding tied to a place in the diff is an inline comment on its exact
  file and line, specific and actionable, scoped to the lines it annotates.
- Never write a location as a line number in the body, a comment, or chat.
  The inline comment's `line` field is the only machine position you write.

## Standalone comment

- Never post a top-level PR comment (`gh pr comment`, `add_issue_comment`)
  for a finding, with one exception: GitHub rejected the finding's inline
  location.
- Then do not drop the finding or let it block the review: publish the rest,
  and after submitting, post that finding as a PR comment that names its
  location by anchor and says it could not be attached inline.

## Chat

Never submit review text as a chat or assistant message.

## Review tools

1. `create_pending_pull_request_review` — open a pending review.
2. `add_comment_to_pending_review` — attach each inline comment.
3. `submit_pending_pull_request_review` — submit with the verdict as `event`
   and the body.

When these tools are unavailable or uncertain, use the single-call script.
Never write a `gh api` review call by hand.

## Single-call script

Write two files under `./.tmp`, never JSON assembled in a shell command:

- a summary file holding only the body;
- a comments file holding a JSON array of every finding,
  `[{"path": "<file>", "line": <n>, "side": "RIGHT", "body": "<text>"}]`;
  `[]`, or no file, when there are none.

Run
`agent-code/post-review --pr <PR_NUMBER> --event <APPROVE|REQUEST_CHANGES|COMMENT> --summary-file <path> --comments-file <path>`
([post-review](../agent-code/post-review); `-h` for usage; `--repo`
defaults to the current repository). It replaces the three review tools;
choose `event` by the verdict rules above.

The last line of stdout is always `RESULT=<NAME>`; match on that name:

| RESULT            | Exit | Meaning                                                                            | Action                                                                                                                                                                                 |
| ----------------- | ---- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`         | `0`  | The review was created and submitted                                               | Done.                                                                                                                                                                                  |
| `GH_CALL_FAILED`  | `3`  | A `gh` API call failed                                                             | If the error names a `comments[]` entry outside the diff, remove it, re-run, then post it as a standalone comment by the rule above. Otherwise **STOP** and report the error verbatim. |
| `PREFLIGHT_ERROR` | `2`  | Usage error, a missing or malformed input file, or `gh` missing or unauthenticated | **STOP.** Fix the reported problem, then retry. Never hand-write the `gh api` call.                                                                                                    |
| `SCRIPT_FAILURE`  | `1`  | The script broke                                                                   | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                                                 |
