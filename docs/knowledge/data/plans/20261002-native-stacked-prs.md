---
type: plan
created: 2026-10-02
description: Replace the manual main-targeted PR chain with GitHub native stacked pull requests — pin the gh-stack extension, vendor GitHub's gh-stack skill, allow lease-guarded force-pushes on stack branches only, merge every PR explicitly, and land stacks with gh stack merge.
generated:
  by: claude-code/opus-5-5
  at: 2026-10-02T23:17:48Z
sources:
- resource: https://docs.github.com/en/pull-requests/how-tos/stacked-pull-requests
- resource: https://github.com/github/gh-stack/tree/main/skills/gh-stack
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge-chain/SKILL.md
---

# Adopt GitHub native stacked pull requests

## Context

GitHub stacked pull requests (public preview) make a chain of dependent PRs a
first-class object: each PR targets the branch below it, every layer is held to
the rules and CI of the stack's base, `gh stack merge` lands any bottom-up
prefix as one all-or-nothing operation, and GitHub rebases the remaining layers
after each merge. Stacks reject auto-merge, and the synchronous merge endpoint
behind `gh pr merge` cannot merge a stacked PR.

`pr-merge-chain` emulates all of that by hand: every member targets `main`,
successors stay drafts behind a `## Dependencies` section, and a coordinator
worktree reconnects squashed history and pushes each successor between merges.
The native feature makes that procedure redundant.

`gh stack push`, `rebase`, and `sync` update branches with `--force-with-lease`,
and `gh stack init` enables `rerere` in the repository's git config. `AGENTS.md`
forbids git config changes, and the `pr-merge`, `update-branch`, and `pr-open`
skills forbid force-pushes; `AGENTS.md` itself has no force-push rule.

Decisions:

- `pr-merge` merges explicitly — never through auto-merge — once conflicts,
  checks, feedback, and reviews are resolved, for every PR.
- `AGENTS.md` gains a repository-wide never-force-push rule with one narrow
  exception: `--force-with-lease` is allowed only through `gh stack push`,
  `gh stack rebase`, and `gh stack sync`, only on branches of a GitHub stack;
  the repository-local `rerere.enabled` and `remote.pushDefault` that `gh stack`
  and the vendored skill's setup write are allowed. No other git config change
  is.
- GitHub's `gh-stack` skill is vendored unchanged, pinned to the same release as
  the `gh-stack` extension installed in the image, and a thin `pr-merge-stack`
  skill replaces `pr-merge-chain`.

## Approach

Layer responsibilities:

``` text
gh-stack (vendored, upstream bytes)   how to drive `gh stack` non-interactively
pr-merge-stack (ours)                 per-layer CI/review loop, then one stack merge
pr-merge (ours)                       one PR: monitor, remediate, explicit merge
pr-feedback-resolution / update-branch  stack-aware conflict and update routing
```

`pr-merge-stack` runs `pr-merge`'s monitoring and remediation loop on each layer
from the bottom up, stopping short of the merge, and lands the stack with
`gh stack merge <top> --yes --squash`. A remediation commit on a lower layer is
followed by `gh stack rebase --upstack` and `gh stack push`, because every layer
above it no longer contains its tip; `reformat.yml` commits on a lower layer are
handled the same way.

A spike on a scratch stack settles the facts the skills depend on before they
are written: the field that marks a PR as stacked, whether GitHub's post-merge
rebase re-triggers CI and the AI-review gate, and that the repository's
`required_linear_history` and squash-only settings accept a stack merge.

Rejected: keeping merge-only updates for stack branches. GitHub's own post-merge
rebase rewrites every remaining layer regardless, so a local merge-based copy
diverges after the first merge, and `update-branch` merging the rewritten remote
branch would resurrect pre-rebase commits. Writing our own `gh stack` driver
skill instead of vendoring was also rejected: the upstream skill already encodes
the non-interactive flags and exit-code recovery that an agent needs, and is
versioned with the extension.

## Implementation Steps

