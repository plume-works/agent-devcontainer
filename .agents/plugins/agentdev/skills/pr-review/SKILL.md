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

- If those review tools are unavailable or uncertain, use the single-call fallback flow described after Step 9. **Never construct `gh api` review-posting calls by hand**.

## Review Focus

Two independent concerns feed two different pass types (see Steps below) so they can be reviewed without one blind spot masking the other.

**Compliance focus** (repo-convention adherence) — runs on the `light` model at both tiers, per the effort matrix:

- Python and JavaScript/TypeScript style and idioms
- Any rule in the Coding Conventions section of the repository `AGENTS.md`, any skill applicable to the changed files (see Step 2), and any repo `CLAUDE.md`/`AGENTS.md` file that shares a path with the changed file or its parents
- IGNORE import ordering, that is handled by `ruff` and `clang-format` in CI
- Only flag a violation if you can quote the exact rule text being broken

**Correctness focus** (bug-hunting) — runs on the model the effort matrix gives it:

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

**PR metadata focus** (title/description relevance) — use `/agentdev:pr-gen-description` before the in-depth passes:

- Compare the current PR title and description from Step 1 against the actual PR diff, base branch, and repository pull request template.
- The title must describe the main change, and the description must cover the material changes, testing actually performed, breaking changes, migration or rollout requirements, and related issues or docs when they apply.
- Flag only material stale, misleading, missing, or irrelevant title/description content. Do not block on wording polish or optional detail.

**Severity tiers** (carried through Steps 4–9 on every candidate/validated finding):

- **Blocking (critical/P1)** — anything from a **correctness pass** (compile/parse failures, definite-wrong-result logic bugs, security implications) or a **durable-knowledge pass** (session residue a rule forbids). Governs Step-5 dedup priority, inline emphasis, and the submit event per Step 9.
- **Blocking metadata gate** — a material PR title/description mismatch from the **PR metadata focus**. Stops the review before the in-depth passes and submits a `REQUEST_CHANGES` review with the metadata finding in the review body (Step 3).
- **Non-blocking** — anything from a **compliance pass**: repo-convention/style violations, even though they're quoted-rule-confirmed.

## Effort Tiers

The review runs at one of two effort tiers, `light` or `full`. The responder workflow resolves the tier from an `@claude review light`/`@claude review full` comment or a `[ci:review-effort=light]`/`[ci:review-effort=full]` marker alone on a line of the PR body, and hands it to this skill as a `REQUESTED REVIEW EFFORT` line in the prompt.

**A requested tier is absolute.** Run the tier you were handed, exactly. Never escalate to the other tier, refuse the review, or fail it because the diff looks like a poor fit for the tier — that call belongs to whoever requested it.

**With no tier in the prompt, size the review yourself** from the diff you already hold: how many passes to run, which model each slot gets, and how deep the durable-knowledge pass goes. This is the same judgment Step 1 makes when it fast-approves a mechanical diff.

Model sizes, unversioned so each name resolves to that model's latest release:

| Size    | Claude            | Codex           |
| ------- | ----------------- | --------------- |
| `large` | `claude-opus-5`   | `gpt-5.6-sol`   |
| `light` | `claude-sonnet-5` | `gpt-5.6-terra` |

Which size each slot gets, and how many of it run:

| Slot          | light effort     | full effort          |
| ------------- | ---------------- | -------------------- |
| orchestrator  | light            | large                |
| metadata gate | light            | large                |
| compliance    | 1x light         | 2x light             |
| correctness   | 1x light         | 2x large             |
| iwe-audit     | light            | large                |
| validation    | one batch, light | per-candidate, light |

The rule in one line: at full effort everything is `large` except compliance and validation, which stay `light` at both tiers; at light effort everything is `light`. The orchestrator row is set by the workflow's `--model`, not from this skill — the rest are yours to pass.

Both tiers run the same checks. The Step 3 metadata gate and the Step 4 durable-knowledge pass run at `light` exactly as they do at `full`: the light tier is a cheaper review, not a weaker one. The Step 1 mechanical fast-approve and its docs-only exclusion are unaffected by the tier.

## Steps

