---
type: someday
description: Move every same-repository `uses:` from workspace-relative `./` to GitHub's `$/` self-repository syntax once actionlint accepts it, then re-enable zizmor's self-repository audit.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T16:12:27Z
sources:
- resource: zizmor.yaml
- resource: .github/workflows/ai-responder.yml
- resource: https://github.blog/changelog/2026-07-30-reference-same-repository-actions-with-self-repository-syntax/
- resource: https://docs.zizmor.sh/audits/#self-repository
- resource: https://github.com/rhysd/actionlint/issues/711
---

# Self-repository `uses:` syntax

GitHub's `$/` prefix loads a same-repository action or reusable workflow from
the commit that is running, without a checkout. `./` loads whatever the job's
working directory holds when the step starts. zizmor's `self-repository` audit
flags every `./` reference; it is disabled in `zizmor.yaml` until this moves.

## Decision

Adopt `$/` for every same-repository `uses:`, and only once actionlint accepts
it. actionlint rejects `$/` in both step and reusable-workflow `uses:`, and it
is a required pre-commit hook, so switching first would fail every workflow
file.

## What moving changes

- **Same content, no checkout dependency.** Every current `./` use already loads
  the commit the event runs: preflight and the review gate check out the event's
  own ref before their local actions, the responder jobs run a PR-controlled
  commit under either syntax, and `./` reusable-workflow calls already resolve
  from the running commit. The change is not a security fix here.
- **Checkouts that exist only to load actions go away.** The sparse
  `Checkout composite actions` steps in `ai-responder.yml`'s preflight and
  `ai-review-present` jobs, and the ordering constraint that `if: always()`
  steps such as `log-debug-stats` need a successful earlier checkout.
- **Enables the SHA-pinning policy.** GitHub treats `$/` as pinned, so the
  repository could enforce full-SHA pinning for all actions.
- **`run-claude-responder` reads the checkout too.** It copies
  `py_packages/agentdev_runtime` from `$GITHUB_WORKSPACE`, which is the PR head,
  while `$/` loads the action from the running commit. The CodeQL suppression on
  the responder checkout still applies.
- **Template consumers inherit the limits.** `$/` works only on github.com and
  needs runner v2.336.0 or newer; `.github/actions/` is a template path, so a
  consumer on GitHub Enterprise Server could not adopt it.

## Scope

- Every `uses: ./` under `.github/workflows/` and `.github/actions/`, including
  nested composite-action calls.
- `scripts/tests/test_paths_filter_last_pass.py` and
  `scripts/tests/test_agent_runtime_ci.py` match the literal `./.github/...`
  strings.
- Remove the `self-repository` entry from `zizmor.yaml`.
- Drop the action-only sparse checkouts.

## Promotion criteria

Promote to a task when an actionlint release, or a maintained fork adopted in
its place, accepts `$/` uses (rhysd/actionlint#711), and the pinned tool in
`dev_tools_pinned_tools` reaches that version.
