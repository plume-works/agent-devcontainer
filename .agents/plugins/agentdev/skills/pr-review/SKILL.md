---
name: pr-review
description: 'Perform a thorough automated code review of a GitHub pull request, publishing feedback as a single GitHub pull request review with inline comments (a standalone comment only as fallback when inline posting fails). Use when asked to review a pull request, or when a PR is opened/reopened and an automated review is required. Keywords: PR review, code review, pull request review, automated review.'
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)
---

# Review PR

Use this skill to review a pull request's diff and publish feedback as a GitHub **pull request review** — not a plain issue/PR comment. The workflow is agent-agnostic: Claude Code, Codex, and other assistants should follow the same review policy while adapting tool names to the environment they are running in.

## When to Use This Skill

- A pull request was just opened or reopened and needs an automated review
- Someone explicitly asks for a review of a pull request (for example, "@claude review this PR" or "@codex review this PR")

## Prerequisites

- `gh` must be installed and authenticated
- `jq` is required when using the bundled fallback script.
- REPO (`owner/name`) and PR NUMBER must be known — read them from the workflow context or ask the user if not provided
- The review is created, annotated, and submitted with three separate GitHub review tools:
  - `create_pending_pull_request_review` — open a pending review
  - `add_comment_to_pending_review` — attach each inline comment to the pending review
  - `submit_pending_pull_request_review` — submit the pending review with an `event`
- Codex-specific option: if the GitHub connector is available use
  `mcp__codex_apps__github._add_review_to_pr`, use that tool to submit the review in one call with:
  - `action`: `APPROVE` or `COMMENT`
  - `review`: the short overall summary body
  - `file_comments`: every validated inline finding, using `path`, `line`, `side`, and `body`

  This still creates a proper pull request review with inline comments, not a standalone PR comment.

- If those review tools are unavailable or uncertain, use the single-call fallback flow described after Step 8. **Never construct `gh api` review-posting calls by hand**.

## Review Focus

Two independent concerns feed two different pass types (see Steps below) so they can be reviewed without one blind spot masking the other.

**Compliance focus** (repo-convention adherence) — use a fast, instruction-following reviewer:

- Python and JavaScript/TypeScript style and idioms
- Any rule in the Coding Conventions section of the repository `AGENTS.md`, any skill applicable to the changed files (see Step 2), and any repo `CLAUDE.md`/`AGENTS.md` file that shares a path with the changed file or its parents
- IGNORE import ordering, that is handled by `ruff` and `clang-format` in CI
- Only flag a violation if you can quote the exact rule text being broken

**Correctness focus** (bug-hunting) — use the strongest available reasoning reviewer:

- Scan only the diff itself, without pulling in extra context beyond the diff and the PR title/description — do not flag anything you cannot validate from the diff alone
- Potential bugs, incorrect logic, and security implications introduced by the changed code
- Test coverage and quality
- Flag only significant, high-confidence issues; ignore nitpicks and likely false positives

**CRITICAL: we only want HIGH SIGNAL issues.** Flag an issue only when at least one of these holds:

- The code will fail to compile or parse (syntax errors, type errors, missing imports, unresolved references)
- The code will definitely produce wrong results regardless of inputs (clear, unambiguous logic errors)
- It's a clear, unambiguous compliance violation where you can quote the exact rule being broken

Do NOT flag:

- Code style or quality concerns
- Potential issues that depend on specific inputs or state
- Subjective suggestions or improvements

Flag only significant bugs; ignore nitpicks and likely false positives. Do not flag issues that you cannot validate without looking at context outside of the git diff.

**Documentation focus** (durable-knowledge adherence) — applies to docs under `data/`, `README.md`, `AGENTS.md`, skill and agent definitions (`SKILL.md`, `*.agent.md`), and docstrings:

- Run `/agentdev:iwe-audit` in diff mode over the changed docs/skills files. It scans the added lines for session residue and returns a `file:line | verdict | replacement | evidence` table (DROP / MOVE / REWRITE / KEEP); it does not restate its criteria here, and it applies nothing.
- Map each table row to an inline review comment: the `file:line` anchors the comment, and the verdict plus its replacement/destination becomes the comment body.
- **High-signal bar:** flag a finding only when you can quote the added line and name the specific rule it breaks — the same anti-nitpick threshold the Compliance focus uses. iwe-audit audits exhaustively; this bar filters its rows down to the review-worthy ones. Drop any row you cannot tie to a quoted line and a named rule.

**Severity tiers** (carried through Steps 3–8 on every candidate/validated finding):

- **Blocking (critical/P1)** — anything from a **correctness pass** (compile/parse failures, definite-wrong-result logic bugs, security implications) or a **durable-knowledge pass** (session residue a rule forbids). The tier governs Step-4 dedup priority and inline emphasis only; it never changes the submit event, which stays `COMMENT` (never `REQUEST_CHANGES`) per Step 8.
- **Non-blocking** — anything from a **compliance pass**: repo-convention/style violations, even though they're quoted-rule-confirmed.