### Task 1: Make pr-merge merge explicitly only

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`,
`.agents/plugins/agentdev/README.md`

- [x] Remove the auto-merge path; disable an existing auto-merge request; squash
  merge explicitly after every completion criterion holds for the current head
  - **Evidence:** commit 29210c2

### Task 2: Run the stacked-PR spike

**Files:** none (scratch branches and PRs in this repository, closed afterwards)

- [ ] Record, from one scratch three-layer stack, all four answers: the REST
  `stack` object of a mid-stack PR; whether `gh pr merge --squash` is refused on
  the bottom PR; whether `gh stack merge <bottom> --yes --squash` passes the
  `main` ruleset; and whether the next layer's post-merge rebase re-runs
  `primary-checks.yml` and `ai-review-present`
  - **Evidence:** stack #259 (PRs #256, #257, #258): `gh pr merge 256 --squash`
    refused by GraphQL; `gh stack merge 256 --yes --squash` merged #256 as
    240ef41; #257's rebased head daacc26 re-ran Primary checks run 37291285494
    and AI Responder run 37291285250, whose `ai-review-present` passed on the
    pre-rebase review

### Task 3: Record the spike's results

**Files:** Create: `docs/knowledge/data/architecture/stacked-prs.md`; Modify:
`docs/knowledge/data/architecture.md`

- [x] Write the stacked-PR architecture doc: the stack-detection field, the
  merge command, the post-merge CI and review behavior, and the policy decision
  with its rejected alternatives
  - **Evidence:** `data/architecture/stacked-prs` linked from
    `data/architecture`, committed with this tick; `iwe schema validate` passes

### Task 4: Install the pinned gh-stack extension in the image

**Files:** Create: `ansible/roles/github_cli/defaults/main.yml`; Modify:
`ansible/roles/github_cli/tasks/main.yml`

- [x] Pin `github_cli_gh_stack_version` under a
  `# renovate: datasource=github-releases depName=github/gh-stack` comment and
  install it for `dev_user` with
  `gh extension install github/gh-stack --pin <version>`;
  `uv run ansible-lint ansible` and the playbook syntax check pass
  - **Evidence:** committed with this tick; `uv run ansible-lint ansible` and
    `uv run ansible-playbook --syntax-check ansible/playbooks/setup-dev.yml`
    exit 0; the install needs no token

### Task 5: Verify the extension in a built image

**Files:** none

- [ ] A local image build succeeds and `gh stack --help` runs inside it

### Task 6: Vendor the gh-stack skill

**Files:** Create: `.agents/plugins/agentdev/skills/gh-stack/SKILL.md`,
`.agents/plugins/agentdev/skills/gh-stack/references/commands.md`,
`.agents/plugins/agentdev/skills/gh-stack/references/stack-design.md`,
`.agents/plugins/agentdev/skills/gh-stack/references/troubleshooting.md`,
`.agents/plugins/agentdev/skills/gh-stack/LICENSE`; Modify:
`.agents/plugins/agentdev/README.md`, `.prettierignore` if Prettier rewrites the
vendored files

- [x] Copy `skills/gh-stack` and the upstream `LICENSE` from the
  `github/gh-stack` tag pinned in Task 4, byte for byte; `validate_agent_files`
  passes and no formatter rewrites them
  - **Evidence:** committed with this tick; `diff -r` against tag v0.2.0
    (d4ab7ab) differs only by `LICENSE`; `uv run validate_agent_files` 0 errors;
    pre-commit leaves the files unchanged under the `.prettierignore` entry
- [ ] Add a pytest that fails when the vendored skill's `metadata.version`
  differs from the pinned extension version, so a Renovate bump cannot leave the
  skill behind

### Task 7: State the stack-branch policy exception

**Files:** Modify: `AGENTS.md`, `docs/knowledge/data/product.md`

- [ ] Amend the git config rule to allow the repository-local `rerere.enabled`
  and `remote.pushDefault` that `gh stack` and the vendored skill's setup write,
  add a repository-wide rule — never force-push, except `gh stack push`,
  `rebase`, and `sync` with `--force-with-lease` on branches of a GitHub stack —
  to `AGENTS.md`, and mirror both in `product.md`'s `## Authoring rules`

### Task 8: Make update-branch and pr-open stack-aware

**Files:** Modify: `.agents/plugins/agentdev/skills/update-branch/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-open/SKILL.md`

- [ ] `update-branch` refuses a branch that belongs to a GitHub stack and points
  to `gh stack sync`; `pr-open`'s push step routes a stack branch to
  `gh stack push` instead of `push-branch.sh`

