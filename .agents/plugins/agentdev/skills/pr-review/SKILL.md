---
name: pr-review
description: 'Perform a thorough automated code review of a GitHub pull request, publishing feedback as a single GitHub pull request review with inline comments (a standalone comment only as fallback when inline posting fails). Use when asked to review a pull request, or when a PR is opened/reopened and an automated review is required. Keywords: PR review, code review, pull request review, automated review.'
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
---

# Review PR

Use this skill to review a pull request's diff and publish feedback as a GitHub **pull request review** — not a plain issue/PR comment. The workflow is agent-agnostic: Claude Code, OpenCode, and other assistants should follow the same review policy while adapting tool names to the environment they are running in.

## When to Use This Skill

- A pull request was just opened or reopened and needs an automated review
- Someone explicitly asks for a review of a pull request (for example, "review this PR")

## Prerequisites

- `gh` must be installed and authenticated
- REPO (`owner/name`) and PR NUMBER must be known — read them from the workflow context or ask the user if not provided

## Review Focus

Two independent concerns feed two different pass types (see Steps below) so they can be reviewed without one blind spot masking the other.

**Compliance focus** (repo-convention adherence) — runs on the `light` model at both tiers, per the effort matrix:

- Python and JavaScript/TypeScript style and idioms
- Any rule in the Coding Conventions section of the repository `AGENTS.md`, any skill applicable to the changed files (see Step 2), and any repo `CLAUDE.md`/`AGENTS.md` file that shares a path with the changed file or its parents
- IGNORE import ordering, that is handled by `ruff` in CI
- Only flag a violation if you can quote the exact rule text being broken

**Correctness focus** (bug-hunting) — runs on the model the effort matrix gives it:

- Start from the diff, then read at the head commit the code the changed lines call, the code that calls them, and the code that runs beside them in the same lifecycle or workflow (sibling steps, hooks, jobs, and scripts run in the same sequence) — a bug may live in how the changed lines meet that code
- Potential bugs, incorrect logic, and security implications introduced by the changed code
- Test coverage and quality

A correctness candidate that claims a wrong outcome states its scenario in three parts: **Trigger** — an input or state the code can actually receive at the head commit; **Path** — the anchor chain (`path@symbol` → `path@symbol`, never line numbers) from the trigger to the fault; **Outcome** — the concrete wrong result, failure, or security exposure. A candidate missing any part is speculation — do not flag it.

**Documentation focus** (durable-knowledge adherence) — applies to docs under `data/`, `README.md`, `AGENTS.md`, skill and agent rulebooks (`SKILL.md`, `*.agent.md`), and docstrings:

- Run `/agentdev:durable-knowledge-audit` in diff mode over the changed docs/skills files.
- Map each of its findings to an inline review comment placed on the diff line that holds the finding's quoted text, and the verdict plus its replacement/destination becomes the comment body.
- **High-signal bar:** flag a finding only when you can quote the added line and name the specific rule it breaks — the same anti-nitpick threshold the Compliance focus uses. Drop any finding you cannot tie to a quoted line and a named rule.

**PR metadata focus** (title/description relevance) — use `/agentdev:pr-gen-description` before the in-depth passes:

- Compare the current PR title and description from Step 1 against the actual PR diff, base branch, and repository pull request template.
- The title must describe the main change, and the description must cover the material changes, testing actually performed, breaking changes, migration or rollout requirements, and related issues or docs when they apply.
- Flag only material stale, misleading, missing, or irrelevant title/description content. Do not block on wording polish or optional detail.

## Effort Tiers

The review runs at one of two effort tiers, `light` or `full`. Nothing requests a tier: no PR body marker, label, or prompt line selects one.

**Size the review yourself** from the diff you already hold: how many passes to run, which model each slot gets, and how deep the durable-knowledge pass goes. This is the same judgment Step 1 makes when it fast-approves a mechanical diff. The validation slot is the one exception — Step 6 fixes it at every effort level, self-sized included.

Model sizes, unversioned so each name resolves to that model's latest release:

| Size    | Claude            |
| ------- | ----------------- |
| `large` | `claude-opus-5`   |
| `light` | `claude-sonnet-5` |

Which size each slot gets, and how many of it run:

| Slot                    | light effort     | full effort          |
| ----------------------- | ---------------- | -------------------- |
| orchestrator            | light            | large                |
| metadata gate           | light            | large                |
| compliance              | 1x light         | 2x light             |
| correctness             | 1x light         | 2x large             |
| durable-knowledge-audit | light            | large                |
| validation              | one batch, light | per-candidate, light |

Before Step 4, state the tier you chose in one line of its own, `Effort tier: <light|full|self-sized> — <reason>`, where the reason names the diff facts that decided it.