## Steps

1. **Gate.** Run `gh pr view <PR_NUMBER>`. If the PR is a draft or already
   closed/merged, stop. For a version-only or generated-file-only diff, do not
   launch the review passes. Instead, confirm the changed file list with
   `gh pr diff <PR_NUMBER> --name-only`, then publish a clean `APPROVE` review
   with a short summary. This preserves the required AI-review gate for a
   mechanical PR without spending a full review cycle. A docs-only diff is not
   fast-approved: it still runs the durable-knowledge pass (Step 3).
2. **Gather context.** Fetch the diff (`gh pr diff <PR_NUMBER>`) and reuse the PR description from Step 1. From the changed-file list, determine which convention sources apply: the Coding Conventions section of `AGENTS.md` always applies; add the `/agentdev:python-format-lint` skill when the diff touches Python, `/agentdev:create-agent` for `*.agent.md` changes, and `/agentdev:create-skill` for `SKILL.md` changes.
3. **Run four or five independent initial-review passes in parallel when the environment supports it** — each pass sees only the diff, the PR title, the PR description, and its own focus list; none sees another pass's output. Each pass returns a list of issues, where each issue has a description and the reason it was flagged (for example, "AGENTS.md adherence", "bug", or "security"):
   - 2x **compliance pass** — audit the diff against the Compliance focus list and the convention sources found in Step 2.
   - 2x **correctness pass** — audit the diff against the Correctness focus list, one pass scanning for obvious bugs and the other for security/logic issues introduced by the changed code.
   - 1x **durable-knowledge pass**, only when the diff contains docs/skills files — audit the changed docs/skills files against the Documentation focus list.
   - **The lens follows the file.** The correctness passes scan code files, the durable-knowledge pass scans docs/skills files, and each ignores files outside its lens. On a mixed docs+code diff both lenses run against their own file subsets in the same review; on a code-only diff the durable-knowledge pass does not run and there are four passes.
   - Codex: use available multi-agent/sub-agent tools when present; otherwise perform the passes sequentially in this session, restarting the review lens from the diff for each pass.
   - Claude Code: issue the four or five `Agent` tool calls in a single message (`subagent_type: general-purpose`; use a fast model for compliance and the strongest available model for correctness and durable-knowledge).
   - **Block until every pass reports back or hard-times-out — see "Waiting on parallel passes" below.** Do not proceed to Step 4 with a pass still outstanding. **The turn in which you dispatch these workers must not be your last turn** — a dispatch-then-stop turn abandons the review with nothing published (see below).
4. **Merge and deduplicate.** Collect the candidate findings from all passes that completed (see fallback below if any didn't). Collapse candidates that name the same file/line and describe the same underlying issue into one, keeping the **blocking** tier if either collapsed candidate was blocking.
5. **Validate each candidate independently, in parallel when supported** — for every surviving candidate, run one validation pass that sees only that single candidate plus the diff/description (not the other candidates, not which pass raised it), and must confirm with high confidence that it is a real, worth-flagging issue. Drop any candidate the validator cannot confirm with high confidence. Preserve each surviving candidate's severity tier from Step 4 unchanged — validation confirms or drops a finding, it never changes its tier. Use the same runner-specific parallel-vs-sequential approach as Step 3, and the same blocking policy in "Waiting on parallel passes" below (cap: one blocking wait, up to 5 minutes per candidate; a validator that doesn't return in time counts as "cannot confirm" — drop the candidate).
6. Create a pending review with `create_pending_pull_request_review`.
7. For every validated finding, attach it as an inline comment on the exact file/line with `add_comment_to_pending_review` — this is the only place finding text goes; never describe a finding's location in prose. If GitHub rejects an inline location, do not drop the finding and do not let it block the review: continue with the remaining inline comments, and after submitting the review in Step 8 post that finding as a normal PR comment (`gh pr comment` or `add_issue_comment`) stating the file/line in prose and noting it could not be attached inline. This is the sole permitted use of a standalone PR comment.
8. Submit the review with `submit_pending_pull_request_review`, choosing `event` from the validated findings that survived Step 5:
   - **No validated findings at all → `APPROVE`.** A clean pass must be approved, not left as a silent `COMMENT`. A finding that fell back to a normal PR comment in Step 7 still counts as a finding → `COMMENT`.
   - **One or more validated findings, of any severity tier → `COMMENT`.** Never use `REQUEST_CHANGES`, even for blocking (critical/P1) findings — the severity tier still controls dedup priority in Step 4 and can be called out in the inline comment text, but it never changes the review event.

   `body` is limited to a short overall summary (no per-finding detail — that lives in the inline comments); for an `APPROVE` with zero findings, state plainly that no issues were found.

   Codex: if using `mcp__codex_apps__github._add_review_to_pr` instead of Steps 6-8, pass the same event as `action`,
   the summary as `review`, and all validated inline findings as `file_comments`.

