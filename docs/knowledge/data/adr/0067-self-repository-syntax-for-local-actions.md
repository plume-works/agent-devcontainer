---
type: adr
stage: accepted
description: Each uses reference to an action or reusable workflow of this repository starts with $/, and the zizmor self-repository audit enforces it.
---

# Local actions use the self-repository syntax

A `uses:` value in the self-repository syntax loads the action from the commit
that runs, so a step needs no earlier checkout. A `./` value needs a checkout,
and loads the files that the checkout or a later step left on disk. For this
reason, each reference to an action or reusable workflow of this repository
starts with `$/`.

## Considered Options

- Keep `./` and stop the zizmor audit. Rejected: each local action then needs an
  earlier checkout, and a full-SHA pin policy cannot apply.
- `owner/repo/path@sha` references. Rejected: the reference pins a commit that
  is not the one that runs, so an action and its caller cannot change together.

## Consequences

- The zizmor `self-repository` audit enforces the rule in workflow steps, in
  calls to reusable workflows, and in composite actions that call a local
  action.
- A step under `if: always()`, such as `log-debug-stats`, loads its action also
  after a checkout that failed or did not run.
- A step cannot load an action that an earlier step wrote to disk.
- GitHub records a `$/` reference as pinned. As a result, a full-SHA pin policy
  can apply to each action. This repository does not use such a policy now:
  `zizmor.yaml` turns off the `unpinned-uses` audit.
- The action content is the same as with `./`. The change does not repair a
  security problem: with each syntax, the responder jobs run a commit that the
  pull request controls.
- A job runs `actions/checkout` only when a step reads the working tree.
- The syntax works only on github.com, with runner v2.336.0 or later. A consumer
  on GitHub Enterprise Server, or with older self-hosted runners, must change
  these workflows before it can use them.
- Each linter of the workflows must accept `$/`. For this reason, actionlint
  comes from the `kjanat/actionlint` fork: `rhysd/actionlint` refuses `$/`.