1. **Gate.** Run `gh pr view <PR_NUMBER>`. If the PR is a draft or already
   closed/merged, stop. For a version-only or generated-file-only diff, do not
   launch the review passes. Instead, confirm the changed file list with
   `gh pr diff <PR_NUMBER> --name-only`, then publish a clean `APPROVE` review
   with a short summary. This preserves the required AI-review gate for a
   mechanical PR without spending a full review cycle. A docs-only diff is not
   fast-approved: it still runs the durable-knowledge pass (Step 4).
2. **Gather context.** Fetch the diff (`gh pr diff <PR_NUMBER>`) and reuse the PR title and description from Step 1. From the changed-file list, determine which convention sources apply: the Coding Conventions section of `AGENTS.md` always applies; add `/agentdev:create-agent` for `*.agent.md` changes, and `/agentdev:create-skill` for `SKILL.md` changes.
3. **PR metadata gate.** Use `/agentdev:pr-gen-description` as a relevance and completeness check against the current PR title, PR description, diff, base branch, and repository pull request template. When reviewing a PR that is not checked out locally, apply that skill's analysis and validation criteria to the fetched PR diff instead of mutating the branch or PR. If the current title or description is materially stale, misleading, irrelevant, or incomplete for the actual change set, submit a `REQUEST_CHANGES` pull request review with a short blocking summary of the metadata problem and **stop before launching the in-depth review passes**. Do not update the title or description from this skill. If the metadata is acceptable, continue.
4. **Run the independent initial-review passes the effort matrix names, in parallel when the environment supports it** — each pass sees only the diff, the PR title, the PR description, and its own focus list; none sees another pass's output. Each pass returns a list of issues, where each issue has a description and the reason it was flagged (for example, "AGENTS.md adherence", "bug", or "security"):
   - **compliance pass** — audit the diff against the Compliance focus list and the convention sources found in Step 2. 2x at full effort, 1x at light.
   - **correctness pass** — audit the diff against the Correctness focus list. 2x at full effort, one pass scanning for obvious bugs and the other for security/logic issues introduced by the changed code; 1x at light, covering both.
   - 1x **durable-knowledge pass**, only when the diff contains docs/skills files — audit the changed docs/skills files against the Documentation focus list. It runs at both tiers.
   - **The lens follows the file.** The correctness passes scan code files, the durable-knowledge pass scans docs/skills files, and each ignores files outside its lens. On a mixed docs+code diff both lenses run against their own file subsets in the same review; on a code-only diff the durable-knowledge pass does not run, leaving four passes at full effort and two at light.
   - **Pass each dispatch the model its slot gets in the effort matrix.** A dispatch that carries no model argument runs at the session's own model, whatever the matrix says — the argument is what puts the matrix in force.
   - Codex: use available multi-agent/sub-agent tools when present, giving each the Codex model for its slot; otherwise perform the passes sequentially in this session, restarting the review lens from the diff for each pass.
   - Claude Code: issue the `Agent` tool calls in a single message (`subagent_type: general-purpose`), each with the `model` for its slot. The `Agent` tool says subagents run in the background and notify you on completion. **That is true only where there is a next turn to be notified in.** This skill's main caller is the responder action, a headless `claude -p` run that ends the moment you stop emitting — no notification ever arrives, and the review is lost with the session.
   - **Block until every pass reports back or hard-times-out — see "Waiting on parallel passes" below.** Do not proceed to Step 5 with a pass still outstanding. **The turn in which you dispatch these workers must not be your last turn** — a dispatch-then-stop turn abandons the review with nothing published (see below).
