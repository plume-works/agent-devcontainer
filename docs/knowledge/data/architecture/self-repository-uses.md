---
type: architecture
description: Every same-repository action and reusable-workflow reference uses GitHub's `$/` self-repository syntax, so it loads from the running commit without depending on a checkout.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T16:45:12Z
sources:
- resource: .github/workflows
- resource: .github/actions
- resource: zizmor.yaml
- resource: https://github.blog/changelog/2026-07-30-reference-same-repository-actions-with-self-repository-syntax/
- resource: https://docs.zizmor.sh/audits/#self-repository
---

# Self-repository `uses:` syntax

## Decision

Every `uses:` that refers to an action or reusable workflow in this repository
starts with `$/`, never `./`. That covers workflow steps, reusable-workflow
calls, and composite actions that call other local actions. zizmor's
`self-repository` audit enforces it.

A job checks out the repository only when a step reads the working tree: tests,
builds, git history, or files a tool loads. A checkout whose only purpose is to
make a local action loadable is not added.

## Why

`$/` resolves to the repository at the commit that is running. `./` resolves
against the job's working directory when the step starts, so it needs an earlier
checkout, and it loads whatever that checkout or any later step left on disk.

- **No checkout dependency.** A step under `if: always()`, such as
  `log-debug-stats`, still loads after a failed or skipped checkout.
- **No runtime substitution.** A step cannot swap a local action for one it
  wrote to disk.
- **Pinning policy.** GitHub treats `$/` as pinned, so a full-SHA pinning policy
  can be enforced for every action.

The loaded content does not change for any reference here, so the move is not a
security fix: the responder jobs run a commit the pull request controls under
either syntax. `run-claude-responder` still copies
`py_packages/agentdev_runtime` from the PR checkout, and the CodeQL suppression
on that checkout still applies.

## Constraints

- **github.com only, runner v2.336.0 or newer.** `.github/actions/` is a
  template path, so a consumer on GitHub Enterprise Server, or with older
  self-hosted runners, cannot adopt these workflows unchanged.
- **The linters must accept `$/`.** actionlint is pinned from the
  [kjanat/actionlint](https://github.com/kjanat/actionlint) fork, which does;
  upstream `rhysd/actionlint` rejects it.

## Rejected alternatives

- **Keep `./` and disable the zizmor audit.** Leaves every local action
  dependent on a prior checkout, and blocks the pinning policy.
- **Reference local actions as `owner/repo/path@sha`.** Pins each reference to a
  commit other than the one running, so a change to an action and its caller
  cannot land together.
