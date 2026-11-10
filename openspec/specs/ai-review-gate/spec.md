# AI review gate Specification

## Purpose

How the required AI review gate accepts a review and when the responder is allowed to act on a pull request.

## Requirements

### Requirement: PRs are blocked until an AI review exists

A pull request SHALL NOT be mergeable until Claude has reviewed it. The
`ai-review-present` check SHALL accept a review only from
`plume-works-quill[bot]`, in state `approved`, `changes_requested`, or
`commented`.

The check SHALL NOT require that the review name the pull request's current head
commit. It asserts that the pull request has been reviewed, not that each pushed
commit has been: reviewing every commit is prohibitively expensive, and neither
AI nor human reviewers work that way. Refreshing a review is the author's call,
requested by adding the `request-ai-review` label.

The check SHALL be a job of the same workflow as the review job, depending on
it, so that it is pending for as long as a review of the pull request is running
in that workflow run, and it SHALL evaluate without polling.

#### Scenario: a reviewed PR receives a further push

- **WHEN** an accepted AI review exists on the pull request and the author
  pushes a commit after it
- **THEN** the review job is skipped and `ai-review-present` passes on the
  existing review.

#### Scenario: an unreviewed PR receives a further push

- **WHEN** no accepted AI review exists on the pull request and the author
  pushes a commit
- **THEN** the review job runs and `ai-review-present` reports its outcome.

#### Scenario: Claude reviews a PR through the responder workflow

- **WHEN** the review job in a run posts a review on a pull request
- **THEN** `ai-review-present` in that run passes once the job completes, and is
  pending until then.

#### Scenario: the review job fails

- **WHEN** the review job in a run fails or is cancelled
- **THEN** `ai-review-present` in that run fails.

#### Scenario: no AI has reviewed

- **WHEN** the review job did not run in a run and no accepted review exists on
  the pull request
- **THEN** `ai-review-present` fails, blocking merge.

#### Scenario: only another identity has reviewed

- **WHEN** the pull request's only reviews are by `github-actions[bot]` or
  `claude[bot]`
- **THEN** `ai-review-present` treats it as unreviewed.

### Requirement: the responder acts as its own GitHub App

The review responder and the trusted-bot approval SHALL post with an
installation token of the `plume-works-quill` App, minted per job with only the
permissions that job needs and after any code from the pull request head has
run. A job whose App secrets are missing SHALL fail and SHALL NOT fall back to
`GITHUB_TOKEN`. The App's token SHALL NOT carry contents write access, and the
responder SHALL NOT open a pull request.

#### Scenario: the App secrets are missing

- **WHEN** a responder job runs and `QUILL_APP_CLIENT_ID` or
  `QUILL_APP_PRIVATE_KEY` is empty
- **THEN** the job fails naming the missing secret, and nothing is posted.

### Requirement: the responder only acts for authorized same-repository requests

The responder SHALL NOT check out or execute code for a pull request originating
from a fork, and SHALL NOT act for an actor without write access. The PR review
responder SHALL run with read-only repository contents access, and no responder
job SHALL hold write repository contents access.

#### Scenario: a fork PR triggers the responder

- **WHEN** the pull request head repository differs from the workflow repository
- **THEN** preflight is skipped, and every responder job is skipped before any
  checkout.

#### Scenario: a user without write access triggers the responder

- **WHEN** the actor of a `pull_request` event has a permission other than
  `admin`, `maintain`, or `write`
- **THEN** preflight fails and no responder job runs.

### Requirement: a review runs on first push and on explicit request

The review job SHALL run when a pull request is opened, marked ready for review,
or reopened, on a push to a pull request that has no accepted review, and when
the `request-ai-review` label is added. The label SHALL run a review whether or
not an accepted review exists. Every run in the pull request's concurrency group
SHALL take a `request-ai-review` it finds on the pull request: the run SHALL
review when the request is authorized and the pull request is not a draft, and
while the pull request carries no `block-ai-reviews`, and the review job SHALL
remove the label with the reviewer App's token once the review finishes, whether
it succeeded or failed, and SHALL NOT remove it when the review is cancelled. A
request whose own run was cancelled while pending is therefore taken by the run
that replaced it. A run that does not review SHALL leave the label for a later
run in that group, as SHALL a run started by another label. A cancelled review
therefore leaves the label until the next run in that group takes it, or until
`request-review.py` re-sends it. An assignment, a reviewer request, and a
reviewer request's removal SHALL NOT start a run. The review job SHALL NOT run
for a `pull_request` event on a draft pull request.