### Waiting on Parallel Passes

Every parallel pass from Steps 3 and 5 must complete or be cancelled before
Steps 4–8. Block on outstanding tasks with the runner's wait primitive. Never
end a turn with an outstanding task, substitute a text status update, or poll
with a no-op shell command. If the runner has no blocking primitive, run the
passes sequentially.

**Self-check gate:** before emitting text or ending a turn, make a blocking call
for every dispatched task ID that has not returned.

Concretely:

- After dispatching a batch of workers, use the runner's blocking wait primitive for each task ID that has not reported back yet:
  - Codex: use the multi-agent tool's blocking output/wait facility if available; if no blocking worker primitive exists, do not launch background work — run the passes sequentially.
  - Claude Code: call `TaskOutput` with `block: true` and an explicit `timeout` (ms) for each outstanding task ID before ending the turn.
- **Budget, so Steps 4–8 still have room inside the action timeout:** per Step-3 pass, allow up to 16 minutes total — the durable-knowledge pass gets the same ceiling as the others. For Step 5 validation passes, allow up to 5 minutes each.
- **Hard fallback:** if a pass still has not completed when its ceiling is reached, stop/cancel it if the runner supports cancellation, drop that pass, and continue with only the passes/validations that did complete — do not block indefinitely on a single hung pass, and do not let one hang stall the whole review. Note in the final review summary body how many of the 4 or 5 initial passes completed if any were dropped (a completion-count status line, not a per-finding location reference, so it does not conflict with the "never write location references" constraint below).

## Fallback: single-call script

If the review tools above are confirmed unavailable, post the whole review — summary, event, and every inline comment — through the repository script in one atomic GitHub review API call. GitHub's `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews` endpoint accepts a `comments[]` array alongside `event` and `body`, so there is no pending-review state to manage or discard.

Write two plain files under `./.tmp` (never assemble this JSON live in a shell command):

- a summary file containing only the short overall review body (no per-finding detail)
- a comments file containing a JSON array of every validated finding: `[{"path": "file.py", "line": 42, "side": "RIGHT", "body": "finding text"}, ...]` (use `[]` or omit the file entirely if no findings survived Step 5)

Then run `${CLAUDE_SKILL_DIR}/scripts/post-review.sh --pr <PR_NUMBER> --event <COMMENT|APPROVE> --summary-file <path> --comments-file <path>` (run with `-h` for full usage; `--repo` defaults to the current repo via `gh repo view`). This single call replaces Steps 6–8 entirely, including the `event` decision rule from Step 8 (`APPROVE` when `[]`/no findings, `COMMENT` otherwise — never `REQUEST_CHANGES`). Do not fall further back to typing `gh api` calls by hand.

The last line of stdout is always `RESULT=<NAME>`; match on that name, not on a bare number:

| RESULT            | Exit | Meaning                                                                                 | Action                                                                                                                                                                                                                                                                                                                                                       |
| ----------------- | ---- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `SUCCESS`         | `0`  | The review was created and submitted                                                    | Done. The created review object is printed above the `RESULT` line.                                                                                                                                                                                                                                                                                          |
| `GH_CALL_FAILED`  | `3`  | A `gh` API call failed (repo/PR lookup, or the review POST)                             | If the error names a `comments[]` entry that cannot be placed inline (its file/line is outside the PR diff), remove that entry from the comments file, re-run the script, then post the removed finding as a normal PR comment (`gh pr comment`) stating the file/line in prose — same fallback as Step 7. Otherwise **STOP** and report the error verbatim. |
| `PREFLIGHT_ERROR` | `2`  | Usage error, a missing or malformed input file, or `gh`/`jq` missing or unauthenticated | **STOP.** Fix the reported problem — write the summary/comments file, correct the arguments, or report the missing prerequisite — then retry. Never hand-write the `gh api` call instead.                                                                                                                                                                    |
| `SCRIPT_FAILURE`  | `1`  | The script broke                                                                        | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                                                                                                                                                                                                                       |

## Constraints

- **Never post a standalone top-level PR comment** (`gh pr comment`, `add_issue_comment`, etc.) for review findings. All feedback must go through the pull request review flow (steps 6–8) so it renders as a proper review with threaded, resolvable inline comments. **Sole exception:** a validated finding whose inline attachment was attempted and rejected (Step 7 fallback) is posted as a normal PR comment so it is not silently lost.
- **Never write location references like "in `file.py` (line 42)" or "around line 10" in the review body or in chat.** Every finding tied to a specific file/line must be an actual inline comment on that file/line via `add_comment_to_pending_review`, not prose pointing at a location. The Step 7 fallback comment is the sole exception — there, an explicit file/line reference in prose is required precisely because the inline placement failed.
- Do not submit review text as plain chat/assistant messages.
- Keep each inline comment specific and actionable, scoped to the line(s) it annotates.
- Only findings that survived Step 5 validation may be posted — never publish an unvalidated candidate.