5. **Merge and deduplicate.** Collect the candidate findings from all passes that completed (see fallback below if any didn't). Collapse candidates that name the same file/line and describe the same underlying issue into one, keeping the **blocking** tier if either collapsed candidate was blocking.
6. **Validate the surviving candidates, on the `light` model at both tiers.** A validator must confirm with high confidence that a candidate is a real, worth-flagging issue; drop any candidate it cannot confirm. Preserve each surviving candidate's severity tier from Step 5 unchanged — validation confirms or drops a finding, it never changes its tier.
   - **One validator prompt, identical at both tiers.** It carries the candidate's file and line, the added text quoted, the claim made against it, the full text of any rule that claim invokes, where to read the diff, and that the working tree is already at the head commit so files can be read for ground truth. It never names which pass raised a candidate.
   - **Make the validator re-derive the claim** from the files rather than trust the candidate's assertion of it, and tell it to drop anything ambiguous, trivial, or not clearly a violation. Ask for `CONFIRM` or `DROP` per candidate with a one-sentence justification.
   - **Never argue the verdict in the prompt.** Supplying reasons a candidate might not hold, or casting the validator as an adversary out to defeat it, settles the verdict before a file is read. Strictness belongs in the bar the validator applies, never in a case the orchestrator makes for one side.
   - **Full effort: one dispatch per candidate**, in parallel when supported, each seeing only that single candidate. Per-candidate isolation is what stops a weak finding reading as strong beside three strong ones, so it is not traded away at this tier.
   - **Light effort: one batched dispatch** carrying every surviving candidate at once and returning a confirm-or-drop verdict for each. This gives up the isolation the full tier keeps, in exchange for one call instead of one per finding.
   - Use the same runner-specific parallel-vs-sequential approach as Step 4, and the same blocking policy and ceilings in "Waiting on parallel passes" below. A validator that does not return inside its ceiling counts as "cannot confirm" — drop the candidate, or at light effort every candidate in the batch.
7. Create a pending review with `create_pending_pull_request_review`.
8. For every validated finding, attach it as an inline comment on the exact file/line with `add_comment_to_pending_review` — this is the only place finding text goes; never describe a finding's location in prose. If GitHub rejects an inline location, do not drop the finding and do not let it block the review: continue with the remaining inline comments, and after submitting the review in Step 9 post that finding as a normal PR comment (`gh pr comment` or `add_issue_comment`) stating the file/line in prose and noting it could not be attached inline. This is the sole permitted use of a standalone PR comment.
9. Submit the review with `submit_pending_pull_request_review`, choosing `event` from the validated findings that survived Step 6:
   - **No validated findings → `APPROVE`.** Do not leave a clean pass as a silent `COMMENT`.
   - **A blocking finding with no live inline anchor** — the Step-3 metadata gate, or a blocking finding whose inline location GitHub rejected in Step 8 and that fell back to a prose PR comment — **→ `REQUEST_CHANGES`.** Name those findings in the body.
   - **Otherwise (every blocking finding is attached inline, or only non-blocking findings remain) → `COMMENT`.**

   `body` is limited to a short overall summary (no per-finding detail — that lives in the inline comments); for an `APPROVE` with zero findings, state plainly that no issues were found. If GitHub rejects `REQUEST_CHANGES` because the account owns the PR, retry as `COMMENT` and note in the body that the account could not request changes on its own PR.

   Codex: if using `mcp__codex_apps__github._add_review_to_pr` instead of Steps 7-9, pass the same event as `action`,
   the summary as `review`, and all validated inline findings as `file_comments`.

### Waiting on Parallel Passes

Every parallel pass from Steps 4 and 6 must complete or be cancelled before
Steps 5–9. Block on outstanding tasks with the runner's wait primitive. Never
end a turn with an outstanding task, substitute a text status update, or poll
with a no-op shell command. If the runner has no blocking primitive, run the
passes sequentially.

**Self-check gate:** before emitting text or ending a turn, make a blocking call
for every dispatched task ID that has not returned.

Text announcing that you are waiting is not waiting. If the next thing you were
about to produce is a sentence about outstanding passes, replace it with the
blocking call itself — under the responder action the run ends with your turn,
and `bugs/review-orchestrator-ends-turn-while-passes-run` records what that
costs.

Concretely:

- After dispatching a batch of workers, use the runner's blocking wait primitive for each task ID that has not reported back yet:
  - Codex: use the multi-agent tool's blocking output/wait facility if available; if no blocking worker primitive exists, do not launch background work — run the passes sequentially.
  - Claude Code: call `TaskOutput` with `block: true` and an explicit `timeout` (ms) for each outstanding task ID before ending the turn.
- **Budget, so Steps 5–9 still have room inside the action timeout:** per Step-4 pass, allow up to 16 minutes total — the durable-knowledge pass gets the same ceiling as the others. For Step 6, allow up to 5 minutes per candidate validation at full effort; a light-effort batch judges every candidate in a single call, so it gets the same 16-minute ceiling as a Step-4 pass rather than one candidate's 5 minutes.
- **Hard fallback:** if a pass still has not completed when its ceiling is reached, stop/cancel it if the runner supports cancellation, drop that pass, and continue with only the passes/validations that did complete — do not block indefinitely on a single hung pass, and do not let one hang stall the whole review. Note in the final review summary body how many of the initial passes completed if any were dropped (a completion-count status line, not a per-finding location reference, so it does not conflict with the "never write location references" constraint below).

## Fallback: single-call script

If the review tools above are confirmed unavailable, post the whole review — summary, event, and every inline comment — through the repository script in one atomic GitHub review API call. GitHub's `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews` endpoint accepts a `comments[]` array alongside `event` and `body`, so there is no pending-review state to manage or discard.

Write two plain files under `./.tmp` (never assemble this JSON live in a shell command):

- a summary file containing only the short overall review body (no per-finding detail)
- a comments file containing a JSON array of every validated finding: `[{"path": "file.py", "line": 42, "side": "RIGHT", "body": "finding text"}, ...]` (use `[]` or omit the file entirely if no findings survived Step 6)

Then run `${CLAUDE_SKILL_DIR}/scripts/post-review.sh --pr <PR_NUMBER> --event <COMMENT|APPROVE|REQUEST_CHANGES> --summary-file <path> --comments-file <path>` (run with `-h` for full usage; `--repo` defaults to the current repo via `gh repo view`). This single call replaces Steps 7–9 entirely; pick the `event` by the Step 9 rule. Do not fall further back to typing `gh api` calls by hand.

The last line of stdout is always `RESULT=<NAME>`; match on that name, not on a bare number:

| RESULT            | Exit | Meaning                                                                                 | Action                                                                                                                                                                                                                                                                                                                                                       |
| ----------------- | ---- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `SUCCESS`         | `0`  | The review was created and submitted                                                    | Done. The created review object is printed above the `RESULT` line.                                                                                                                                                                                                                                                                                          |
| `GH_CALL_FAILED`  | `3`  | A `gh` API call failed (repo/PR lookup, or the review POST)                             | If the error names a `comments[]` entry that cannot be placed inline (its file/line is outside the PR diff), remove that entry from the comments file, re-run the script, then post the removed finding as a normal PR comment (`gh pr comment`) stating the file/line in prose — same fallback as Step 8. Otherwise **STOP** and report the error verbatim. |
| `PREFLIGHT_ERROR` | `2`  | Usage error, a missing or malformed input file, or `gh`/`jq` missing or unauthenticated | **STOP.** Fix the reported problem — write the summary/comments file, correct the arguments, or report the missing prerequisite — then retry. Never hand-write the `gh api` call instead.                                                                                                                                                                    |
| `SCRIPT_FAILURE`  | `1`  | The script broke                                                                        | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                                                                                                                                                                                                                       |

## Constraints

- **Never post a standalone top-level PR comment** (`gh pr comment`, `add_issue_comment`, etc.) for review findings. All feedback must go through the pull request review flow (steps 7–9) so it renders as a proper review with threaded, resolvable inline comments. **Sole exception:** a validated finding whose inline attachment was attempted and rejected (Step 8 fallback) is posted as a normal PR comment so it is not silently lost.
- **Never write location references like "in `file.py` (line 42)" or "around line 10" in the review body or in chat.** Every finding tied to a specific file/line must be an actual inline comment on that file/line via `add_comment_to_pending_review`, not prose pointing at a location. The Step 8 fallback comment is the sole exception — there, an explicit file/line reference in prose is required precisely because the inline placement failed. The Step 3 PR metadata gate is also review-body-only because title and description findings do not have file locations.
- Do not submit review text as plain chat/assistant messages.
- Keep each inline comment specific and actionable, scoped to the line(s) it annotates.
- Only findings that survived Step 6 validation may be posted — never publish an unvalidated candidate.
