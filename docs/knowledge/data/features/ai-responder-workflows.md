---
type: feature
stage: implemented
description: One Claude-only GitHub Actions workflow gives the repository automated PR review with a read-only review responder, a write-capable task responder, and a gate job that depends on the review job and blocks merge until an AI review exists.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T23:00:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: data/plans/20260816-ai-responder-workflows.md
- resource: data/plans/20260903-single-ai-review-workflow.md
- resource: data/architecture/pr-review-effort-tiers.md
- resource: data/architecture/assignee-review-trigger.md
- resource: data/architecture/ai-review-event-selection.md
- resource: https://github.com/Dr-QP/Dr.QP/commit/24e1e3aa5426de0ba32f018eefdf2f587e96aba3
- resource: https://github.com/Dr-QP/Dr.QP/commit/b15bee1540306b698937ce2dee72b243e7747fec
---

# AI responder workflows

## Purpose

The repository had no automated PR review. One workflow, `ai-responder.yml`,
provides it: a `claude-respond` job reviews PRs, a `claude-task` job answers
free-form `@claude` tasks, and an `ai-review-present` gate job — in the same
workflow, depending on the review job — blocks merge until an AI review exists.
The gate is satisfiable because the review responder produces the review, and it
stays pending for as long as a review is running in the same run rather than
polling for one.

## Behaviour

**Responders run with fixed content permissions.** The PR review responder keeps
`contents: read`; the free-form task responder has `contents: write`. Both jobs
call the same local composite action after checkout, so the agent setup remains
shared while GitHub receives a static permission map for each job.

**The responder reviews with the branch's own catalog.** The responder jobs must
run in a container with the project toolchain to produce grounded output, and PR
reviews are driven by the `agentdev:pr-review` skill. Because a GitHub Actions
`container:` job runs no devcontainer lifecycle hooks, the shared responder
action runs the lifecycle scripts (`postCreate`, `postStart`, `postAttach`)
itself. That gives it the *branch's own* catalog — a PR that changes a skill is
reviewed by the skill as changed — plus an indexed codebase-memory-mcp that
grounds the review. Two lifecycle steps a review job never needs
(`pre-commit install --install-hooks`, Xpra) are skipped through
`AGENTDEV_SKIP_PRE_COMMIT` and `AGENTDEV_SKIP_XPRA` guards that default to
today's behavior, so the devcontainer is unchanged.

**The responder is Claude-only.** The Codex responder job, the `AI_RESPONDERS`
variable and its validation, and every ROS-specific element from upstream are
dropped. The fork gate and the write-access gate are kept verbatim — they are
the security spine: the responder never checks out or executes code for a fork
PR, and never acts for an actor without write access. Both gates apply before a
comment is bridged into a dispatch and again in the dispatched run.

**Review output stays on the formal review path.** The Claude responder uses a
custom prompt, but intentionally leaves `track_progress` unset. That action
input restores tag-mode tracking comments for custom prompts, but for this
review workflow it routes findings into a regular PR comment instead of a
submitted GitHub PR review. A `@claude` mention on a pull request is bridged
into a `workflow_dispatch` on the head branch as a free-form task, so the task
runs the branch's own file and its checks attach to the head commit; the
dispatched run appends its Actions run link to the triggering comment before the
responder starts. A dispatch never reviews. Free-form task prompts instruct
Claude to post its response back to the issue or pull request thread, quoting
the original request.

**The gate accepts any Claude review, past or present.** `ai-review-present`
accepts a review from `claude[bot]` or `github-actions[bot]` in state
`approved`, `changes_requested`, or `commented`. It asserts the PR has been
reviewed, not that each pushed commit has been, and never requires the review to
name the current head commit. Refreshing a review is the author's call: removing
the pull request's author as assignee and adding them back runs a `pull_request`
review whose gate counts toward merge, as recorded in [Assignee-triggered AI
re-reviews](../architecture/assignee-review-trigger.md). An `@claude review`
comment is rejected with a reply pointing at that toggle.