The rule in one line: at full effort everything is `large` except compliance and validation, which stay `light` at both tiers; at light effort everything is `light`. The orchestrator runs on the session's configured model, not one from this skill — the rest are yours to pass.

Both tiers run the same checks. The Step 3 metadata gate and the Step 4 durable-knowledge pass run at `light` exactly as they do at `full`: the light tier is a cheaper review, not a weaker one. The Step 1 mechanical fast-approve and its docs-only exclusion are unaffected by the tier.

## Steps

1. **Gate.** Run `gh pr view <PR_NUMBER> --json state,isDraft,baseRefOid,headRefOid,title,body` as a call of its own whose output is neither piped nor filtered. If the PR is a draft or already
   closed/merged, stop. For a version-only or generated-file-only diff, do not
   launch the review passes. Instead, confirm the changed file list with
   `gh pr diff <PR_NUMBER> --name-only`, then publish a clean `APPROVE` review
   with a short summary as [references/reporting.md](references/reporting.md)
   describes. This preserves the required AI-review gate for a
   mechanical PR without spending a full review cycle. A docs-only diff is not
   fast-approved: it still runs the durable-knowledge pass (Step 4).
2. **Gather context.** Fetch the diff (`gh pr diff <PR_NUMBER>`) and reuse the PR title and description from Step 1. From the changed-file list, determine which convention sources apply: the Coding Conventions section of `AGENTS.md` always applies; add `/agentdev:create-agent` for `*.agent.md` changes, and `/agentdev:create-skill` for `SKILL.md` changes.
3. **PR metadata gate.** Use `/agentdev:pr-gen-description` as a relevance and completeness check against the current PR title, PR description, diff, base branch, and repository pull request template. When reviewing a PR that is not checked out locally, apply that skill's analysis and validation criteria to the fetched PR diff instead of mutating the branch or PR. List every claim the title and description make — what the change does, how it behaves, what was tested and with what result — and check each one against the diff and the head commit. If a claim is contradicted, or the current title or description is materially stale, misleading, irrelevant, or incomplete for the actual change set, publish the metadata finding as [references/reporting.md](references/reporting.md) describes and **stop before launching the in-depth review passes**. Do not update the title or description from this skill. If the metadata is acceptable, continue.
4. **Run the independent initial-review passes the effort matrix names, in parallel when the environment supports it** — each pass sees the diff, the PR title, the PR description, and its own focus list, and the correctness passes may also read the head commit as their focus list allows; none sees another pass's output. Each pass returns a list of issues, where each issue has a description, the reason it was flagged (for example, "AGENTS.md adherence", "bug", or "security"), and whether it blocks under the rulebook's `## What blocks`; an issue that claims a wrong outcome also carries its scenario's Trigger, Path, and Outcome. Each pass ends its return with a `Dropped:` section listing every candidate it considered and rejected itself, one line each with the reason, or `Dropped: none`:
   - **compliance pass** — audit the diff against the Compliance focus list and the convention sources found in Step 2. 2x at full effort, 1x at light.
   - **correctness pass** — audit the diff against the Correctness focus list. 2x at full effort, one pass scanning for obvious bugs and the other for security/logic issues introduced by the changed code; 1x at light, covering both.
   - 1x **durable-knowledge pass**, only when the diff contains docs/skills files — audit the changed docs/skills files against the Documentation focus list. It runs at both tiers.
   - **The lens follows the file.** The correctness passes scan code files, the durable-knowledge pass scans docs/skills files, and each ignores files outside its lens. On a mixed docs+code diff both lenses run against their own file subsets in the same review; on a code-only diff the durable-knowledge pass does not run, leaving four passes at full effort and two at light.
   - **Every pass prompt carries the full text of [rules/review.md](../../rules/review.md)** and the "Never execute code" constraint (see Constraints) verbatim: a pass does not inherit this skill's text.
   - **Pass each dispatch the model its slot gets in the effort matrix.** A dispatch that carries no model argument runs at the session's own model, whatever the matrix says — the argument is what puts the matrix in force.
   - Claude Code: issue every pass's `Agent` call in a single message with `run_in_background: false` (`subagent_type: general-purpose`), each with the `model` for its slot. Foreground calls issued together run in parallel, and the message returns only once every one has finished. If the `Agent` tool offers no foreground option, run the passes sequentially in this session, restarting the review lens from the diff for each pass. **Never dispatch a pass in the background:** this skill's main caller is the responder action, a headless `claude -p` run that ends the moment you stop emitting, so a background pass is lost with the session.
   - **Collect every pass before Step 5 — see "Waiting on parallel passes" below.** On Claude Code the foreground dispatch returns with every result. Do not proceed to Step 5 with a pass still outstanding. **The turn in which you dispatch these subagents must not be your last turn** — a dispatch-then-stop turn abandons the review with nothing published (see below).
