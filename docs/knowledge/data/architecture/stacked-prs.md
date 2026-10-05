---
type: architecture
description: How a GitHub native stacked pull request is detected, merged, and re-checked after a lower layer lands in this repository, and why stack branches alone may be force-pushed.
generated:
  by: claude-code/opus-5-5
  at: 2026-10-05T10:00:00Z
sources:
- resource: https://docs.github.com/en/pull-requests/how-tos/stacked-pull-requests
- resource: https://github.com/github/gh-stack/releases/tag/v0.2.0
- resource: https://github.com/plume-works/agent-devcontainer/pull/256
- resource: https://github.com/plume-works/agent-devcontainer/pull/257
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
---

# Stacked pull requests

Facts below hold for `gh-stack` v0.2.0 against the `main` ruleset of this
repository (squash-only, `required_linear_history`, four required checks,
review-thread resolution).

## Detecting a stacked PR

The REST pull request object (`GET /repos/{owner}/{repo}/pulls/{n}`) carries a
`stack` object for a PR in a stack, and no `stack` key at all otherwise:

``` json
{"id": 1745769, "number": 259, "position": 2, "size": 3,
 "base": {"ref": "main", "sha": "<trunk sha>"}}
```

`position` is 1-based from the bottom. `gh pr view --json` has no `stack` field,
so skills read it through `gh api`. `gh stack view --json` gives the local view
of a checked-out stack: per branch `name`, `head`, `base`, `isMerged`,
`isQueued`, `needsRebase`, and `pr.number`/`pr.state`.

A merged layer stays in the stack: `position` and `size` of the remaining layers
do not change when a lower layer merges, and unstacking leaves merged members
stacked. "Lowest unmerged layer" is therefore computed from each member's state,
never from `position == 1`.

## Merging

`gh pr merge` cannot merge a stacked PR. GraphQL `mergePullRequest` refuses it
with "This pull request is part of a stack and must be merged using the
asynchronous merge REST API".

`gh stack merge <pr> --yes --squash` merges every layer up to and including
`<pr>` in one all-or-nothing operation. It passes the `main` ruleset like any
squash merge: each merged layer still needs its required checks green and no
blocking review state. Bypassing merge requirements is not supported for stacks.

## After a lower layer merges

GitHub retargets the next layer to the trunk and rebases every remaining layer
onto the new trunk tip, giving each a new head SHA. That rewrite is a
`pull_request` `synchronize` event, so `primary-checks.yml` and every other PR
workflow re-run on each remaining layer.

The AI responder does not review again. It reviews only on first push or on
request ([AI review gate](../spec/ai-review-gate.md)), and `ai-review-present`
accepts the review of the pre-rebase head. A sticky `CHANGES_REQUESTED` on a
layer survives the rebase and keeps that layer blocked until a fresh review
replaces it.

## Creating a stack

`gh stack init` must run on a branch, not a detached `HEAD`, and bases the first
layer on the local trunk ref; `gh stack rebase` fetches the trunk and rebases
the whole stack onto it. `gh stack submit --auto` opens each PR with the
repository's PR template as its body, which the AI review's metadata gate blocks
— every layer needs a real description before review.

Run without a TTY, as an agent runs it, the v0.2.0 `init`, `submit`, `rebase`,
`merge`, and `unstack` subcommands write no git config; under a TTY, `init` asks
before enabling `rerere`. The vendored skill's setup writes the repository-local
`rerere.enabled` and `remote.pushDefault` explicitly.

## Policy

Only `gh stack push`, `gh stack rebase`, and `gh stack sync` may force-push,
with `--force-with-lease`, and only on branches of a GitHub stack. Every other
branch update is a plain push. The repository-local `rerere.enabled` and
`remote.pushDefault` are the only git config changes allowed for stacks.

Rejected alternatives:

- **Merge-only updates for stack branches.** GitHub's post-merge rebase rewrites
  every remaining layer anyway, so a local merge-based copy diverges after the
  first merge, and merging the rewritten remote branch would resurrect the
  pre-rebase commits.
- **Our own `gh stack` driver skill.** The upstream `gh-stack` skill already
  encodes the non-interactive flags and exit-code recovery an agent needs, and
  it is versioned with the extension; it is vendored unchanged instead.
- **The server-side Rebase stack button.** It updates refs through GitHub, which
  `AGENTS.md` forbids.
