---
name: pr-discover-ai-responder
description: Resolve which GitHub Actions workflow answers an `@claude review` mention, and find its runs for a pull request. Use before any `gh run list --workflow=` query about an AI review, when a responder run seems missing because `gh pr checks` does not list it, or when the responder's filename is unknown or differs between repositories (`ai-responder.yml` and `claude-review.yml` are both in use). Requesting a review belongs to pr-request-ai-review; merge policy belongs to pr-merge.
---

# Discover the AI Responder Workflow

The workflow that answers `@claude review` is not named the same in every
repository. A wrong filename makes every `gh run list --workflow=` query return
nothing, which reads exactly like "no responder ran" — so resolve the name
before querying, and never assume it.

## Resolve the workflow

```bash
${CLAUDE_SKILL_DIR}/scripts/discover-ai-responder.sh
```

On success it prints `RESPONDER_WORKFLOW=<filename>`. Capture it for the queries
below:

```bash
RESPONDER_WORKFLOW=$(
  ${CLAUDE_SKILL_DIR}/scripts/discover-ai-responder.sh | sed -n 's/^RESPONDER_WORKFLOW=//p'
)
```

| RESULT                  | Exit | What to do                                                                                                                                                                 |
| ----------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`               | 0    | Use the emitted filename for every query below.                                                                                                                            |
| `NO_RESPONDER_WORKFLOW` | 3    | No workflow name matched. Re-run with `--pattern` if it is named differently; otherwise report that this repository has no AI responder rather than that a run is missing. |
| `AMBIGUOUS_WORKFLOW`    | 4    | Several matched, and they are listed on stderr. Pick one with `--workflow`, or narrow with `--pattern`. Do not guess.                                                      |
| `GH_UNAVAILABLE`        | 5    | `gh` is missing or unauthenticated. Report the blocker; this is not evidence about any run.                                                                                |
| `PREFLIGHT_ERROR`       | 2    | Usage error. Check the arguments.                                                                                                                                          |
| `SCRIPT_FAILURE`        | 1    | Unhandled error. Inspect stderr.                                                                                                                                           |

Pass `--workflow <file>` to skip discovery when the filename is already known;
the output shape is unchanged, so a caller can use one code path either way.

## Find its runs

**`gh pr checks <pr>` is not sufficient to find these runs.** The responder
workflow triggers on `issue_comment`, `pull_request_review`, and
`pull_request_review_comment` in addition to `pull_request`. For those
non-`pull_request` events, GitHub records the run against `context.sha` /
`context.ref` — the repository's default branch — not the PR's head SHA, even
though the workflow's "Determine checkout ref" step then checks out the PR's
real head commit internally. Because `gh pr checks` only lists checks attached
to the PR head commit, a responder run started by an `@claude review` comment
routinely never appears there, including while it is still running. Always
cross-check the workflow's own run list instead of trusting `gh pr checks`
alone:

```bash
# All recent responder runs, regardless of which branch/SHA GitHub filed them under
gh run list --workflow="$RESPONDER_WORKFLOW" \
  --json databaseId,status,conclusion,event,headBranch,headSha,createdAt,url,displayTitle \
  --limit 20

# Narrow to in-flight runs only
gh run list --workflow="$RESPONDER_WORKFLOW" --status in_progress \
  --json databaseId,event,createdAt,url,displayTitle
gh run list --workflow="$RESPONDER_WORKFLOW" --status queued \
  --json databaseId,event,createdAt,url,displayTitle

# Narrow to runs from comment triggers specifically (these are the ones gh pr checks misses)
gh run list --workflow="$RESPONDER_WORKFLOW" --event issue_comment \
  --json databaseId,status,conclusion,createdAt,url,displayTitle --limit 10
```

## Confirm a run belongs to this PR

For comment-triggered runs the `headBranch` will usually read as the default
branch rather than the PR branch, so the run list alone does not tell you which
PR a run is reviewing. Open the run and check the "Determine checkout ref" step
output, or the PR number embedded in its logs:

```bash
gh run view <run-id> --json databaseId,status,conclusion,event,headBranch,headSha,url
gh run view <run-id> --log | grep -A3 'Determine checkout ref'
```

To wait on a run already confirmed to belong to this PR:

```bash
gh run watch <run-id> --exit-status
```

Workflow start is not completion. Treat a run as finished only when its `status`
reaches `completed`, then re-read the PR's reviews and checks.

## Related Skills

- [pr-request-ai-review](../pr-request-ai-review/SKILL.md) — post the comment
  that triggers a review, then confirm it started.
- [pr-merge](../pr-merge/SKILL.md) — merge-time policy for a failed AI-review
  gate, including when to trigger and when to escalate.
