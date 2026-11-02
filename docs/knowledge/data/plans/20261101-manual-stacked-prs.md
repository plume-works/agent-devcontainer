---
type: plan
created: 2026-11-01
release:
- features/manual-stacked-prs
- features/native-stacked-prs
- bugs/stack-guard-reverts-post-merge-rebase
description: Remove gh stack and GitHub native stacks and replace them with manual stacked pull requests — branches cut from their predecessor, kept current only with merges, and restacked after a squash merge by one pr-restack-all run.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T13:00:00Z
sources:
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py
- resource: ansible/roles/github_cli/tasks/main.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
rank: 300
---

# Replace gh stack with manual stacked pull requests

## Context

GitHub native stacks rewrite history twice: GitHub rebases every remaining layer
on the server after a lower layer merges, and `gh stack rebase` rewrites them
again locally before a force-push. The stack guard checks only that no remote
commit lacks an identical local patch, so it cannot detect a force-push that
undoes a server-side rebase — [Bug: the stack guard reverts GitHub's post-merge
rebase](../bugs/stack-guard-reverts-post-merge-rebase.md). A plain push of the
same branch is rejected as non-fast-forward.

The maintainer's decision: "GET RID OF GH STACKS. WE DO ONLY NORMAL PRs".
Dependent work becomes [Manual stacked pull
requests](../features/manual-stacked-prs.md), replacing [Native stacked pull
requests](../features/native-stacked-prs.md). Prior art: `implement-agent-specs`
(`c1dce219:.claude/skills/implement-agent-specs/SKILL.md`) cut a dependent
branch from its predecessor's; `pr-merge-chain`
(`9ecc8876^:.agents/plugins/agentdev/skills/pr-merge-chain/SKILL.md`)
reconnected a successor to its predecessor's squash commit with merges.

IWE plans that build on an unshipped dependency are a separate plan that depends
on this one.

## Approach

No branch is ever rewritten. A dependent branch is cut from its predecessor's
branch and records the dependency three ways: its git ancestry, a
`Depends-on: #<P>` trailer commit, and the PR body's `## Depends on` section.
Its PR targets the predecessor's branch, so GitHub shows a clean diff and
retargets it to `main` when the predecessor merges.

After a squash merge the successor is reconnected, not rebased: the
predecessor's final head and squash commit come from its PR metadata, the squash
commit is merged into a private copy of the head, and that copy is merged into
the successor. The reconnect merge yields the squash commit's tree.

One `pr-restack-all` run restacks a whole chain from a fresh detached worktree
built from remote refs, never touching a local branch, so it cannot disturb
another session's worktree; a session whose branch it advanced sees an ordinary
non-fast-forward rejection and merges.

All new code lives in the plugin's `bin/`; the PR body's `## Depends on` section
is parsed and rewritten by one module that `pr-restack-all` and the body
validation share.

Rejected:

- **Guarding `gh stack` harder.** A lease protects remote-only commits, not
  consumers of a rewritten branch, and GitHub's own post-merge rebase makes
  every local copy stale regardless of the tool.
- **Every PR targets `main`** (as `pr-merge-chain` did). Its diff includes every
  predecessor until they merge; basing on the predecessor gives a clean diff.
- **Resolving the reconnect merge with `-s ours`.** Correct by construction but
  silent; a normal merge lets git report a conflict.
- **Owners restacking their own PRs, or a coordinator pausing its sessions.**
  More coordination than one restack from a detached worktree.
- **A required `base-is-main` check without bypass.** It also rejects the
  owners' own pushes and branch creation (GH013).

Assumptions:

- `pr-sync` delegates to `pr-open`, so the body validation runs in
  `pr-gen-description` and in `pr-open` before it applies a body.
- A conflicted dependent PR is resolved by `update-branch` against its
  `baseRefName`; `pr-merge-stack` restacks after every merge, so a PR reaches
  `pr-feedback-resolution` already reconnected.

## Implementation Steps

Decision numbers inside the approved blocks below name parts of this plan: 4c is
the trailer commit (Task 2), 8 the restack scope and 16 the chain discovery
(Task 3), 9 the merge record (Task 1), 12 `pr-merge`'s base rule (Task 6).

### Task 1: The `## Depends on` and trailer module