Removing `block-ai-reviews` SHALL start a run in the pull request's concurrency
group, which takes a waiting `request-ai-review`. Every other label event,
adding or removing any other label, SHALL NOT run a review and SHALL NOT share
the pull request's concurrency group, so it never replaces a queued review run.
Preflight does not run on a fork or bot-authored pull request, so a
`request-ai-review` label added there is not removed.

The workflow SHALL be triggered only by pull request, pull request review, and
merge group events: a comment, an issue, or a mention of `@claude` SHALL start
no run, and the workflow SHALL accept no `workflow_dispatch`.

The `ai-review-present` gate SHALL run for every pull request, pull request
review, and merge group event, every label event included.

#### Scenario: a draft is opened

- **WHEN** a pull request is opened as a draft
- **THEN** no review runs until the pull request is marked ready for review.

#### Scenario: a writer requests a review with the label

- **WHEN** a writer adds `request-ai-review` to a reviewed pull request
- **THEN** a `pull_request` run reviews the pull request, its review job then
  removes the label as `plume-works-quill`, and its `ai-review-present` reports
  that review.

#### Scenario: a push replaces a pending request

- **WHEN** `request-ai-review` is added while another run of the pull request is
  in progress, and a push queues before the request's run starts
- **THEN** the push's run reviews the pull request, its review job removing the
  label.

#### Scenario: a push lands during a requested review

- **WHEN** a push cancels a review that `request-ai-review` started
- **THEN** the label stays, and the push's run reviews the new head and removes
  it.

#### Scenario: a user without write access adds the label

- **WHEN** a user with triage but not write access adds `request-ai-review`
- **THEN** preflight fails, no review runs, and the label stays until a run a
  writer starts reviews the pull request.

#### Scenario: a writer assigns a pull request

- **WHEN** a writer assigns a reviewed pull request
- **THEN** no run of the workflow starts.

#### Scenario: a reviewer is requested

- **WHEN** a writer requests a reviewer on a pull request, or removes that
  request
- **THEN** no run of the workflow starts.

#### Scenario: an unrelated label is added

- **WHEN** a label other than `request-ai-review` is added while a requested
  review is queued
- **THEN** no review runs for the label, the queued review keeps its place, and
  `ai-review-present` in the label's run reports on the existing reviews.

#### Scenario: a writer comments `@claude`

- **WHEN** a writer opens a pull request comment, review comment, or issue with
  `@claude`
- **THEN** no run of the workflow starts.

### Requirement: a pull request can block every AI review

While a pull request carries the `block-ai-reviews` label, no review SHALL run
for it, whatever event starts the run, an explicit `request-ai-review` included.
A `request-ai-review` added while the block is on SHALL stay on the pull
request, and removing `block-ai-reviews` SHALL start a run that reviews it. The
label SHALL NOT waive the `ai-review-present` gate.

Preflight SHALL read the pull request's labels when it runs, not from the event
payload. A label added after a run's preflight read them does not apply to that
run.

The gate SHALL NOT read the label, because a job skipped by its own `if:`
satisfies a required status check, and a label the gate honoured would let
anyone who can label a pull request self-waive the mandatory review. A blocked
pull request with no accepted review keeps a red gate, and only a user with
ruleset bypass can merge it.

#### Scenario: a blocked pull request triggers the workflow

- **WHEN** a pull request carrying `block-ai-reviews` is opened or pushed to and
  no accepted review exists
- **THEN** no review responder runs, and `ai-review-present` runs and fails.

#### Scenario: a blocked pull request already has an accepted review

- **WHEN** a pull request carrying `block-ai-reviews` has an accepted review and
  receives a push
- **THEN** no review responder runs, and `ai-review-present` passes on the
  existing review.

#### Scenario: a writer requests a review on a blocked pull request

- **WHEN** a writer adds `request-ai-review` to a pull request carrying
  `block-ai-reviews`
- **THEN** no review runs, and `request-ai-review` stays on the pull request.

#### Scenario: the block is lifted with a request waiting

- **WHEN** `block-ai-reviews` is removed from a pull request carrying
  `request-ai-review`
- **THEN** a run reviews the pull request, and its review job then removes
  `request-ai-review`.

### Requirement: the AI review verdict follows its findings

