---
type: feature
stage: implemented
description: One Claude-only GitHub Actions workflow gives the repository automated PR review — a responder that reviews using the branch's own agentdev catalog, plus a gate job that depends on the review job and blocks merge until an AI review exists.
generated:
  by: claude-code/opus-4-8
  at: 2026-09-03T00:00:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: data/plans/20260816-ai-responder-workflows.md
- resource: data/plans/20260903-single-ai-review-workflow.md
- resource: https://github.com/Dr-QP/Dr.QP/commit/24e1e3aa5426de0ba32f018eefdf2f587e96aba3
- resource: https://github.com/Dr-QP/Dr.QP/commit/b15bee1540306b698937ce2dee72b243e7747fec
---

# AI responder workflows

## Purpose

The repository had no automated PR review. One workflow, `ai-responder.yml`,
provides it: a `claude-respond` job answers `@claude` mentions and reviews PRs,
and an `ai-review-present` gate job — in the same workflow, depending on the
review job — blocks merge until an AI review exists. The gate is satisfiable
because the responder produces the review, and it stays pending for as long as a
review is running in the same run rather than polling for one.

## Behaviour

**The responder reviews with the branch's own catalog.** The responder must run
in a container with the project toolchain to produce a grounded review, and the
review is driven by the `agentdev:pr-review` skill. Because a GitHub Actions
`container:` job runs no devcontainer lifecycle hooks, the responder job checks
out the branch and runs the lifecycle scripts (`postCreate`, `postStart`,
`postAttach`) itself. That gives it the *branch's own* catalog — a PR that
changes a skill is reviewed by the skill as changed — plus an indexed
codebase-memory-mcp that grounds the review. Two lifecycle steps a review job
never needs (`pre-commit install --install-hooks`, Xpra) are skipped through
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
into a `workflow_dispatch` on the head branch, so the review runs the branch's
own file and its checks attach to the head commit; the dispatched run appends
its Actions run link to the triggering comment before the responder starts.

**The gate accepts any AI review, past or present.** `ai-review-present` accepts
a review from `claude[bot]`/`github-actions[bot]`, a review from
`chatgpt-codex-connector[bot]`, or a `+1` reaction from that Codex bot, in state
`approved`, `changes_requested`, or `commented`. It asserts the PR has been
reviewed, not that each pushed commit has been, and never requires the review to
name the current head commit. Refreshing a review is the author's call via an
`@claude review` comment. Codex reviews arrive through Codex web, entirely
outside GitHub Actions.

The gate's full contract lives in the
[AI review gate](../spec/ai-review-gate.md) spec. The boundary between the
lifecycle scripts and the workflow that supplies their devcontainer contract is
recorded in
[CI agent plugin availability](../architecture/ci-agent-plugin-availability.md).
