---
type: plan
created: 2026-10-17
description: Route every stack branch update through a two-phase guard script — begin before the stack is rewritten, publish in place of a bare push — inside a repo-owned gh-stack skill that keeps upstream's reference pages, so no gh stack push, submit, or sync can overwrite commits that exist only on a layer's remote.
release:
- bugs/gh-stack-push-overwrites-remote-layer
- features/native-stacked-prs
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md
- resource: AGENTS.md
- resource: https://github.com/github/gh-stack/blob/v0.2.1/internal/git/gitops.go
- resource: https://github.com/github/gh-stack/blob/v0.2.1/cmd/push.go
- resource: https://github.com/github/gh-stack/blob/v0.2.1/cmd/sync.go
- resource: https://github.com/github/gh-stack/blob/v0.2.1/cmd/utils.go
- resource: https://github.com/github/gh-stack/blob/v0.2.1/cmd/rebase.go
- resource: https://github.com/github/gh-stack/issues/380
- resource: https://github.com/github/gh-stack/issues/489
- resource: https://github.com/github/gh-stack/issues/472
---

# Guard every gh stack push against overwriting a layer's remote commits

## Context

[Bug: gh stack push overwrites a stack layer whose remote is
ahead](../bugs/gh-stack-push-overwrites-remote-layer.md). In `gh-stack` v0.2.1,
`push` and `submit` fetch every layer and only then build each
`--force-with-lease` value from the tracking ref they just updated
(`cmd/push.go:106`, `internal/git/gitops.go:257-276`). The lease therefore
always passes, and a stale local layer replaces newer remote commits. No manual
`git fetch` is involved. Upstream tracks this as github/gh-stack#380.

`gh stack sync` does not close the gap:

- it fast-forwards a layer only when the local tip is an ancestor of the remote
  (`cmd/utils.go:896-925`) and skips a diverged layer;
- when it rebases (trunk moved, a layer was fast-forwarded, or a layer merged),
  it force-pushes with the same fresh lease and loses the remote-only commits;
