---
type: feature
stage: implemented
description: One Claude-only GitHub Actions workflow, triggered only by pull request events, gives the repository automated PR review with a read-only review responder and a gate job that depends on the review job and blocks merge until an AI review exists.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: data/plans/20260816-ai-responder-workflows.md
- resource: data/plans/20260903-single-ai-review-workflow.md
- resource: docs/knowledge/data/archive/3.0.0/architecture/label-review-triggers.md
- resource: docs/knowledge/data/archive/1.0.0/architecture/ai-review-event-selection.md
- resource: docs/knowledge/data/archive/2.1.0/architecture/pull-request-only-responder.md
- resource: https://github.com/Dr-QP/Dr.QP/commit/24e1e3aa5426de0ba32f018eefdf2f587e96aba3
- resource: https://github.com/Dr-QP/Dr.QP/commit/b15bee1540306b698937ce2dee72b243e7747fec
---

# AI responder workflows

## Purpose

The repository had no automated PR review. One workflow, `ai-responder.yml`,
provides it: a `claude-respond` job reviews PRs, and an `ai-review-present` gate
job — in the same workflow, depending on the review job — blocks merge until an
AI review exists. The gate is satisfiable because the review responder produces
the review, and it stays pending for as long as a review is running in the same
run rather than polling for one.

## Behaviour

**Only pull request events start the workflow.** It triggers on `pull_request`,
`pull_request_review`, and `merge_group`; no comment, issue, or `@claude`
mention starts a run, and no job holds `contents: write`. The review responder
keeps `contents: read`. The decision is recorded in [Pull-request-only AI
responder](../archive/2.1.0/architecture/pull-request-only-responder.md).

**The responder reviews with the branch's own catalog.** The review job must run
in a container with the project toolchain to produce grounded output, and PR
reviews are driven by the `agentdev:pr-review` skill. Because a GitHub Actions
`container:` job runs no devcontainer lifecycle hooks, the shared responder
action runs the lifecycle scripts (`postCreate`, `postStart`, `postAttach`)
itself. That gives it the *branch's own* catalog — a PR that changes a skill is
reviewed by the skill as changed. Two lifecycle steps a review job never needs
(`pre-commit install --install-hooks`, Xpra) are skipped through
`AGENTDEV_SKIP_PRE_COMMIT` and `AGENTDEV_SKIP_XPRA` guards that default to
today's behavior, so the devcontainer is unchanged.

**The responder is Claude-only.** The Codex responder job, the `AI_RESPONDERS`
variable and its validation, and every ROS-specific element from upstream are
dropped. The fork gate and the write-access gate are the security spine: the
responder never checks out or executes code for a fork PR, and never acts for an
actor without write access.

**Review output stays on the formal review path.** The Claude responder uses a
custom prompt, but intentionally leaves `track_progress` unset. That action
input restores tag-mode tracking comments for custom prompts, but for this
review workflow it routes findings into a regular PR comment instead of a
submitted GitHub PR review.

**The responder posts as its own GitHub App.** The review responder and the
`trusted-bot-approval` job post with installation tokens of the
`plume-works-quill` App, minted per job with only the permissions that job needs
and, in the review job, after the lifecycle scripts have run. Their secrets live
in the `plume-works-review` environment; a job whose App secrets are missing
fails instead of falling back to `GITHUB_TOKEN`. The App opens no pull request
and pushes nothing. The decision is recorded in [Responder App
identity](../archive/3.0.0/architecture/responder-app-identity.md).

**The gate accepts one login.** `ai-review-present` accepts a review only from
`plume-works-quill[bot]`, in state `approved`, `changes_requested`, or
`commented`; reviews by `github-actions[bot]` or `claude[bot]` do not count. It
asserts the PR has been reviewed, not that each pushed commit has been, and
never requires the review to name the current head commit. Refreshing a review
is the author's call: adding the `request-ai-review` label runs a `pull_request`
review whose gate counts toward merge, and the review job removes the label, as
`plume-works-quill`, once the review finishes, so the label is on a pull request
only while a request waits for a finished review. A push that cancels a
requested review leaves the label, and the push's run reviews the new head. A
request on a draft, or from someone without write access, waits for a later run
that can review. Assigning someone, requesting a reviewer, and an
`@claude review` comment start nothing, and any other label runs only the gate,
outside the pull request's concurrency group. The design is recorded in [Label
review triggers](../archive/3.0.0/architecture/label-review-triggers.md).