### Task 9: Route a conflicted stacked PR to a cascading rebase

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md`

- [ ] The merge-conflict step resolves a conflicted stacked PR with
  `gh stack rebase` and `gh stack push` instead of `update-branch`; a
  non-stacked PR keeps merging its `baseRefName`

### Task 10: Merge a stacked PR with gh stack merge in pr-merge

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [ ] For a stacked PR, `pr-merge` merges only the lowest unmerged layer, with
  `gh stack merge <pr> --yes --squash`, and pushes remediations through
  `gh stack rebase --upstack` and `gh stack push`; a higher layer is handed to
  `pr-merge-stack`

### Task 11: Create pr-merge-stack

**Files:** Create: `.agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md`;
Modify: `.agents/plugins/agentdev/README.md`

- [ ] Accept a PR or stack number, read the stack with `gh stack view --json`,
  run `pr-merge`'s loop on each unmerged layer bottom-up without merging,
  re-sync after any lower-layer change, then land the stack with one
  `gh stack merge <top> --yes --squash` and handle a merge that stops partway

### Task 12: Remove pr-merge-chain

**Files:** Delete: `.agents/plugins/agentdev/skills/pr-merge-chain/SKILL.md`;
Modify: `.agents/plugins/agentdev/README.md`

- [ ] Delete the skill and its README row; no file outside
  `docs/knowledge/data/plans/` still names it

### Task 13: Refresh the codebase map

**Files:** Modify:
`docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md`

- [ ] Run `/agentdev:iwe-map` in refresh mode so the skills map lists `gh-stack`
  and `pr-merge-stack` instead of `pr-merge-chain`

### Task 14: Merge a real stack with pr-merge-stack

**Files:** none

- [ ] Land a stack of at least two PRs in this repository through
  `/agentdev:pr-merge-stack`, with every layer's CI and AI review green before
  the single stack merge

## Spec changes

New spec `spec/stacked-prs`, linked from `data/spec.md`:

``` markdown
## ADDED Requirements

### Requirement: pr-merge merges explicitly

The pr-merge skill SHALL NOT enable auto-merge. It SHALL disable an existing
auto-merge request when it starts and SHALL merge with a squash only after
conflicts, checks, AI review, and review feedback are resolved for the current
head SHA.

#### Scenario: Auto-merge already enabled

- **WHEN** pr-merge starts on a PR whose `autoMergeRequest` is non-null
- **THEN** it disables auto-merge before monitoring
- **AND** reports that it did so

#### Scenario: Requirements met

- **WHEN** every completion criterion holds for the current head SHA
- **THEN** pr-merge squash merges the PR explicitly and confirms `MERGED`

### Requirement: Stacked PRs merge through gh stack merge

A PR that belongs to a GitHub stack SHALL be merged with
`gh stack merge <pr> --yes --squash`, never with `gh pr merge`. pr-merge SHALL
merge only the lowest unmerged layer of a stack; pr-merge-stack SHALL bring
every unmerged layer through CI and review bottom-up and land them with one
`gh stack merge` of the top PR.

#### Scenario: Lowest unmerged layer

- **WHEN** pr-merge is asked to merge the lowest unmerged PR of a stack
- **THEN** it merges that PR with `gh stack merge <pr> --yes --squash`

#### Scenario: Higher layer

- **WHEN** pr-merge is asked to merge a stacked PR with unmerged PRs below it
- **THEN** it hands the stack to pr-merge-stack instead of merging

#### Scenario: Whole stack

- **WHEN** pr-merge-stack has every unmerged layer green for CI and review
- **THEN** it runs one `gh stack merge <top> --yes --squash`

### Requirement: Force-pushes are limited to stack branches

Agent skills SHALL NOT force-push, except that `gh stack push`,
`gh stack rebase`, and `gh stack sync` MAY update branches of a GitHub stack
with `--force-with-lease`. The repository-local `rerere.enabled` and
`remote.pushDefault` written by `gh stack` or the vendored gh-stack skill's
setup are the only permitted git config changes.

#### Scenario: Branch outside a stack

- **WHEN** a skill must update a branch that belongs to no GitHub stack
- **THEN** it pushes without force

#### Scenario: Lower layer changed

- **WHEN** a commit lands on a lower layer of a stack
- **THEN** the layers above are updated with `gh stack rebase --upstack` and
  `gh stack push`

### Requirement: update-branch refuses stack branches

The update-branch skill SHALL refuse a branch that belongs to a GitHub stack and
SHALL direct the caller to `gh stack sync`.

#### Scenario: Stack branch

- **WHEN** update-branch runs on a branch of a GitHub stack
- **THEN** it stops without merging and names `gh stack sync`
```

[PR merge conflicts](../spec/pr-merge-conflicts.md):

``` markdown
## MODIFIED Requirements

