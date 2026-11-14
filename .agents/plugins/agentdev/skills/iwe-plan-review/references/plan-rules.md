# Plan rules

The rules a plan document satisfies. This file is their only home: the
`iwe-planner` rulebook follows it while drafting a plan, and
`iwe-plan-reviewer` checks the draft against it from a fresh context.

Every rule here is decided yes or no from the plan and the current checkout. A
rule that needs a judgment of taste or scale stays in the `iwe-planner`
rulebook and is not reviewed.

The rules bind a plan's unticked tasks and its other sections. A ticked task
and its `- **Evidence:**` line are outside them.

## Tasks

- **One task is one outcome.** A task that could be described as half-done is
  split.
- **Externally closed work stands alone.** Work that a CI run, a deploy, a
  review, or a published artifact closes is its own task, because the session
  writing the code cannot close it.
- **One checkbox is one observation.** A checkbox joining independently
  observable events, such as a passing run and a failing run, is split into one
  checkbox per event. An event that may never occur on its own, such as a
  failure or cancellation path, names how it is provoked.
- **An observation task names who closes it.** Behaviour observable only after
  merge, only in a live service or a live agent session, or that no test
  running the behaviour can reach is a task carrying a
  `**Closed by:** <who or what event>` line. Ship waits for it.
- **Approved text is copied, never described.** A task that applies wording the
  user decided — text for a document, a snippet, a message — carries that
  wording verbatim in a fenced block. A task that says what the wording should
  accomplish has lost it: the session that applies the plan starts cold and
  writes something reasonable and different. The copy keeps each word: the
  formatters and `iwe normalize` can change only its line breaks and indent.

## Verification

- **Every `## Verification` step runs in the verifier's checkout.** Each step
  is a command the `iwe-verifier` agent can run in the checkout it works in —
  inside the Dev Container or container the agent already runs in — without
  starting a nested Dev Container, without CI, and without an effect beyond the
  working tree: no deploy, no push, no live service, no live agent session, no
  step a person performs. A check that needs any of these is a cited CI job or
  a task carrying a `**Closed by:**` line, never a `## Verification` step.
- **No step claims only that CI passes.** A plan carries no task and no
  `## Verification` step whose only claim is that CI passes: `pr-merge` gates
  every merge on CI.
- **A search for leftover text covers only the files the plan changes.**

## Acceptance

- **Each scenario is complete.** Each `### Scenario:` block in `## Acceptance`
  has a `**WHEN**` line, a `**THEN**` line, and a `**Test:**` line or a
  `**Checked at ship:**` line.

## ADRs

- **Each linked ADR is proposed.** Each ADR that `## ADRs` links exists, and
  its frontmatter has `stage: proposed`.

## Tests

- **A planned test runs the behaviour it covers.** It executes the code,
  script, hook, or command under test with inputs it controls, owns every
  resource it uses, and checks what results. These do not cover behaviour: a
  test that reads a repository file to check its text, keys, steps, or
  versions, or that two files agree; a test that checks another tool did its
  job; and a test that queries a live service or waits on CI.
- **No end-to-end test drives an agent session.** A plan adds no test that
  drives an agent session through the workflow skills against a live model.

## Anchors

- **Every code anchor resolves and carries no line number.** Each anchor under
  `## Key references` names its target in the current checkout.