**The review's verdict follows its findings.** The review submits `APPROVE` when
it has no validated finding or only non-blocking ones, and `REQUEST_CHANGES`
when any blocking finding remains, inline or not. The `main` ruleset requires
one approving review, so an approving review is what lets a reviewed pull
request merge; its inline comments still open threads that must be resolved
first. A clean re-review approves, which replaces the reviewer's own earlier
change request. The rule is recorded in [AI review event
selection](../archive/1.0.0/architecture/ai-review-event-selection.md).

**Trusted-bot pull requests are approved instead of reviewed.** A
`trusted-bot-approval` job approves a same-repository pull request whose author
is a `Bot` listed exactly in `TRUSTED_BOT_ACTORS`, with a body stating that the
AI review was skipped. It checks out nothing and approves once: a push to a pull
request it already approved adds no second approval. The same list drives the
`ai-review-present` waiver.

The approval holds only while every commit is the bot's own — authored by the
bot, committed by the bot or `web-flow`, with a verified signature — and every
push since the head branch's latest creation (that creation, pushes, force
pushes) came from the bot itself. When any commit or push fails that check, the
job approves nothing, dismisses its standing approval, and posts a notice naming
the failure, so the pull request needs a human approval. A run triggered by
`dependabot[bot]` cannot read the App secrets and is skipped with a notice; a
run a person triggers on a Dependabot pull request approves it when the check
passes. The job runs the pull request's own copy of the workflow, so the
approval is only as strong as the trust in the repository's writers: the checks
hold against a commit that leaves the workflow unchanged, not against a writer
who edits the job.

The gate's full contract lives in the [AI review
gate](../spec/ai-review-gate.md) spec. The boundary between the lifecycle
scripts and the workflow that supplies their devcontainer contract is recorded
in [CI agent plugin
availability](../archive/1.0.0/architecture/ci-agent-plugin-availability.md).

**Pull requests can block every review, not the gate.** While the
`block-ai-reviews` label is on, no review runs, an explicit `request-ai-review`
included; a request added meanwhile stays on the pull request, and removing
`block-ai-reviews` starts a run that reviews it. Preflight reads the labels when
it runs, so a label added after it read them does not apply to that run.
`ai-review-present` never reads the label: a skipped job satisfies a required
check, so a label the gate honoured would be a waiver of the mandatory review
for anyone who can label a pull request. A blocked PR without an accepted review
keeps a red gate, mergeable only by ruleset bypass.

**Every review sizes itself.** No marker, label, or prompt line requests an
effort tier; the review chooses its passes and models from the diff and keeps
the session's configured model.

## Edge cases

- **A draft pull request.** No review runs until the pull request is marked
  ready for review.
- **A push to a pull request that already has an accepted review.** The review
  job is skipped and `ai-review-present` passes on the existing review.
- **The review job fails or is cancelled.** `ai-review-present` in that run
  fails.
- **A fork pull request.** Preflight is skipped, so every responder job is
  skipped before any checkout, and `ai-review-present` fails for want of a
  review.
- **A pull request from a bot outside `TRUSTED_BOT_ACTORS`.** The
  `trusted-bot-approval` job runs, finds the author unlisted, and approves
  nothing; preflight skips every bot-authored pull request, so no review runs
  and `ai-review-present` stays red, so merging needs a user with ruleset
  bypass.
- **A person pushes to an approved trusted-bot pull request.** The next run
  dismisses the bot approval and posts a notice; closing and reopening the pull
  request runs the same check and does not restore it.

## Open questions

- Whether a run that published no review should fail on its own, rather than
  pass on an earlier review — open in [Fail a review run that published no
  review](../backlog/fail-review-run-without-review.md).

## References

- Plan: [Ship the reachable-scenario bar with part-by-part validation in
  pr-review](../plans/20261005-pr-review-scenario-validation.md)