**The review's verdict follows its findings.** The review submits `APPROVE` when
it has no validated finding or only non-blocking ones, and `REQUEST_CHANGES`
when any blocking finding remains, inline or not. The `main` ruleset requires
one approving review, so an approving review is what lets a reviewed pull
request merge; its inline comments still open threads that must be resolved
first. A clean re-review approves, which replaces the reviewer's own earlier
change request. The rule is recorded in [AI review event
selection](../architecture/ai-review-event-selection.md).

**Trusted-bot pull requests are approved instead of reviewed.** A
`trusted-bot-approval` job approves a same-repository pull request whose author
is a `Bot` listed exactly in `TRUSTED_BOT_ACTORS`, with a body stating that the
AI review was skipped. It checks out nothing and approves once: a push to a pull
request it already approved adds no second approval. The same list drives the
`ai-review-present` waiver.

The approval holds only while every commit is the bot's own — authored by the
bot, committed by the bot or `web-flow`, with a verified signature — and a push
comes from the bot itself. When any commit or push fails that check, the job
approves nothing, dismisses its standing approval, and posts a notice naming the
failure, so the pull request needs a human approval. A run triggered by
`dependabot[bot]` holds a read-only token and is skipped with a notice; a run a
person triggers on a Dependabot pull request approves it when the check passes.

The gate's full contract lives in the [AI review
gate](../spec/ai-review-gate.md) spec. The boundary between the lifecycle
scripts and the workflow that supplies their devcontainer contract is recorded
in [CI agent plugin
availability](../architecture/ci-agent-plugin-availability.md).

**Pull requests can opt out of the review run, not out of the gate.** A
`[ci:skip-ai-review]` marker alone on a line of the pull request body skips the
review responder — matched as a whole line, so a body that merely discusses the
marker stays prose. The marker outranks an assignment, so assigning a marked PR
runs the gate without a review. `ai-review-present` never reads the marker: a PR
body is author-controlled and a skipped job satisfies a required check, so a
marker the gate honored would be a self-service waiver of the mandatory review.
A marked PR without an accepted review keeps a red gate, mergeable only by
ruleset bypass. The marker does not disable free-form `@claude` tasks.

**A review can be asked to run cheaply.** A `[ci:review-effort=light]` or
`[ci:review-effort=full]` marker alone on a line of the pull request body is the
only way to request one of two effort tiers, matched as a whole line for the
same reason the skip marker is. Preflight resolves the tier and the responder
sizes the review session from it. A requested tier is obeyed exactly — the
review never escalates it, refuses, or fails over the diff it finds — and with
no request the review sizes itself and keeps the session's configured model. An
effort tier changes what a review costs, never whether one is required: both
tiers run the metadata check and the durable-knowledge pass, and neither waives
`ai-review-present`. The reasoning is recorded in [PR review effort
tiers](../architecture/pr-review-effort-tiers.md).

## Edge cases

- **A draft pull request.** No review runs until the pull request is marked
  ready for review.
- **A push to a pull request that already has an accepted review.** The review
  job is skipped and `ai-review-present` passes on the existing review.
- **The review job fails or is cancelled.** `ai-review-present` in that run
  fails.
- **A fork pull request.** Preflight records the fork, issues no dispatch, and
  skips every responder job before any checkout.
- **A head branch without `ai-responder.yml`.** The `@claude` bridge fails
  naming the branch, and no review runs.
- **A head branch whose workflow predates a dispatch input.** The dispatch
  carries only the inputs the request supplies, so an older branch still runs.

## Open questions

- Whether a run that published no review should fail on its own, rather than
  pass on an earlier review — open in [Fail a review run that published no
  review](../backlog/fail-review-run-without-review.md).

## References

- Plan: [Ship the reachable-scenario bar with part-by-part validation in
  pr-review](../plans/20261005-pr-review-scenario-validation.md)
