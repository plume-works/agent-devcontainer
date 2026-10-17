---
type: architecture
description: How a GitHub native stacked pull request is detected, merged, and re-checked after a lower layer lands in this repository, and why stack branches alone may be force-pushed.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T09:00:00Z
sources:
- resource: https://docs.github.com/en/pull-requests/how-tos/stacked-pull-requests
- resource: https://docs.github.com/en/pull-requests/get-started/about-stacked-prs
- resource: https://github.com/plume-works/agent-devcontainer/pull/256
- resource: https://github.com/plume-works/agent-devcontainer/pull/257
- resource: https://github.com/plume-works/agent-devcontainer/pull/268
- resource: https://github.com/github/gh-stack/releases/tag/v0.2.1
- resource: https://github.com/github/gh-stack/issues/380
- resource: https://github.com/github/gh-stack/issues/472
- resource: https://github.com/github/gh-stack/issues/489
- resource: ansible/roles/github_cli/tasks/main.yml
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
---

# Stacked pull requests

Facts below hold for `gh-stack` v0.2.1 against the `main` ruleset of this
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

Auto-merge cannot be enabled on any layer: GraphQL `enablePullRequestAutoMerge`
refuses it with "Auto-merge is not supported for stacked pull requests", even
where the repository allows auto-merge. Stacks are merge-queue aware.

Every branch of a stack must live in the same repository; GitHub does not
support cross-fork stacks.

## Conflicts between layers

A layer's mergeability is computed against the layer below it. When the lower
layer changes a line the layer above also changes, the upper PR reports
`mergeable: CONFLICTING` and `mergeStateStatus: DIRTY` once GitHub recomputes
it; the REST `base.sha` can lag behind the lower layer's new tip meanwhile.
`gh stack rebase` stops on the conflict with exit 3; resolving the files,
`git add`, and `gh stack rebase --continue` finish the cascade, and
`gh stack push` clears the conflict on GitHub.

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
layer on the local trunk ref. For a branch that exists only on the remote, it
creates the local branch at the trunk tip rather than adopting the remote one,
so the next push replaces the real branch and closes its PR
(github/gh-stack#489). `gh stack rebase` fetches the trunk and every layer,
fast-forwards layers that are behind their remote, skips merged layers, and
rebases the whole stack onto the trunk; it never pushes.
`gh stack submit --auto` opens each PR with the repository's PR template as its
body, which the AI review's metadata gate blocks — every layer needs a real
description before review.

Run without a TTY, as an agent runs it, the `init`, `submit`, `rebase`, `merge`,
and `unstack` subcommands write no git config; under a TTY, `init` asks before
enabling `rerere`. The gh-stack skill's setup writes the repository-local
`rerere.enabled` and `remote.pushDefault` explicitly.

## Pushing

`gh stack push` and `gh stack submit` fetch every layer and then lease each push
against the tracking ref they just updated, so the lease always passes and a
stale local layer replaces newer remote commits (github/gh-stack#380).
`gh stack sync` fast-forwards a layer only when the local tip is an ancestor of
its remote and skips a diverged layer. When it rebases, it force-pushes with the
same fresh lease. When it does not, its plain push is rejected, yet it reports
`Stack synced` and exits 0 (github/gh-stack#472). The repository's answer is the
[Stack push guard](stack-push-guard.md).

## Tooling

The image installs `gh-stack` as a precompiled `gh` extension: the `github_cli`
role downloads the release binary for the architecture, checks it against a
pinned SHA-256, and writes the extension manifest itself. `gh extension install`
is not used because it requires an authenticated `gh` even for a public
extension, and an image build has no token.

The gh-stack skill's `SKILL.md` is repository-owned ([Stack push
guard](stack-push-guard.md) records why); only its `references/upstream/` pages
and `LICENSE` are GitHub's, copied unchanged from the pinned tag. Re-vendor them
from the tag when upstream changes them, and re-read the release's push and sync
behavior against the guard. Nothing ties the copy to the pin automatically.

## Policy

Only `gh stack rebase` and the gh-stack skill's guarded `publish` may
force-push, with `--force-with-lease`, and only on branches of a GitHub stack,
after the guard's `begin` ([Stack push guard](stack-push-guard.md)). A bare
`gh stack push`, `submit`, or `sync` is never run. Every other branch update is
a plain push. The repository-local `rerere.enabled` and `remote.pushDefault` are
the only git config changes allowed for stacks.

Rejected alternatives:

- **Merge-only updates for stack branches.** GitHub's post-merge rebase rewrites
  every remaining layer anyway, so a local merge-based copy diverges after the
  first merge, and merging the rewritten remote branch would resurrect the
  pre-rebase commits.
- **The server-side Rebase stack button.** It updates refs through GitHub, which
  `AGENTS.md` forbids.
