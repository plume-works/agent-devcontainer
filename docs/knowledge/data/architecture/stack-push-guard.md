---
type: architecture
description: Why every remote update of a GitHub stack goes through the gh-stack skill's two-phase stack-guard.sh, why the skill is repository-owned over upstream's reference pages, and why gh stack sync left the workflows.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-18T18:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.sh
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
- resource: https://github.com/github/gh-stack/blob/v0.2.1/internal/git/gitops.go
- resource: https://github.com/github/gh-stack/blob/v0.2.1/cmd/push.go
- resource: https://github.com/github/gh-stack/blob/v0.2.1/cmd/link.go
- resource: https://github.com/github/gh-stack/blob/v0.2.1/cmd/sync.go
- resource: https://github.com/github/gh-stack/blob/v0.2.1/cmd/rebase.go
- resource: https://github.com/github/gh-stack/issues/380
---

# Stack push guard

`gh stack push`, `submit`, and `sync` take their `--force-with-lease` from a
tracking ref they have just fetched, so the lease cannot protect a layer's
remote-only commits ([Stacked pull requests](stacked-prs.md)). The repository
therefore never relies on gh-stack's lease.

## Decision

**Two phases, one script.** The gh-stack skill's `agent-code/stack-guard.sh` has
two subcommands:

- `begin` runs before anything rewrites the stack. It fast-forwards a layer
  whose local tip is an ancestor of its remote. It stops on a layer whose remote
  holds a commit with no identical patch locally, whitespace included, or a
  merge commit the local branch lacks, with the trunk excluded so that GitHub's
  post-merge rebase is not a loss. It records every layer's remote tip in
  `./.tmp/gh-stack-guard/tips`.
- `publish` replaces `gh stack push` (and, with `--submit`,
  `gh stack submit --auto`). It stops when a recorded tip moved, pushes the
  changed layers itself, with `--submit` runs `gh stack link`, then verifies
  that every remote tip equals its local tip.

The recorded tip is the lease gh-stack fails to take. The check has to run
before the rewrite. After a rebase whose conflict was resolved, a layer's patch
changes, so a patch test run then either stops on harmless work or, compared
with the pre-rebase tip, misses a remote commit. `publish` without a record
falls back to the patch test, which can stop when nothing is lost but never
misses remote work.

**`gh stack sync` is out of the workflows.** A refresh after a merge or trunk
move is `begin`, `gh stack rebase`, `publish`. `rebase` fetches, fast-forwards
layers that are behind, skips merged layers, and refreshes PR state, but never
pushes. `sync` pushes by itself, rebasing a diverged layer with the fresh lease,
and exits 0 when its own push is rejected.

**The skill is repository-owned over upstream references.** `SKILL.md` is ours
and expresses every workflow through the guard. GitHub's reference pages stay
byte-for-byte under `references/upstream/` with their MIT `LICENSE`; `SKILL.md`
overrides any push or sync they mention. A re-vendor replaces only
`references/upstream/`.

The record is one file per checkout, not per stack. A `begin` for one stack
replaces another stack's record, so that stack's next `publish` falls back to
the patch test. Where Git does not already ignore `.tmp/`, the guard adds it to
`.git/info/exclude`, since `gh stack rebase` refuses a worktree with untracked
files.

**The guard is the only force-pusher.** `publish` never runs `gh stack push` or
`submit`. It pushes every layer whose remote differs from its local tip in one
`git push --atomic`, each with `--force-with-lease` on the tip its checks
examined (an empty lease for a layer absent on the remote). That tip is read
from the remote-tracking ref after the guard's own fetch; `git ls-remote` only
says which layers exist. A push that landed after the fetch rejects the whole
push, so nothing is overwritten and `publish` reports `REMOTE_MOVED`. Atomicity
leaves no half-published stack; it needs a remote that supports atomic pushes,
as GitHub does.

**`--submit` goes through `gh stack link`.** After the guarded push, `link`
pushes the named layers without force and atomically, so it is a no-op or a
rejection, never an overwrite. It opens the missing PRs as drafts with the
repository's PR template as body, titled after the branch name, and chains each
PR onto the argument before it. That chaining is positional, so create mode
(every unmerged layer, bottom to top, on `--base <trunk>`) runs only while no
layer has merged; it also repairs bases and membership. Once a layer has merged,
`--submit` uses add mode, `gh stack link <stack-number> <new layers>`, which
appends the layers without a PR to the top of the GitHub stack and leaves its
current PRs alone. The stack number comes from
`gh api repos/{owner}/{repo}/pulls/<n> --jq .stack.number` on a layer's PR, read
before the push, so a failed lookup changes nothing. Add mode cannot insert, so
a layer without a PR below one with a PR is refused, as is an all-digit layer
name, which `link` reads as a PR number. With every layer holding a PR and one
merged, no link runs: the push already updated the PRs. A queued layer is passed
to create mode by its PR URL, which `link` neither pushes nor drops from the
stack.

**Queued layers are guarded, never pushed.** A push to a queued layer would take
its PR out of the merge queue. Every subcommand checks and records every
unmerged layer, the guard's push leaves a queued one alone, and the final check
accepts a queued layer that still sits at the tip publish checked.

The remote-only test compares patches with `git patch-id --verbatim`. The
default patch-id and `--cherry-pick` ignore whitespace, so a whitespace-only fix
on the remote would count as already present.

## Rejected alternatives

- **A gate beside the unchanged vendored skill.** The vendored core loop and
  editing recipe still teach a bare push, so following the skill bypasses the
  gate.
- **Patching the vendored `SKILL.md` in place.** The file would keep the
  "vendored" label while no longer being upstream's, and every re-vendor would
  need a hand merge.
- **Dropping the upstream references too.** Their command preconditions and
  recovery detail depend on the release, and would have to be re-derived on
  every pin bump.
- **`gh stack sync` before every push.** `sync` loses remote-only commits itself
  whenever it rebases.
- **Delegating the push to gh stack and detecting a loss afterwards.** gh-stack
  re-fetches and leases on what it just saw, so every window between the guard's
  check and gh-stack's fetch overwrites, and reading the loss back from the
  reflog depends on reflogs gc and expiry may prune. Detection also leaves the
  lost commits to be recovered by hand.
- **Pushing layer by layer.** A lease rejection part-way would leave lower
  layers published and upper ones stale; one atomic push avoids that.
- **A single check just before the push.** Once local history is rewritten, the
  patch test cannot tell a resolved conflict from lost work.
- **Waiting for upstream #380.** Data loss stays possible until a fixed release
  is pinned, and nothing here controls when that is.