- when it does not rebase, its plain push is rejected, yet it prints
  `Stack synced` and exits `0` (github/gh-stack#472), and its hint to run
  `gh stack push` then loses the commits.

`gh stack init <branch>` for a branch that exists only on the remote creates the
local branch at the trunk tip, and the next `submit` force-pushes it over the
real branch and closes its pull request (github/gh-stack#489).

Five repository skills call `gh stack push` or `gh stack sync` directly. The
vendored skill's own core loop and editing recipe teach the same bare push, so a
gate that lives beside the vendored skill can still be bypassed.

## Approach

**One repository-owned guard script, `gh-stack/agent-code/stack-guard.sh`, with
two subcommands.**

- `begin`: run before anything rewrites the stack (a commit on a layer,
  `gh stack rebase`, `gh stack init` of an existing branch). It fetches every
  active layer. It fast-forwards a layer whose local tip is an ancestor of its
  remote. It stops on a layer whose remote holds a commit with no
  patch-equivalent in the local branch, excluding the trunk:
  `git rev-list --right-only --cherry-pick --no-merges L...<remote>/L ^<remote>/<trunk>`.
  Finally it records every layer's remote tip in a state file under `./.tmp/`.
- `publish`: run in place of `gh stack push`, or with `--submit` in place of
  `gh stack submit --auto`. It fetches and stops if any layer's remote tip moved
  since `begin`. It then runs the gh-stack command and verifies that every
  layer's remote tip equals its local tip.

The recorded tip acts as the lease that gh-stack fails to take. Without a state
file, `publish` runs `begin`'s patch test against the current local tips. That
fallback never misses remote-only work, but it also stops after a
conflict-resolved rebase, whose resolution changes a layer's patch.

**The `gh-stack` skill becomes repository-owned, and upstream's reference pages
stay inside it unchanged.** `SKILL.md` is rewritten as ours. It keeps the name,
the discovery triggers, and upstream's non-interactive-flags guidance, and it
expresses every create, edit, publish, post-merge and recovery workflow through
the guard. `references/` moves verbatim to `references/upstream/` together with
the MIT `LICENSE`. Where an upstream page says to run `gh stack push` or `sync`,
our `SKILL.md` overrides it. A re-vendor replaces only `references/upstream/`.

**`gh stack sync` leaves our workflows.** A post-merge or trunk refresh becomes
`begin`, then `gh stack rebase`, then `publish`. `rebase` already fetches,
fast-forwards layers that are behind, skips merged layers and refreshes PR state
(`cmd/rebase.go:181-215`), but it never pushes. Every push therefore passes
through `publish`, and `sync`'s exit `0` after a failed push leaves the path.

Rejected:

- **A gate script beside the unchanged vendored skill**: the vendored core loop
  still teaches a bare `push`.
- **Patching the vendored `SKILL.md` in place**: it keeps the "vendored" label
  on a file that is no longer upstream's, and every re-vendor has to merge by
  hand.
- **Dropping the upstream references too**: their version-specific command and
  recovery detail then has to be re-derived on every pin bump.
- **`gh stack sync` before every push**: it loses commits itself whenever it
  rebases.
- **One check just before the push**: once local history is rewritten, the patch
  test either stops on a resolved conflict or, compared against the pre-rebase
  tip, misses a remote commit.
- **Waiting for upstream #380**: data loss stays possible until a fixed release
  is pinned, and nothing here controls when that is.

The time between `publish`'s check and gh-stack's own fetch is not covered. The
check after the push detects an overwrite in that window but cannot prevent it.

Assumption: the state file is `./.tmp/gh-stack-guard/tips`, one per checkout, so
each worktree that pr-merge-stack creates under `./.tmp/` has its own. A `begin`
overwrites it.

## Implementation Steps

### Task 1: Guard script and its tests

**Files:** Create:
`.agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.sh`,
`.agents/plugins/agentdev/tests/test_gh_stack_guard.py`

- [x] `stack-guard.sh begin [--remote <name>]` and
  `stack-guard.sh publish [--submit] [--remote <name>]` follow the
  `/agentdev:skill-scripts` contract through `bin/result-codes.sh`. Layers and
  trunk are read from `gh stack view --json`, and merged or queued layers are
  skipped. Named results: `SUCCESS`, `PREFLIGHT_ERROR` (not a repo, not in a
  stack, detached HEAD), `REMOTE_ONLY_COMMITS` (begin, or publish's fallback;
  stderr lists the commits per layer), `REMOTE_MOVED` (publish; stderr names the
  layer and both SHAs), `PUSH_FAILED` (the gh-stack command exited non-zero),
  and `PUSH_INCOMPLETE` (exit `0`, but a remote tip differs from its local tip).
  `begin` prints `FAST_FORWARDED=<layer>` for each layer it moved, so the caller
  knows to run `gh stack rebase --upstack`.

  - **Evidence:** commit `feat(gh-stack): add stack-guard.sh begin and publish`;
    `shellcheck` clean, and every named result is asserted in
    `tests/test_gh_stack_guard.py`.

- [x] pytest covers, with a bare remote, a second publisher clone, and a stubbed
  `gh` whose `stack push`/`stack submit` do what gh-stack does (fetch, then a
  lease taken from the fresh tracking ref):

  | Case                                                         | Expected                                                                         |
  | ------------------------------------------------------------ | -------------------------------------------------------------------------------- |
  | remote ahead of local                                        | `begin` fast-forwards, `FAST_FORWARDED`; `publish` `SUCCESS`                     |
  | local and remote each gained a commit                        | `begin` `REMOTE_ONLY_COMMITS` naming the remote commit                           |
  | lower layer squash-merged, upper layer rebased by the remote | `begin` `SUCCESS`                                                                |
  | that, plus a new remote commit on the upper layer            | `begin` `REMOTE_ONLY_COMMITS` naming only that commit                            |
  | that, plus a new local commit on the upper layer             | `begin` `SUCCESS`                                                                |
  | lower layer edited, upper rebased cleanly                    | `publish` `SUCCESS`, tips verified                                               |
  | lower layer edited, rebase conflict resolved                 | `publish` after `begin` `SUCCESS`; `publish` without state `REMOTE_ONLY_COMMITS` |
  | remote gained a commit between `begin` and `publish`         | `publish` `REMOTE_MOVED`, stub push never ran                                    |
  | stub push exits 0 but leaves a remote tip unchanged          | `publish` `PUSH_INCOMPLETE`                                                      |
  | layer exists only on the remote, local created at trunk      | `begin` fast-forwards it to the remote tip                                       |

  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests/test_gh_stack_guard.py` passed
    14 tests in the same commit, and so did the full plugin suite (153 tests).
    Removing the moved-tip check, the begin check, or the trunk exclusion each
    fails at least one test.

### Task 2: Repository-owned gh-stack skill over upstream references

**Files:** Modify: `.agents/plugins/agentdev/skills/gh-stack/SKILL.md`; Move:
`.agents/plugins/agentdev/skills/gh-stack/references/*.md` →
`.agents/plugins/agentdev/skills/gh-stack/references/upstream/`,
`.agents/plugins/agentdev/skills/gh-stack/LICENSE` →
`.agents/plugins/agentdev/skills/gh-stack/references/upstream/LICENSE`

- [ ] The three upstream pages move byte-for-byte (`git mv`, no content change),
  next to the `LICENSE` they ship under.
- [ ] `SKILL.md` keeps `name: gh-stack` and a discovery description that covers
  the same triggers. It drops upstream's `metadata.author`/`version`, and it
  credits the adapted non-interactive guidance to `github/gh-stack` under
  `references/upstream/LICENSE`.
- [ ] Every workflow in `SKILL.md` that updates a remote branch goes through the
  guard. That covers creating a stack (with `begin` before `gh stack init` of an
  existing branch), editing a layer, publishing, refreshing after a merge or
  trunk move (`begin` → `gh stack rebase` → `publish`), and rebase-conflict
  recovery. It includes a result table for every `stack-guard.sh` result. No
  step runs a bare `gh stack push`, `gh stack submit`, or `gh stack sync`, and
  the skill states that this overrides the upstream pages.
- [ ] `REMOTE_ONLY_COMMITS` and `REMOTE_MOVED` stop the workflow and ask the
  user how to incorporate the listed commits. The skill never resolves
  divergence on its own.

### Task 3: Re-point the stack callers

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-open/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-merge/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md`,
`.agents/plugins/agentdev/skills/update-branch/SKILL.md`

- [ ] Each caller names the gh-stack skill's publish workflow, or `begin` before
  its stack edit, where it now names `gh stack push` or `gh stack sync`.
  pr-merge-stack's partial-merge recovery uses the post-merge refresh.
  update-branch's Workflow 0 and its result table direct to that refresh.
- [ ] `grep -rn "gh stack push\|gh stack sync\|gh stack submit" .agents/plugins/agentdev/skills --include=SKILL.md`
  matches only the gh-stack skill's own non-interactive guidance and its
  statements about what the guard runs.

### Task 4: Force-push exception names the guard

**Files:** Modify: `AGENTS.md`, `docs/knowledge/data/product.md`

- [ ] `AGENTS.md`'s force-push exception allows the `--force-with-lease` updates
  of GitHub stack branches made by `gh stack rebase` and by
  `stack-guard.sh publish`, only after `stack-guard.sh begin`, and points to
  `docs/knowledge/data/architecture/stacked-prs.md`. Its git-config exception
  names the gh-stack skill's setup without "vendored". `product.md`'s
  `## Authoring rules` mirror says the same.

### Task 5: Record the decision and the gh-stack behavior

**Files:** Create: `docs/knowledge/data/architecture/stack-push-guard.md`;
Modify: `docs/knowledge/data/architecture.md`,
`docs/knowledge/data/architecture/stacked-prs.md`

- [ ] `architecture/stack-push-guard` records the two-phase guard, the
  repository-owned skill over upstream references, the replacement of
  `gh stack sync`, the uncovered fetch window, and every rejected alternative in
  `## Approach`. It is linked from `data/architecture.md`.
- [ ] `architecture/stacked-prs` states its facts for v0.2.1. It records the
  fetch-then-lease behavior of `push`/`submit`/`sync`, `sync`'s exit `0` after a
  failed push, and `init`'s trunk-based creation of a remote-only branch. Its
  Policy points to the guard. The "Our own `gh stack` driver skill" rejection is
  replaced by a link to `architecture/stack-push-guard`. Its Tooling section
  says that a re-vendor replaces only `references/upstream/`.

### Task 6: Feature, bug, and codebase-map docs follow

**Files:** Modify: `docs/knowledge/data/features/native-stacked-prs.md`,
`docs/knowledge/data/bugs/gh-stack-push-overwrites-remote-layer.md`,
`docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md`

- [ ] `features/native-stacked-prs` describes the repository-owned gh-stack
  skill and the guard, and states that stack branches are updated only through
  it. It no longer claims that a test keeps the skill on the pinned release. Its
  edge cases say a partial merge is refreshed with `begin` → `gh stack rebase` →
  `publish`.
- [ ] The bug's Reproduction drops the manual `git fetch` step. Its Root cause
  states gh-stack's fetch-then-lease, the `sync` cases, and #489, and its Fix
  names this plan.
- [ ] The codebase map is refreshed with `/agentdev:iwe-map` refresh mode for
  the touched skills, and `stale-map-docs.py` reports none.

### Task 7: Guard proven against a real GitHub stack

**Files:** none (evidence only)

- [ ] On a scratch repository, a two-layer stack runs each case from Task 1's
  table through the gh-stack skill's workflows with the real `gh stack`. No case
  loses a remote commit, and the run's PR timelines show no
  `head_ref_force_pushed` that drops a commit. Branches and PRs are cleaned up
  afterwards.

## Spec changes

[Stacked PRs](../spec/stacked-prs.md). This is contract-heavy because it governs
data loss on shared branches.

``` markdown
## MODIFIED Requirements

### Requirement: Force-pushes are limited to stack branches

Agent skills SHALL NOT force-push, except that `gh stack rebase` and the
gh-stack skill's `stack-guard.sh publish` MAY update branches of a GitHub stack
with `--force-with-lease`. The repository-local `rerere.enabled` and
`remote.pushDefault` written by `gh stack` or the gh-stack skill's setup are the
only permitted git config changes.

#### Scenario: Branch outside a stack

- **WHEN** a skill must update a branch that belongs to no GitHub stack
- **THEN** it pushes without force

#### Scenario: Lower layer changed

- **WHEN** a commit lands on a lower layer of a stack
- **THEN** the layers above are updated with `gh stack rebase --upstack` and
  published with `stack-guard.sh publish`

### Requirement: update-branch refuses stack branches

The update-branch skill SHALL refuse a branch that belongs to a GitHub stack and
SHALL direct the caller to the gh-stack skill's post-merge refresh.

#### Scenario: Stack branch

- **WHEN** update-branch runs on a branch of a GitHub stack
- **THEN** it stops without merging and names the gh-stack skill's refresh

## ADDED Requirements

### Requirement: Stack pushes never drop remote-only commits

Agent skills SHALL update the remote branches of a GitHub stack only through
`stack-guard.sh publish`, never with a bare `gh stack push`, `gh stack submit`,
or `gh stack sync`. `stack-guard.sh begin` SHALL run before a skill rewrites a
stack layer. It SHALL fast-forward a layer that its remote is ahead of, and it
SHALL stop when a layer's remote holds a commit whose patch the local branch
lacks, excluding the trunk. `publish` SHALL stop when a layer's remote tip moved
since `begin`, and SHALL report a remote tip that differs from its local tip
after the push.

#### Scenario: Remote ahead

- **WHEN** `begin` runs and a layer's local tip is an ancestor of its remote tip
- **THEN** it fast-forwards the local layer and reports it

#### Scenario: Remote-only commit

- **WHEN** `begin` runs and a layer's remote holds a commit whose patch the
  local branch lacks
- **THEN** it stops, names the commit, and the skill asks the user how to
  incorporate it

#### Scenario: Remote rebased after a lower layer merged

- **WHEN** GitHub rebased a layer after a lower layer merged, and the remote
  holds no other commit
- **THEN** `begin` succeeds

#### Scenario: Remote moved during the edit

- **WHEN** a layer's remote tip changed between `begin` and `publish`
- **THEN** `publish` stops before pushing and names the layer

#### Scenario: Push left a layer behind

- **WHEN** the gh-stack push exits `0` but a layer's remote tip differs from its
  local tip
- **THEN** `publish` reports the layer as not published
```

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_gh_stack_guard.py`
- `shellcheck .agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.sh`
- `git diff --stat main -- .agents/plugins/agentdev/skills/gh-stack/references/upstream/`
  shows only renames, with 100% similarity.
- The Task 3 grep finds no bare push, submit, or sync outside the gh-stack
  skill's guidance.
- `uv run validate_agent_files .agents/plugins/agentdev/skills/*/SKILL.md`
  passes.
- `uv run pytest docs/knowledge/tests` passes.
- `iwe normalize` and `iwe schema validate` pass, and `stale-map-docs.py`
  reports no stale map doc.
- Task 7's run on a real GitHub stack.

## Out of scope

- Fixing gh-stack itself. Upstream #380, #489, and #472 stay upstream's to fix.
  When #380 ships, this guard's `publish` check becomes redundant but harmless.
- Merge commits inside a layer: `--no-merges` ignores them, and update-branch
  already keeps merges off stack branches.
- Resolving divergence automatically. The guard stops, and the user decides.
- The time between `publish`'s check and gh-stack's own fetch.

## Key references

Verified anchor points (line numbers as of 2026-10-17):

- `.agents/plugins/agentdev/skills/gh-stack/SKILL.md:30-38` — Setup, which
  writes the repository-local git config
- `.agents/plugins/agentdev/skills/gh-stack/SKILL.md:73-83` — editing an
  existing stack, ending in `gh stack push`
- `.agents/plugins/agentdev/skills/gh-stack/SKILL.md:86-93` — core loop, ending
  in `gh stack submit --auto`
- `.agents/plugins/agentdev/skills/gh-stack/SKILL.md:100-109` — Staying in sync
  with `gh stack sync`
- `.agents/plugins/agentdev/skills/gh-stack/SKILL.md:163-166` — rebase and sync
  conflict recovery
- `.agents/plugins/agentdev/skills/gh-stack/SKILL.md:189-193` — links to
  `references/`
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:220-222` — stack branches
  pushed with `gh stack push`
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:260` — force-push rule
  naming `gh stack push`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:78` — force-push rule
  naming `gh stack push`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:104-105` — conflict commit
  followed by `rebase --upstack` and `push`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:201-202` — stacked PR
  remediation through `rebase --upstack` and `push`
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:65-66` —
  stacked PR conflict through `rebase` and `push`
- `.agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md:22-23` — stack
  branches updated by rebase, sync, and push
- `.agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md:57-58` — layers above
  re-synced with `rebase --upstack` and `push`
- `.agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md:84-89` — partial
  merge recovery through `gh stack sync`
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:87-88` — Workflow 0
  directing to `gh stack sync`
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:159` — result table
  row naming `gh stack sync`
- `.agents/plugins/agentdev/bin/result-codes.sh` — shared result helpers
- `.agents/plugins/agentdev/tests/git_fixtures.py:19` — `git` fixture runner and
  `stub_gh`
- `AGENTS.md:6` — force-push exception
- `AGENTS.md:11` — git-config exception naming the vendored skill
- `docs/knowledge/data/product.md:123-127` — Authoring rules mirror of both
  exceptions
- `docs/knowledge/data/architecture/stacked-prs.md:22` — facts stated for v0.2.0
- `docs/knowledge/data/architecture/stacked-prs.md:108-111` — re-vendor
  procedure
- `docs/knowledge/data/architecture/stacked-prs.md:126-128` — rejected "Our own
  `gh stack` driver skill"
- `docs/knowledge/data/features/native-stacked-prs.md:27-29` — vendored skill
  "kept on the same release by a test"
- `docs/knowledge/data/features/native-stacked-prs.md:56-58` — partial merge
  re-synced with `gh stack sync`
- `docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md:41` —
  "vendored unchanged from `github/gh-stack`"