The review responder SHALL submit `APPROVE` when no validated finding remains or
every validated finding is non-blocking, and SHALL submit `REQUEST_CHANGES` when
any blocking finding remains, whether or not it is attached inline. It SHALL NOT
choose `COMMENT`, except as the retry when GitHub rejects a verdict because the
reviewer owns the pull request.

#### Scenario: a re-review finds only non-blocking issues

- **WHEN** the AI reviewer earlier requested changes on a pull request and a
  re-review finds only non-blocking issues
- **THEN** the re-review is an `APPROVE` with inline comments, the reviewer's
  change request no longer blocks merge, and merge waits only for the inline
  threads to be resolved.

#### Scenario: a review finds an anchored blocking issue

- **WHEN** a review finds a blocking issue and attaches it inline
- **THEN** the review is `REQUEST_CHANGES`, and the pull request stays blocked
  until a later review from the same reviewer approves it.

### Requirement: trusted-bot pull requests are approved without an AI review

The AI responder workflow SHALL approve a same-repository pull request whose
author is a `Bot` listed in `TRUSTED_BOT_ACTORS`, with a review body stating
that the AI review was skipped, only when every commit on the pull request is
authored by that bot, committed by that bot or `web-flow`, and carries a
verified signature, and only when that bot made the head branch's latest
creation and every push and force push since. When any commit or update fails
that check it SHALL NOT approve, and SHALL dismiss its own standing approval. It
SHALL NOT check out the pull request, SHALL NOT approve a pull request that
already carries its approval, and SHALL skip a run triggered by
`dependabot[bot]`, which cannot read the App secrets in the `plume-works-review`
environment.

#### Scenario: Renovate opens a pull request

- **WHEN** `plume-works-renovate[bot]` opens a pull request on a branch of this
  repository
- **THEN** the workflow approves it once, no AI review runs, and
  `ai-review-present` passes on the trusted-bot waiver.

#### Scenario: a bot outside the list opens a pull request

- **WHEN** a bot not listed in `TRUSTED_BOT_ACTORS` opens a pull request
- **THEN** no approval and no AI review is posted, and the pull request stays
  blocked unless merged by ruleset bypass.

#### Scenario: a person pushes to a trusted-bot pull request

- **WHEN** an account other than the author bot pushes a commit that leaves the
  workflow unchanged to a trusted-bot pull request the workflow already approved
- **THEN** the workflow dismisses its approval, approves nothing, and the pull
  request needs a human approval to merge, even after it is closed and reopened.

#### Scenario: a reused branch name starts clean

- **WHEN** a trusted bot recreates a branch whose earlier life included a
  person's push, and opens a new pull request from it
- **THEN** only the pushes since the branch's latest creation are checked, and
  the workflow approves the new pull request.

### Requirement: a correctness finding states a reachable scenario

Every correctness candidate in a `pr-review` review SHALL state a **Trigger** —
an input or state the code can receive at the head commit — a **Path** — the
anchor chain from the trigger to the fault — and an **Outcome** — the concrete
wrong result. A candidate with an empty part SHALL be discarded before
validation. The validator SHALL receive a scenario candidate's three parts in
place of its claim, judge them in trigger, path, outcome order, and return
`CONFIRM` only when every part holds as written, or
`DROP: trigger|path|outcome — <reason>` naming the first part that does not.
A comment or pull request description presenting behavior as deliberate SHALL
be weighed as evidence, not taken as refuting a reachable wrong outcome.

#### Scenario: a candidate has no Outcome

- **WHEN** a correctness pass returns a candidate with a Trigger and a Path but
  no Outcome
- **THEN** the candidate is discarded and never reaches validation

#### Scenario: a scenario's Path is false as written

- **WHEN** the validator finds that a candidate's Trigger can occur but its Path
  does not lead to the fault
- **THEN** it returns `DROP: path — <reason>`, even when another path would reach
  the same fault

#### Scenario: the description calls a broken guarantee deliberate

- **WHEN** the pull request description presents a behavior as intended and the
  code reaches a wrong outcome through it
- **THEN** the description does not by itself refute the finding

### Requirement: every review sizes itself within a fixed model matrix