5. **Merge and deduplicate.** Collect the candidate findings from every pass. Discard every candidate that claims a wrong outcome with an empty Trigger, Path, or Outcome; it never reaches validation. Collapse candidates that name the same file/line and describe the same underlying issue into one, retaining one of them whole — its description and, for a correctness candidate, its scenario — and keeping it **blocking** if either collapsed candidate blocks. Then state, in a message of its own starting `Merge:`, every discarded candidate with the part it lacked and every collapsed group with the candidate retained, or `Merge: nothing discarded or collapsed`.
6. **Validate the surviving candidates, on the `light` model at every effort level.** A validator must confirm with high confidence that a candidate is a real, worth-flagging issue; drop any candidate it cannot confirm. Validation confirms or drops a finding; it never changes whether the finding blocks.
   - **One validator prompt, the same at every effort level.** It carries the candidate's file and line, the added text quoted, the Trigger, Path, and Outcome of a candidate that carries a scenario in place of its claim, the claim made against any other candidate, the full text of [rules/review.md](../../rules/review.md), the full text of any other rule that claim invokes, where to read the diff and the PR title and description, that the working tree is already at the head commit so files can be read for ground truth, and the "Never execute code" constraint verbatim. It never names which pass raised a candidate. Each verdict in the validator's return starts its own line with `CONFIRM` or `DROP`.
   - **Make the validator re-derive what the candidate asserts** from the files rather than trust it. The bar follows the candidate's shape:
     - **A candidate carrying a scenario is judged part by part, as written,** against the head commit, in order: the Trigger can actually occur, the Path leads from it to the fault, and the Outcome follows from that path. The validator stops at the first part that does not hold and returns `DROP: trigger|path|outcome — <reason>` naming it; a part false as written is a drop even when another scenario would reach the same fault. The verdict is `CONFIRM` only when every part holds as written.
     - **Any other candidate** is dropped when ambiguous, trivial, or not clearly a violation; ask for `CONFIRM` or `DROP` with a one-sentence justification.
   - **Never argue the verdict in the prompt.** Supplying reasons a candidate might not hold, or casting the validator as an adversary out to defeat it, settles the verdict before a file is read. Strictness belongs in the bar the validator applies, never in a case the orchestrator makes for one side.
   - **Full effort: one dispatch per candidate**, in parallel when supported, each seeing only that single candidate. Per-candidate isolation is what stops a weak finding reading as strong beside three strong ones, so it is not traded away at this tier.
   - **Light effort: one batched dispatch** carrying every surviving candidate at once and returning a confirm-or-drop verdict for each. This gives up the isolation the full tier keeps, in exchange for one call instead of one per finding.
   - **Batching is the light tier's trade and nothing else's.** A self-sized review validates one dispatch per candidate, like full effort — sizing the review yourself does not extend to giving up isolation.
   - Use the same runner-specific parallel-vs-sequential approach as Step 4 — foreground `Agent` calls on Claude Code — and the same blocking policy in "Waiting on parallel passes" below.
7. **Publish** the validated findings as [references/reporting.md](references/reporting.md) describes.

### Waiting on Parallel Passes

Every parallel pass from Steps 4 and 6 must complete or be cancelled before
Steps 5–7. Never end a turn with an outstanding task, substitute a text status
update, or poll with a no-op shell command. If the runner can neither run passes
in the foreground nor block on them, run the passes sequentially.

**Self-check gate:** before emitting text or ending a turn, make a blocking call
for every background task ID that has not returned.

Text announcing that you are waiting is not waiting. If the next thing you were
about to produce is a sentence about outstanding passes, replace it with the
blocking call itself — under the responder action the run ends with your turn,
so every pass that has not reported back is a finding that never reaches the
review.

Concretely:

- **Claude Code: dispatch in the foreground.** Issue each batch's `Agent` calls in a single message with `run_in_background: false`; the message returns with every pass's result, so nothing is left to wait on. This path has no per-pass ceiling and never drops a hung pass: the responder job's `timeout-minutes` bounds the whole review, and a review that exceeds it fails the job.

## Constraints

- **Never execute code** — no test run, build, linter, dependency install or sync, `docker`, or `devcontainer` command, in this session or in any pass or validator it dispatches. CI runs those; a review reads the diff and the head commit. A pass or validator never reads CI results either: it states the Trigger, Path, and Outcome from the code alone. This skill's own `agent-code/` scripts are the only programs it runs.
- **CI results: one look, from this session, never a wait.** Only this session, while publishing the review in Step 7, may read CI results — one `gh pr checks`, plus `gh run view --log-failed` for a check that has already failed — to cite a finished check beside a finding. A check still running is left out. Never wait for one: no `--watch`, `gh run watch`, `sleep`, or polling loop.