### Requirement: Feedback resolution resolves merge conflicts first

The pr-feedback-resolution skill SHALL read the PR's `mergeable`,
`mergeStateStatus`, and `baseRefName` before any feedback edit. When `mergeable`
is `CONFLICTING` or `mergeStateStatus` is `DIRTY`, it SHALL resolve the conflict
before collecting feedback: a PR in a GitHub stack through `gh stack rebase` and
`gh stack push`, any other PR by merging its `baseRefName` through
`update-branch` and pushing the merge. When `mergeable` is `UNKNOWN`, it SHALL
re-poll before deciding. A PR that is only `BEHIND` its base SHALL NOT be
updated.

#### Scenario: Conflicted PR

- **WHEN** the PR's `mergeable` is `CONFLICTING` or `mergeStateStatus` is
  `DIRTY`
- **THEN** `update-branch` runs with `--base <baseRefName>` before any feedback
  edit
- **AND** the resolved merge is pushed before feedback is collected

#### Scenario: PR on another branch outside a stack

- **WHEN** a conflicted PR targets a branch other than `main` and belongs to no
  GitHub stack
- **THEN** that branch, not `main`, is merged into the PR branch

#### Scenario: Stacked PR

- **WHEN** a conflicted PR belongs to a GitHub stack
- **THEN** the conflict is resolved with `gh stack rebase` and the stack is
  pushed with `gh stack push`
- **AND** `update-branch` is not run

#### Scenario: Mergeability not yet computed

- **WHEN** `mergeable` is `UNKNOWN`
- **THEN** the merge state is re-polled in bounded waits before deciding

#### Scenario: Branch behind without conflicts

- **WHEN** `mergeStateStatus` is `BEHIND` and the PR has no conflicts
- **THEN** the branch is not updated and feedback collection proceeds
```

## Verification

- `uv run validate_agent_files` passes on every changed or added `SKILL.md`.
- `uv run pytest .agents/plugins/agentdev/tests` passes, including the
  vendored-version test from Task 6.
- `uv run ansible-lint ansible` and
  `uv run ansible-playbook --syntax-check ansible/playbooks/setup-dev.yml` pass.
- `grep -rn "pr-merge-chain" --exclude-dir=plans .agents docs AGENTS.md README.md`
  prints nothing.
- `diff -r` of the vendored skill against the pinned upstream tag shows only the
  added `LICENSE`.
- Tasks 5 and 14 are closed by their external evidence: the image build log and
  the merged stack's PR URLs.

## Out of scope

- Creating stacks from `git-new-branch` or `pr-open`, and opening one PR per
  plan as a stack from `iwe-implement-all`.
- Reducing duplicate CI runs across layers with
  `github.event.pull_request.stack` conditions.
- Cross-fork stacks, which GitHub does not support.
- Any git config change other than `rerere.enabled` and `remote.pushDefault`.
- Using the server-side **Rebase stack** button from an agent: it updates refs
  through GitHub, which `AGENTS.md` forbids.

## Key references

Verified anchor points (line numbers as of 2026-10-02):

- `AGENTS.md:5` — no GitHub API ref updates
- `AGENTS.md:10` — Best Practice 0, no git config changes
- `docs/knowledge/data/product.md:119` — authoring rule, no API ref updates
- `docs/knowledge/data/product.md:123` — authoring rule, no git config changes
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:61` — never force-push
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:93` — Disable Auto-Merge
  Once
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:198` — Final Squash Merge
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:204` —
  `gh pr merge <pr> --squash`
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:66` — stacked
  PR merges its real base
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:28` — merge-based
  update precondition
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:32` — never force-push
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:247` — never force-push in
  the push step
- `.agents/plugins/agentdev/skills/pr-merge-chain/SKILL.md:1` — skill to delete
- `.agents/plugins/agentdev/README.md:84` — pr-merge row
- `.agents/plugins/agentdev/README.md:85` — pr-merge-chain row
- `ansible/roles/github_cli/tasks/main.yml:32` — Install GitHub CLI
- `.github/workflows/reformat.yml:367` — git-auto-commit push to the PR head
- `.github/workflows/ai-responder.yml:19` — `pull_request` triggers, including
  `synchronize`
- `.github/workflows/ai-responder.yml:509` — `ai-review-present` gate job
- `docs/knowledge/data/spec/pr-merge-conflicts.md:40` — Scenario: Stacked PR
- `docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md:29` — skills
  map row naming pr-merge-chain