Nothing SHALL request a review effort tier: no pull request body marker, label,
or prompt line selects one, and `run-claude-responder` SHALL take no model
input. `pr-review` SHALL size each review at `light` or `full` from the diff it
holds. At `full` every slot SHALL run on the `large` model except compliance and
validation; at `light` every slot SHALL run on the `light` model. Both tiers
SHALL run the metadata gate and the durable-knowledge pass. Validation SHALL run
on the `light` model at every effort, one dispatch per candidate, except that
`light` effort SHALL validate every candidate in one batched dispatch.

#### Scenario: a full review validates its findings

- **WHEN** a review runs at `full` effort and three candidates survive
  deduplication
- **THEN** each is validated in its own dispatch on the `light` model

#### Scenario: a light review validates its findings

- **WHEN** a review runs at `light` effort and three candidates survive
  deduplication
- **THEN** all three are validated in one dispatch on the `light` model, and the
  metadata gate and durable-knowledge pass have run

## Rationale

### The verdict follows severity

The maintainer settled the verdict rule against the `main` ruleset, which
requires one approving review, keeps stale reviews on push, and requires every
review thread to be resolved. The AI reviewer's `APPROVE` is what satisfies the
required approval, and only that reviewer's own `APPROVE` replaces its earlier
`CHANGES_REQUESTED`; a `COMMENT` does neither. Inline comments on an approving
review still open threads that hold the merge, so approving with non-blocking
findings loses no enforcement, while an approval beside an unaddressed blocking
finding would read as sign-off on it. GitHub rejects both verdict events when
the reviewer identity is the pull request's author, which is why `COMMENT`
survives only as that retry.

Rejected:

- **`COMMENT` when every blocking finding is anchored inline.** It assumed merge
  was gated by thread resolution alone; under the one-approval ruleset it
  neither satisfies the approval nor lifts the reviewer's change request.
- **`APPROVE` with anchored blocking findings, relying on thread resolution.**
  An approval beside a blocking finding reads as sign-off on it.
- **Never `REQUEST_CHANGES`.** The rule inherited from the Dr.QP workspace,
  where no approving review was required; here a blocking finding would never
  block and no review would satisfy the approval.

### The responder is its own GitHub App

The maintainer decided that the review responder and the trusted-bot approval
both post as `plume-works-quill[bot]`, the only login the gate accepts, written
as a literal with no variable to repoint it. Its approval is then one no other
workflow can give, and the organization setting "Allow GitHub Actions to create
and approve pull requests" can stay off. The App's installation holds contents
write, because the `main` ruleset counts an approval only from a reviewer with
write access; no job mints a token with it, so only a holder of the App's
private key could push. Reviews by `github-actions[bot]` and `claude[bot]` are
ignored with no transition period. The token is minted after the Dev Container
lifecycle scripts, which keeps it out of their environment but not out of a
process they leave running; the fork and write-access gates bound that exposure
to writers.

Rejected:

- **Post with `GITHUB_TOKEN` and enable the organization approval setting.**
  Any workflow in the organization could then approve as the reviewer and
  satisfy the required review.
- **The App reviews while `GITHUB_TOKEN` approves trusted bots.** The
  organization setting has to stay on, so the same gap stays open.
- **The Claude GitHub App through OIDC (`claude[bot]`).** An identity this
  organization does not control, shared with every other installation.
- **Fall back to `GITHUB_TOKEN` when the App secrets are missing.** A silent
  fallback brings back the shared identity the gate no longer accepts.

### Trusted-bot approval covers only the bot's own pushes

Commit metadata cannot prove who pushed: a commit another account creates
through the API can name the bot as author and still verify. The job therefore
also reads the head branch's push activity back to its latest creation, so a
reopened pull request or a cancelled run cannot restore an approval after a
person's push, and a reused branch name such as Renovate's `renovate/<dep>`
starts clean. The `main` ruleset keeps stale approvals on push, which is why a
failed check dismisses the job's standing approval. The job runs the pull
request's own copy of the workflow, so the approval is only as strong as the
trust in the repository's writers; guarding it against a writer who edits the
job is out of scope.

Rejected:

- **Check only the actor of a `synchronize` run.** A person could push a commit
  naming the bot as author, then close and reopen the pull request.
- **Skip Dependabot pull requests by author.** The commit check already keeps a
  person's change out; an author skip would only withhold approval from pull
  requests holding Dependabot's commits alone.

### The workflow runs only on pull request events

