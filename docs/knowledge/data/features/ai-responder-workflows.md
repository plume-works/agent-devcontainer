---
type: feature
stage: implemented
description: Two matched GitHub Actions workflows give the repository automated PR review — a Claude-only responder that reviews using the branch's own agentdev catalog, and a required gate that blocks merge until an AI review exists.
generated:
  by: claude-code/opus-4-8
  at: 2026-08-31T00:00:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/workflows/require-ai-review.yml
- resource: data/plans/20260816-ai-responder-workflows.md
---

# AI responder workflows

## Purpose

The repository had no automated PR review. Two workflows imported from Dr-QP
together provide one: a responder that answers `@claude` mentions and reviews
PRs, and a gate that blocks merge until an AI review exists. They are a matched
pair — the gate is satisfiable because the responder produces the review.

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
PR, and never acts for an actor without write access.

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