**Files:** Create: `.agents/plugins/agentdev/bin/depends_on.py`,
`.agents/plugins/agentdev/tests/test_depends_on.py`

- [ ] `depends_on.py` finds a PR body's `## Depends on` section, lists its
  `- #<P>` entries in order, and replaces one entry's line with its merge
  record, leaving the rest of the body byte-for-byte; it reads every
  `Depends-on: #<P>` trailer from a branch's commits
- [ ] Tests cover a body with no section, one entry, several entries, an entry
  already carrying a record, the section followed by another heading, and
  trailers on two commits

The merge record replaces `- #P` with exactly this form:

``` text
- #591 — merged as d66fdf4d (head 7a8c22c2), reconnected
```

### Task 2: `git-new-branch --depends-on`

**Files:** Modify:
`.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py`,
`.agents/plugins/agentdev/skills/git-new-branch/SKILL.md`; Create:
`.agents/plugins/agentdev/tests/test_git_new_branch_depends_on.py`

- [ ] `--depends-on <P>`, repeatable, requires each PR to be open, cuts the
  branch from the first PR's head branch and merges the other heads in, adds one
  empty commit with a `Depends-on: #<P>` trailer per PR, and pushes without
  force; a PR that is not open stops it before anything is created
- [ ] `SKILL.md` documents the option, its result codes, and the rule that the
  predecessor's PR must exist first

Approved flow:

``` text
git-new-branch <name> --depends-on <P>
  1. gh pr view <P> --json state,headRefName   → must be OPEN
  2. base = origin/<headRefName>                → same cut as --base today
  3. empty commit:  Depends-on: #<P>            (decision 4c)
  4. plain push with its own upstream           (exists)
```

### Task 3: `pr-restack-all`

**Files:** Create: `.agents/plugins/agentdev/bin/pr_restack_all.py`,
`.agents/plugins/agentdev/skills/pr-restack-all/SKILL.md`,
`.agents/plugins/agentdev/tests/test_pr_restack_all.py`

- [ ] `pr_restack_all.py` takes a top PR or a branch and restacks the chain as
  the blocks below state, printing `RECONNECTED=#P HEAD=<HEAD> MERGE=<MERGE>`
  per reconnect and writing the merge record through Task 1's module after each
  push lands
- [ ] Tests run against real git repositories under `/tmp`, creating
  `refs/pull/N/head` refs and squash commits with plain git, with the PR
  metadata lookup behind one replaceable function: restack onto an open
  predecessor, onto a merged one, X+2 after X and X+1 merged, rerun after a
  conflict, a branch with two dependencies, and no local branch created or moved
- [ ] `SKILL.md` documents the inputs, result codes, the conflict-and-rerun
  path, and that it never merges `main`

Approved chain discovery:

- Input: the top PR. Walk down: each PR's base is its predecessor's head branch;
  the open PR with that head is the next link; a base of main is the bottom.
  Merge order is bottom to top.
- Merged layers drop out, since GitHub retargets the next PR to main.
- Per link, the last entry of the PR's `## Depends on` must be the PR below it,
  or stop.

Approved restack:

``` text
input: top PR
1. walk the chain from GitHub PRs (decision 16)
2. one fresh detached worktree in ./.tmp, from remote refs only
   (no local branch is checked out, created, or moved)
3. bottom-up, for each PR-N above the merged one:
     git checkout --detach origin/<PR-N branch>
     restack onto nearest predecessor P (decision 8)
     git push origin HEAD:refs/heads/<PR-N branch>     plain push
     write the merge record (decision 9)
4. conflict → stop, print the worktree path; resolve there, rerun
   (already-restacked PRs are skipped: MERGE(P) already in PR-N)
```

Approved restack scope:

- A restack never merges main; catching up with main is a separate
  `update-branch` run.
- A restack acts only on the nearest predecessor P = the last entry of PR-N's
  `## Depends on`. P open → merge origin/<P branch>. P merged → MERGE(P) already
  in PR-N → nothing to do; else reconnect for P, plain push. Earlier entries are
  carried in HEAD(P).

Approved reconnect, for a merged predecessor PR-X and its successor PR-X+1:

1. From PR-X metadata: HEAD = headRefOid (PR-X's final head), MERGE =
   mergeCommit.oid (its squash commit on main). Both come from PR metadata,
   never from branch refs.
2. `git fetch origin refs/pull/<PR-X>/head` — must equal HEAD.
3. Private copy of PR-X at HEAD, never pushed.
4. Merge MERGE into that copy — a normal `git merge`. A conflict is reported by
   git and handled like any merge conflict.
5. Merge that copy into PR-X+1, plain push.

A branch without a PR is restacked the same way, its dependencies read from its
`Depends-on:` trailers, every merged one reconnected.

Approved flow:

``` text
main   m0───o──────Sx──────q──────Sy───r
        \           \              \
         x1──x2──────Bx             \
               \       \             \
                y1──y2──Ry────────────By
                      \   \             \
                       z1──Rz1───────────Rz2   ← X+2
```

x·/y·/z· are PR-X, PR-X+1, PR-X+2 commits; Sx, Sy squash commits (MERGE); Bx, By
private copies (HEAD merged with MERGE, never pushed as a branch); Ry, Rz1, Rz2
restack merges, plain push. Order: X merges as Sx → X+1 restacks (Bx, Ry) → X+2
restacks onto open X+1 (Rz1) → X+1 merges as Sy → X+2 restacks onto merged X+1
(By, Rz2). X+2 takes main up to Sy, not r.

### Task 4: `## Depends on` body validation

**Files:** Create: `.agents/plugins/agentdev/bin/check_depends_on.py`,
`.agents/plugins/agentdev/tests/test_check_depends_on.py`; Modify:
`.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md`

- [ ] `check_depends_on.py` takes a candidate body and fails when Task 1's
  module cannot find its `## Depends on` section and entries, or could not
  rewrite an entry's line
- [ ] `pr-gen-description` writes `## Depends on` only for a new PR, keeps the
  current section byte-for-byte on regeneration, and runs the check in Step 8

### Task 5: `pr-open` opens a dependent PR

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-open/SKILL.md`

- [ ] The GitHub stack detection in step 8 and its force-push exception are
  gone; every push goes through the existing helper
- [ ] A branch carrying `Depends-on:` trailers runs `pr-restack-all <branch>` in
  step 4 instead of an `update-branch` merge, is refused while more than one
  dependency is unmerged, and in create mode gets its base from the one unmerged
  predecessor's head branch (`main` when none), the first `## Depends on`
  section, and no draft flag
- [ ] Step 9 runs Task 4's check before `gh pr create` and `gh pr edit`, and
  does not apply a body that fails it

### Task 6: `pr-merge` merges only into `main`

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [ ] Every `gh stack` path is gone: stack detection, `gh stack checkout`, the
  guarded re-sync after a reformat or fix commit, and `gh stack merge`
- [ ] `pr-merge` refuses a PR whose base is not `main` and never passes
  `--admin`

### Task 7: `pr-merge-stack` merges a chain

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md`

- [ ] The skill keeps its name and runs the approved loop, with step 2 run by
  the owning session or child inside a coordinator session and by the skill
  itself outside one, and step 4 always the skill's own single `pr-restack-all`
  run

``` text
input: top PR
loop:
  1. walk the chain from GitHub PRs (decision 16)    → bottom = the PR whose base is main
  2. pr-merge bottom                                  → CI, AI review, squash merge
                                                        (pr-merge refuses a base ≠ main, decision 12)
  3. GitHub retargets the next PR to main
  4. pr-restack-all top                               → restacks every PR still in the chain
  5. bottom was the top PR → done; else back to 1
```

### Task 8: `update-branch` and `pr-feedback-resolution` lose their stack paths

**Files:** Modify: `.agents/plugins/agentdev/skills/update-branch/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md`

- [ ] `update-branch` loses its stack prerequisite, Workflow 0, and the stack
  troubleshooting row; its script is unchanged
- [ ] `pr-feedback-resolution` resolves every conflicted PR through
  `update-branch --base <baseRefName>`, its pre-stack text (`bad960f6^`)

### Task 9: Delete the gh-stack skill

**Files:** Delete: `.agents/plugins/agentdev/skills/gh-stack/`,
`.agents/plugins/agentdev/tests/test_gh_stack_guard.py`; Modify:
`.prettierignore`, `.agents/plugins/agentdev/README.md`

- [ ] The skill directory, its guard tests, and its `.prettierignore` entry are
  gone, and the catalog README lists `pr-restack-all` and the new
  `pr-merge-stack` summary instead of `gh-stack`

### Task 10: The images stop shipping gh-stack

**Files:** Modify: `ansible/roles/github_cli/defaults/main.yml`,
`ansible/roles/github_cli/tasks/main.yml`,
`docker/deploy/agentdev-deploy.Dockerfile`,
`py_packages/agentdev_runtime/agentdev_runtime/agent_state.py`,
`py_packages/agentdev_runtime/agentdev_runtime/settings.py`,
`py_packages/agentdev_runtime/README.md`, `scripts/refresh-pin-checksums.py`,
`scripts/tests/test_agent_runtime_acceptance.py`

- [ ] The pinned download, its Renovate comment and checksums, the three install
  tasks, the deploy image's copy, the runtime registration and
  `AGENTDEV_GH_STACK_DIR`, the checksum refresh entry, and the acceptance
  check's `gh stack --help` are gone

### Task 11: The repository rules

**Files:** Modify: `AGENTS.md`, `docs/knowledge/data/product.md`

- [ ] `AGENTS.md` line 7 becomes:

``` text
NEVER force-push. NEVER use `gh stack` or GitHub native stacked pull requests; work that depends on an open pull request is a normal pull request based on its predecessor's branch and kept current with merges (see `docs/knowledge/data/architecture/manual-stacked-prs.md`).
NEVER rebase or reset a branch that has been pushed; bring in other history with a merge.
```

- [ ] Best Practice 0 becomes its pre-stack text (`a1c1563c^`):

``` text
0. NEVER change git config on local or global level unless explicitly instructed. NEVER switch/change remote.
```

- [ ] `product.md`'s `## Authoring rules` mirrors both, and its changelog
  records the change

### Task 12: Project memory

**Files:** Create: `docs/knowledge/data/architecture/manual-stacked-prs.md`;
Delete: `docs/knowledge/data/architecture/stacked-prs.md`,
`docs/knowledge/data/architecture/stack-push-guard.md`; Modify:
`docs/knowledge/data/architecture.md`,
`docs/knowledge/data/features/native-stacked-prs.md`,
`docs/knowledge/data/backlog/pr-merge-stack-post-merge-cleanup.md`,
`docs/knowledge/data/backlog.md`

- [ ] `architecture/manual-stacked-prs` records the design, the rejected
  alternatives above, and the reconnect evidence: a normal merge of the squash
  commit into the PR's final head, replayed with `git merge-tree` on every
  squash-merged PR where `main` had moved before the squash (145 in
  plume-works/agent-devcontainer, 73 in Dr-QP/Dr.QP), was clean and equal to the
  squash commit's tree every time, linked from the architecture hub; it does not
  reference the two deleted documents
- [ ] `architecture/stacked-prs` and `architecture/stack-push-guard` are removed
  with `iwe delete`, and every remaining link to them passes
  `iwe schema validate`
- [ ] `features/native-stacked-prs` is `stage: deprecated`
- [ ] `backlog/pr-merge-stack-post-merge-cleanup` is `stage: cancelled`, its
  link moved to `## Cancelled`

### Task 13: The `iwe/**` ruleset

**Files:** none — repository settings

- [ ] A ruleset on `refs/heads/iwe/**` requires the status check `base-is-main`,
  with the Write, Maintain, and Admin repository roles as bypass actors in mode
  `always`; no workflow reports the check

### Task 14: The AI responder's pushes

**Files:** none, or the Task 13 ruleset

- [ ] The identity `ai-responder.yml` pushes to PR branches with is confirmed,
  and when it is a GitHub App, that App is a bypass actor on the Task 13 ruleset

### Task 15: CI

**Files:** none

- [ ] The pull request's CI is green

## Spec changes

[Stacked PRs](../spec/stacked-prs.md) — its Purpose is rewritten for manual
stacks, `pr-merge merges explicitly` is unchanged, and:

``` markdown
## REMOVED Requirements

### Requirement: Stacked PRs merge through gh stack merge

GitHub native stacks and `gh stack` are no longer used.

### Requirement: Force-pushes are limited to stack branches

No force-push is permitted; replaced by "No branch is rewritten".

### Requirement: update-branch refuses stack branches

No branch belongs to a GitHub stack.

### Requirement: Stack pushes never drop remote-only commits

The guard and every `gh stack` push are removed.

## ADDED Requirements

### Requirement: No branch is rewritten

Agent skills SHALL NOT force-push, SHALL NOT rebase or reset a branch that has
been pushed, SHALL NOT run `gh stack`, and SHALL NOT create a GitHub native
stack. Another branch's history SHALL be brought in with a merge.

#### Scenario: Remote moved

- **WHEN** a skill's push is rejected as non-fast-forward
- **THEN** it merges the remote branch and pushes again without force

### Requirement: A dependent branch records its predecessors

`git-new-branch --depends-on <P>`, repeatable, SHALL require every named pull
request to be open, SHALL cut the branch from the first one's head branch and
merge the others' heads, SHALL add an empty commit with a `Depends-on: #<P>`
trailer for each, and SHALL push without force.

#### Scenario: One open predecessor

- **WHEN** `git-new-branch <name> --depends-on <P>` runs and P is open
- **THEN** the branch starts at P's head with a `Depends-on: #<P>` commit and is
  pushed

#### Scenario: Predecessor without an open pull request

- **WHEN** a named pull request is not open
- **THEN** it stops before creating a branch

#### Scenario: Two predecessors

- **WHEN** `--depends-on` names two open pull requests
- **THEN** the branch contains both heads and one trailer line for each

### Requirement: pr-open bases a dependent pull request on its predecessor

For a branch with `Depends-on:` trailers, pr-open SHALL run
`pr-restack-all <branch>` before creating or updating the pull request, SHALL
refuse while more than one dependency is unmerged, SHALL set a new pull
request's base to the unmerged predecessor's head branch, or `main` when none
is unmerged, SHALL write its first `## Depends on` section with one `- #<P>`
entry per dependency in merge order, and SHALL NOT open it as a draft.

#### Scenario: Open predecessor

- **WHEN** pr-open creates the pull request of a branch depending on open P
- **THEN** its base is P's head branch and its body lists `- #<P>` under
  `## Depends on`

#### Scenario: Two unmerged dependencies

- **WHEN** a branch depends on two unmerged pull requests
- **THEN** pr-open refuses and creates nothing

### Requirement: The Depends on section stays machine-editable

pr-gen-description and pr-open SHALL write the `## Depends on` section only
when the pull request is created and SHALL keep it byte-for-byte when a body is
regenerated. Before a body is applied they SHALL check it with the parser
`pr-restack-all` uses, and SHALL NOT apply a body whose section that parser
cannot find or edit.

#### Scenario: Regenerated body

- **WHEN** a pull request whose section carries a merge record is synced
- **THEN** the new body carries the same section

#### Scenario: Unparseable section

- **WHEN** a candidate body's `## Depends on` section cannot be parsed
- **THEN** the body is not applied

### Requirement: pr-restack-all restacks a chain with merges

pr-restack-all SHALL take a top pull request or a branch. For a pull request it
SHALL find the chain by walking each pull request's base to the open pull
request whose head is that branch, down to a base of `main`, and SHALL stop when
a pull request's last `## Depends on` entry is not the pull request below it.
For a branch it SHALL read the dependencies from its `Depends-on:` trailers. It
SHALL work in one fresh detached worktree under `./.tmp/` built from remote
refs, and SHALL NOT check out, create, or move a local branch. Bottom-up, for
each pull request it SHALL act only on the nearest predecessor P: when P is
open, merge P's head branch; when P is merged and P's merge commit is already in
the branch, do nothing; when P is merged otherwise, take HEAD as P's
`headRefOid` and MERGE as P's `mergeCommit.oid`, require
`refs/pull/<P>/head` to equal HEAD, merge MERGE into a detached copy of HEAD,
and merge that copy into the branch; when P is closed unmerged, stop. It SHALL
push without force and, after the push lands, replace the `- #<P>` entry with
`- #<P> — merged as <MERGE> (head <HEAD>), reconnected`. It SHALL NOT merge
`main` and SHALL stop on a merge conflict, printing the worktree path.

#### Scenario: Predecessor open

- **WHEN** a pull request's predecessor is open
- **THEN** the predecessor's head branch is merged in and pushed, and no record
  is written

#### Scenario: Predecessor merged

- **WHEN** a pull request's predecessor was squash-merged and its merge commit
  is not in the branch
- **THEN** the merge commit is merged into a copy of the predecessor's final
  head, the copy is merged into the branch, the branch is pushed without force,
  and the entry records the merge commit and head

#### Scenario: Two predecessors already merged

- **WHEN** X and X+1 have merged and X+2 is restacked
- **THEN** only X+1 is reconnected, and X+2 contains `main` up to X+1's merge
  commit and nothing later

#### Scenario: Rerun after a conflict

- **WHEN** a restack stopped on a conflict that was resolved and it runs again
- **THEN** pull requests already restacked are skipped

#### Scenario: Branch without a pull request

- **WHEN** pr-restack-all runs on a branch whose trailers name one merged and
  one open pull request
- **THEN** the merged one is reconnected and the branch is pushed

#### Scenario: Local branches

- **WHEN** pr-restack-all runs while another worktree has a chain branch checked
  out
- **THEN** no local branch or worktree other than its own is changed

### Requirement: pr-merge merges only into main

pr-merge SHALL refuse a pull request whose base is not `main` and SHALL NOT
pass `--admin`.

#### Scenario: Dependent pull request

- **WHEN** pr-merge is asked to merge a pull request based on another branch
- **THEN** it stops without merging

### Requirement: pr-merge-stack merges a chain bottom-up

pr-merge-stack SHALL take the top pull request and repeat until it has merged:
find the chain as pr-restack-all does, merge the bottom pull request through
pr-merge, then restack the rest with one `pr-restack-all` run of the top.

#### Scenario: Chain of three

- **WHEN** pr-merge-stack runs on the top of a chain of three open pull requests
- **THEN** each merges in order, with a restack after each of the first two

### Requirement: Merges into dependent branches are blocked

The repository SHALL have a ruleset on `refs/heads/iwe/**` requiring the status
check `base-is-main`, with the Write, Maintain, and Admin repository roles as
bypass actors, and no workflow SHALL report that check.

#### Scenario: Pull request into an iwe branch

- **WHEN** a pull request based on an `iwe/` branch is merged without `--admin`
- **THEN** GitHub refuses the merge

#### Scenario: Owner push

- **WHEN** a user with Write access pushes to an `iwe/` branch
- **THEN** the push is accepted
```

[PR merge conflicts](../spec/pr-merge-conflicts.md) — its Purpose drops the
`gh stack` path, and:

``` markdown
## MODIFIED Requirements

### Requirement: Feedback resolution resolves merge conflicts first

The pr-feedback-resolution skill SHALL read the PR's `mergeable`,
`mergeStateStatus`, and `baseRefName` before any feedback edit. When `mergeable`
is `CONFLICTING` or `mergeStateStatus` is `DIRTY`, it SHALL resolve the conflict
before collecting feedback by merging its `baseRefName` through `update-branch`
and pushing the merge. When `mergeable` is `UNKNOWN`, it SHALL re-poll before
deciding. A PR that is only `BEHIND` its base SHALL NOT be updated.

#### Scenario: Conflicted PR

- **WHEN** the PR's `mergeable` is `CONFLICTING` or `mergeStateStatus` is
  `DIRTY`
- **THEN** `update-branch` runs with `--base <baseRefName>` before any feedback
  edit
- **AND** the resolved merge is pushed before feedback is collected

#### Scenario: PR on another branch

- **WHEN** a conflicted PR targets a branch other than `main`
- **THEN** that branch, not `main`, is merged into the PR branch

#### Scenario: Mergeability not yet computed

- **WHEN** `mergeable` is `UNKNOWN`
- **THEN** the merge state is re-polled in bounded waits before deciding

#### Scenario: Branch behind without conflicts

- **WHEN** `mergeStateStatus` is `BEHIND` and the PR has no conflicts
- **THEN** the branch is not updated and feedback collection proceeds
```

## Depends on

[pre-commit replaces Super-Linter](20261031-pre-commit-replaces-super-linter.md)
— both edit `skills/pr-merge-stack/SKILL.md`. If its PR #611 is still open when
this work starts, cut the branch with `--depends-on 611`; otherwise from `main`.

## Verification

- `uv run pytest .agents/plugins/agentdev/tests` passes, including the new
  `test_depends_on.py`, `test_git_new_branch_depends_on.py`,
  `test_pr_restack_all.py`, and `test_check_depends_on.py`.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- `uv run pytest py_packages/agentdev_runtime` passes.
- `git grep -n -i -E "gh[ -]stack|stack-guard|AGENTDEV_GH_STACK"` finds nothing
  outside done plans, done bugs, `data/log.md`, and `data/releases/`.
- `iwe normalize` and `iwe schema validate` pass.
- `gh api repos/{owner}/{repo}/rulesets` shows the Task 13 ruleset with its
  three bypass roles.
- The pull request's CI is green.

## Out of scope

- IWE plans building on an unshipped dependency, and the ship gate on
  dependencies — a separate plan depending on this one.
- Consolidating the plugin's Python into one module tree.
- Converting a GitHub native stack still open when this ships.
- The `implement-agent-specs` coordinator workflow beyond what `pr-merge-stack`
  and `pr-restack-all` cover.

## Key references

Verified anchor points (line numbers as of 2026-11-01):

- `AGENTS.md:7` — the force-push exception for `gh stack`
- `AGENTS.md:12` — Best Practice 0 with the `rerere`/`pushDefault` exception
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:37` — stack detection
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:62` — `gh stack checkout`
  in the worktree setup
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:104` — guarded re-sync
  after a reformat commit
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:203` — guarded re-sync
  after a fix commit
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:231` — `gh stack merge`
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:90` — §2 Existing Pull
  Request Detection, create mode's `main` base
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:132` — §4 Branch Sync with
  the Base Branch
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:212` — §8 stack detection
  before the push
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:251` — §9 Create or Update
  the Pull Request
- `.agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md:1` — the native-stack
  skill to rewrite
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:29` — stack
  prerequisite
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:75` — Workflow 0:
  Refuse a Stack Branch
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:159` — stack
  troubleshooting row
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:60` — stack
  branch of the merge-conflict step
- `.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py:138`
  — `parse_arguments`
- `.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py:455`
  — `main`
- `.agents/plugins/agentdev/skills/git-new-branch/SKILL.md:49` — Bundled Script
  options
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md:160` — Step 8:
  Review and Validate
- `.agents/plugins/agentdev/skills/pr-sync/SKILL.md:8` — delegation to `pr-open`
- `.agents/plugins/agentdev/bin/result_codes.py:1` — shared result codes
- `.agents/plugins/agentdev/bin/skill_common.py:80` — `require_git_repo`
- `.agents/plugins/agentdev/README.md:136` — `gh-stack` catalog row
- `.agents/plugins/agentdev/README.md:145` — `pr-merge-stack` catalog row
- `.agents/plugins/agentdev/tests/test_gh_stack_guard.py:1` — guard tests
- `.prettierignore:14` — gh-stack exclusion
- `ansible/roles/github_cli/defaults/main.yml:2` — gh-stack pin block
- `ansible/roles/github_cli/tasks/main.yml:94` — gh-stack install tasks
- `docker/deploy/agentdev-deploy.Dockerfile:9` — gh-stack copy out of root's
  home
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py:104` —
  `register_user_tools`
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py:129` — its call
  in `create`
- `py_packages/agentdev_runtime/agentdev_runtime/settings.py:96` —
  `AGENTDEV_GH_STACK_DIR`
- `py_packages/agentdev_runtime/README.md:33` — `AGENTDEV_GH_STACK_DIR` row
- `scripts/refresh-pin-checksums.py:119` — gh-stack pin entry
- `scripts/tests/test_agent_runtime_acceptance.py:392` — `gh stack --help`
- `docs/knowledge/data/product.md:131` — force-push and git config rules
- `docs/knowledge/data/architecture.md:75` — stacked-prs and stack-push-guard
  links
- `docs/knowledge/data/features.md:74` — native stacked PRs link
- `docs/knowledge/data/backlog.md:53` — pr-merge-stack cleanup link
