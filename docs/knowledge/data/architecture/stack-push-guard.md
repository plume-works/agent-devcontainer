---
type: architecture
description: Why every remote update of a GitHub stack goes through the gh-stack skill's two-phase stack-guard.sh, why the skill is repository-owned over upstream's reference pages, and why gh stack sync left the workflows.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T09:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.sh
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
- resource: https://github.com/github/gh-stack/blob/v0.2.1/internal/git/gitops.go
- resource: https://github.com/github/gh-stack/blob/v0.2.1/cmd/push.go
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
  holds a commit with no patch-equivalent locally, with the trunk excluded so
  that GitHub's post-merge rebase is not a loss. It records every layer's remote
  tip in `./.tmp/gh-stack-guard/tips`.
- `publish` replaces `gh stack push` (and, with `--submit`,
  `gh stack submit --auto`). It stops when a recorded tip moved, pushes, then
  verifies that every remote tip equals its local tip.

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

The time between `publish`'s check and gh-stack's own fetch is not covered. The
check after the push detects an overwrite in that window but cannot prevent it.

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
- **A single check just before the push.** Once local history is rewritten, the
  patch test cannot tell a resolved conflict from lost work.
- **Waiting for upstream #380.** Data loss stays possible until a fixed release
  is pinned, and nothing here controls when that is.