The maintainer removed the free-form `@claude <prompt>` task responder and the
`@claude review` reply. Every run then executes the pull request's own copy of
the workflow, no run is privileged by a default-branch trigger, preflight
authorizes the `github.actor` of the event with no identity forwarded between
runs, and no responder job pushes. A comment-started run was also never counted:
the `main` ruleset, merge state, and the status rollup draw only on check suites
created by the pull request's own events, so a `workflow_dispatch` run's gate
did not count toward merge even though its checks landed on the head commit.

Rejected:

- **Bridge an `@claude review` comment to a `workflow_dispatch` on the head
  branch.** The dispatched run's actor is `github-actions[bot]`, so it needs a
  forwarded requester input and `allowed_bots` on `claude-code-action`, and its
  gate does not count toward merge.
- **Keep the `@claude review` reply only to redirect requests.** It keeps a
  privileged comment trigger and a job on every `@claude` comment.
- **Keep the task responder, review-only by default.** The task path is what
  needs `contents: write`, the bridge, and requester forwarding.

### Reviews are requested with a label

The maintainer wanted an easy, trusted, explicit way to request a re-review,
and decided on a `request-ai-review` label held until a review of it finishes,
and a `block-ai-reviews` label that holds every review, a waiting request
included. A label fires `pull_request`/`labeled`, so its run is counted by the
ruleset and its checks land on the head commit. `block-ai-reviews` saves the
runs that would fail while Claude is unavailable without letting a pull request
merge, because the gate still requires an accepted review.

Rejected:

- **Request a review by assigning the pull request.** It borrows a field that
  means ownership, needs two actions per re-request, and a queued `assigned`
  run could be dropped by a later event in the same concurrency group.
- **A comment trigger.** A comment-started run is not a `pull_request` run, so
  its gate does not count toward merge.
- **Re-run the gate by re-requesting a reviewer.** It needs a second
  collaborator and leaves reviewer churn on the pull request.
- **A persistent state label removed after the review posts.** A failed review
  leaves it on, to be removed by hand before the next request.
- **A skip label that an explicit request overrides.** A label named for
  skipping reviews that still lets a request through reads as broken.
- **A repository-wide review pause.** A per-pull-request label covers an outage,
  and a pause would still need bypass merges unless it waived the gate.
- **A `[ci:skip-ai-review]` or `[ci:review-effort=…]` body marker.** Replaced by
  the labels and by self-sizing.

### Every review sizes itself

The orchestrator holds the diff, so it sizes the review, the way it already
fast-approves a mechanical diff; a configured default tier would have to be
right for every diff in advance. Per-dispatch model arguments are what put the
matrix in force, because they outrank a definition's frontmatter, the
`CLAUDE_CODE_SUBAGENT_MODEL` variable, and the session model. Compliance stays
on the `light` model because quoting a rule and checking a diff against it is
instruction-following, not reasoning. Validation stays on the `light` model
because its bar lives in the prompt: a stronger reasoner asked to confirm only
at high confidence argues more persuasively for dropping rather than judging
more accurately, and validation is the only slot whose dispatch count scales
with the findings. Batching is the light tier's trade alone, because
per-candidate isolation stops a weak finding reading as strong beside strong
ones.

Rejected:

- **Requested effort tiers obeyed absolutely.** Replaced by self-sizing when
  the labels replaced the body markers.
- **Escalate a `light` review to `full` on a large documentation diff, or fail
  it above a documentation-line threshold.** It overrules the stated tier, and a
  threshold is a number nobody can source.
- **Drop the metadata gate and durable-knowledge pass at light effort.** It
  makes `light` weaker rather than cheaper.
- **Batch full-effort validation.** It gives up per-candidate isolation.
- **A model alias rather than a full identifier.** `claude_args` resolves full
  identifiers.

### Correctness findings state a reachable scenario

The maintainer shipped the reachable-scenario bar on full-effort replays of
pull requests #199 and #203, which found every known bug in every run with no
correctness finding judged noise. The `light` validator judges whether a fault
is real rather than whether each stated part holds, so a `DROP`'s named part is
diagnostic, and a confirmed Outcome may overstate the harm. Validating
correctness candidates on the `large` model stays a someday idea.

Rejected:

- **Carry the claim alongside the scenario parts.** Given both, the validator
  re-derives the claim and confirms candidates whose stated part is false.
- **Change the validator but keep the diff-only bar.** The part-by-part
  validator acts only on the scenario candidates that bar produces.
- **Hold the change until the negative controls pass.** The light validator does
  not test each part as written under either prompt form.
