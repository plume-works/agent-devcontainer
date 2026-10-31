---
type: codebase
description: The 41 skills the agentdev plugin ships, grouped by family, with the ones that bundle scripts or reference pages.
source: .agents/plugins/agentdev/skills
source_digest: sha256:3ef8770e353725bfcf6209c1b47583f044300b03668d219508c56059e48050d4
verified:
  by: claude-code/opus-5.5
  at: 2026-10-31T11:10:05Z
stale_after: 2027-01-29
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T11:10:05Z
sources:
- id: code
  resource: .agents/plugins/agentdev/skills
---

# Catalog skills

Each skill is a directory holding `SKILL.md` — frontmatter per the Agent Skills
specification plus Claude Code's `disable-model-invocation` — and optionally
`agent-code/` (bundled scripts), `references/`, and `assets/` (files the skill
copies out as output). A skill reaches its own files by a path relative to its
directory (`agent-code/<file>`), uses `${CLAUDE_SKILL_DIR}` only in
`allowed-tools`, and reaches a sibling through its namespaced name.

## Contains

[iwe-bootstrap skill](skills/iwe-bootstrap.md)

## Public surface

| Family                            | Count | Skills                                                                                                                                                                                                                                             |
| --------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Git and pull requests             | 14    | `git-commit`, `git-new-branch`, `git-merge-resolve`, `update-branch`, `gh-stack`, `pr-open`, `pr-sync`, `pr-gen-description`, `pr-review`, `pr-feedback-resolution`, `pr-eval-review-needed`, `pr-request-ai-review`, `pr-merge`, `pr-merge-stack` |
| Review, CI, and formatting        | 7     | `code-review-standards`, `exec-summary`, `extract-github-actions-logs`, `get-codeql-data`, `local-reformat`, `semantic-refactor-audit`, `sync-super-linter-tool-versions`                                                                          |
| Escalation and the catalog itself | 6     | `microvm-sandbox`, `remote-codespace-session`, `create-agent`, `create-skill`, `skill-scripts`, `template-consume`                                                                                                                                 |
| IWE knowledge-graph workflow      | 14    | `iwe-audit`, `iwe-bootstrap`, `iwe-branch-name`, `iwe-capture`, `iwe-explore`, `iwe-implement`, `iwe-implement-all`, `iwe-map`, `iwe-plan`, `iwe-setup`, `iwe-ship`, `iwe-ship-all`, `iwe-verify`, `iwe-weekly`                                    |

Skills with bundled scripts: `extract-github-actions-logs`, `git-commit`,
`gh-stack`, `git-new-branch`, `git-merge-resolve`, `iwe-bootstrap`,
`iwe-branch-name`, `iwe-capture`, `iwe-explore`, `iwe-map`, `iwe-plan`,
`iwe-verify`, `pr-gen-description`, `pr-open`, `pr-request-ai-review`,
`pr-review`, `remote-codespace-session`, `template-consume`, `update-branch`.
Skills with `references/` pages: `gh-stack`, `iwe-bootstrap`,
`semantic-refactor-audit`, `template-consume`. `iwe-bootstrap` is the one skill
with `assets/`: the blank IWE workspace it installs. `gh-stack`'s `SKILL.md` is
the repository's own; its `references/upstream/` pages and `LICENSE` are copied
unchanged from `github/gh-stack` at the release the image's `github_cli` role
installs.

## How it works

A `SKILL.md` is loaded into the conversation when the user invokes it or when
its description matches the request; seven IWE workflow skills (`iwe-plan`,
`iwe-implement`, `iwe-implement-all`, `iwe-ship`, `iwe-ship-all`, `iwe-setup`,
`iwe-weekly`) use `disable-model-invocation: true` to require explicit
invocation, and each pairs it with an `agents/openai.yaml` setting
`allow_implicit_invocation: false`, the gate Codex reads; `iwe-map` remains
model-invocable for workflow handoffs. Ship and Implement keep their rulebooks
in the `iwe-shipper` and `iwe-implementer` catalog agents: `iwe-ship` only
builds a conversation-free prompt and dispatches `iwe-shipper`, `iwe-implement`
follows `iwe-implementer` in place, the two `-all` coordinators dispatch one
agent per plan in dependency order with no conversation forwarded, and
`iwe-implement` and `iwe-implement-all` also run that rulebook's
`## Running the loop`, running Verify through `iwe-verify` after the tasks and
`iwe-revision-evaluator` on a drafted revision. `iwe-plan` follows the
`iwe-planner` agent in place, whose revise mode re-dispatches `iwe-shipper` when
a revision answers its blocker report. Verify keeps its rulebook in the
`iwe-verifier` agent: from a session `iwe-verify` dispatches it with a
conversation-free prompt, and inside `iwe-shipper` it has the Shipper follow
that rulebook in place. Both routes start and end at `iwe-verify`'s
`verify-cache.py`: `lookup` refuses a dirty worktree and returns the one saved
report for the plan under `.tmp/verify/` when its commit is `HEAD` and its
catalog digest, over the files of the catalog the script runs from, still
matches; `save` overwrites that report, recording the skill request and the
verifier prompt in its frontmatter, and refuses a `Needs decision` verdict.
Scripts are standard-library Python, import the [shared bin modules](bin.md),
and end every path with `RESULT=<NAME>` on stdout; the `SKILL.md` carries a
table keyed on those names. `iwe-capture` and `iwe-plan` each bundle a
`close-issue.py` that supplies only its wording and option name to the shared
`run_close` flow, so both report the same results. `iwe-map`'s
`stale-map-docs.py` fingerprints the tracked source behind every
`data/codebase/` doc, normalizing content that an `iwe-map.digest_ignore` rule
in an `.agent.metadata.json` designates machine-managed so an automerged pin
bump does not register as a change. The metadata files themselves stay out of
that fingerprint; a rule reaches a digest only as the pattern and replacement
that applied. Its `--explain` flag prints one `MASK` line per applied rule, and
it adds `BROKEN_METADATA` (exit 5) to the shared result vocabulary for metadata
it cannot read, compile, or apply to a masked text file.
`--replay [--since <date>]` bounds each verdict by the first-parent commit that
established the document's recorded digest; the date can add evidence but cannot
exclude that ancestry. A digest boundary is trusted only when that revision's
source computes to the recorded digest, with committed blobs read under the same
newline translation as the working tree. Replay uses NUL-separated Git paths,
inventories hidden values across every current masked file, and prints
`ABSORBED` or `MOVED` per commit or working-tree edit and file, then `RESTAMP`
with a new digest for a non-fresh doc the rules explain and `REFRESH` for the
rest. Metadata or masked-text failures found while collecting evidence become
document-scoped `BROKEN_METADATA`. Refresh mode records docs that quote old
values before shared masks and excludes them from re-stamping. The IWE family
runs against the [knowledge workspace](../../../docs/knowledge.md).
`template-consume` optionally initializes a consumer's knowledge by invoking
`iwe-bootstrap` — after removing a copied publisher workspace only when it is
byte-identical to the adopted ref — then hands onboarding to `iwe-setup` and
`iwe-map`; update mode tracks only the reusable knowledge support files, never
invokes bootstrap, and never replaces consumer-owned project memory. An optional
Expo profile edits files the consumer already has, enables the official Expo
plugin, and adds the Expo Bridge extension, Metro's port 8081 forwarded
silently, and an `eas-host` iOS build rule with an EAS cloud fallback; it adds
no tracked paths, so update mode reconciles it against the guide on every run.
An update that finds the consumer still pinned to `agent-desktop` while the
template pins `agentdev-devcontainer` first applies the guide's image-family
migration as one unit — pins, Compose, descriptor, copied scripts, and tracked
paths together — or, when declined, nothing. Its state is split three ways: the
`template-consume` section of the consumer root's `.agent.metadata.json` is the
only machine-parsed record of the adopted ref and the tracked paths —
`check-updates.py` reads nothing else, and a legacy `.agentdev-template.json` is
consolidated into it on the next update; `.agentdev-template-progress.md` is the
consumer-owned task and choice ledger that survives an interrupted setup; and
`data/template-adoption` summarizes the episode for a consumer that kept the
knowledge base.

`git-new-branch.py` and `git-commit.py` share the default-branch lookup in
`bin/git_default_branch.py`: the first falls back to it when `--base` does not
exist on the remote, the second refuses to commit on the branch it names and,
when a configured remote's default is unknown, refuses with `DEFAULT_UNKNOWN`.
`git-new-branch.py` stashes only with `--stash` and pops only the entry it
created, located by its commit. In worktree mode it puts the worktree under
`/workspaces` beside a main checkout that lives there, unless
`AGENTDEV_RUNTIME_MODE` is `standalone`, and otherwise under the checkout's
ignored `.worktrees/`.

`iwe-branch-name.py` names a plan's work branches
`iwe/<slug>/iter-<N>-<impl|ship>` and creates none; `iwe-implementer` and
`git-new-branch`'s naming table defer plan branch names to it. `next` takes one
more than the highest iteration of the slug, in either phase, among local
branches, `git ls-remote --heads`, and
`gh pr list --repo <remote URL> --state all`, so pull requests come from the
remote's own repository, and reports `GH_UNAVAILABLE` (6) rather than a number
when `gh` cannot answer. `plan-state` fetches the remote default branch,
resolved through `bin/git_default_branch.py`, and reads the plan from that tree,
never the working tree; it counts task checkboxes under
`## Implementation Steps` or `## Tasks`, and a plan with none is `incomplete`.
Without `--phase`, `next` maps a `complete` plan to `ship`, an `incomplete` one
to `impl`, and any other to the default branch.

`update-branch.py` brings in the branch's configured upstream — a fast-forward
when only behind, a merge when diverged — before it merges `<remote>/<base>`,
and reports it as `UPSTREAM_ACTION`. Both merges run `git-merge-resolve.py` as a
child process; a run stops at the first conflicted merge, `SOURCE` naming it,
and a rerun continues with the next.

`pr-open`'s `push-branch.py` is the push path for `pr-open`, `pr-sync`,
`update-branch`, `pr-feedback-resolution`, and `pr-merge`. Before it pushes, and
before it reports `ACTION=none` for a head the upstream already has, it runs
`iwe-map`'s `stale-map-docs.py` in a temporary detached worktree at the branch
head and prints `MAP_CHECK=<fresh|skipped|stale|failed|overridden>`; a stale map
exits `MAP_STALE` (6) and a check without a verdict `MAP_CHECK_FAILED` (7),
neither pushing. A commit without `.iwe/config.toml` is not checked, and
`--skip-map-check` bypasses the check. A branch of a GitHub stack is pushed with
the gh-stack skill's `stack-guard.py publish` instead, which runs no map check;
`update-branch` refuses such a branch, and `pr-merge` hands a stacked PR with
unmerged layers below it to `pr-merge-stack`, which lands the stack with one
`gh stack merge`.

## Depends on

The [bin helpers](bin.md) for scripts; the tools each skill names in prose.

## Invariants & gotchas

- Adding or changing a skill goes through `/agentdev:create-skill`, and a script
  through `/agentdev:skill-scripts`, whose gates are the validator and the
  [plugin tests](tests.md).
- A directory without `SKILL.md` is not a skill and is not counted.
- Scratch for evals and forward-tests goes to `./.tmp/` at the repository root,
  never beside the skill.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `.agents/plugins/agentdev/skills/create-skill/SKILL.md:1` — the authoring
  rules every skill follows
- `.agents/plugins/agentdev/skills/skill-scripts/SKILL.md:1` — the script
  contract
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:22` — the marker
  section that selects setup or update mode
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:61` — the progress
  document
- `.agents/plugins/agentdev/skills/template-consume/agent-code/check-updates.py:109`
  — `read_marker`, the only read of the marker section
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:997`
  — the `eas-host` iOS build rule: action order, Metro start, cloud fallback
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:841`
  — knowledge initialization through `iwe-bootstrap`
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:1112`
  — the image-family migration update mode applies first
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:198` — update
  mode's migration step
- `.agents/plugins/agentdev/skills/iwe-capture/agent-code/close-issue.py:33` —
  the shared issue-closing call, identical in `iwe-plan`
- `.agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.py:137`
  — `classify_upstream`, which picks the `UPSTREAM_ACTION`
- `.agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.py:116`
  — `merge_ref`, the child-process merge and its result mapping
- `.agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.py:537` —
  `Guard.begin`, the guard every stack push starts from
- `.agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py:132` —
  `check_map_freshness`, the push-time map gate
- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md:28` — the `iwe-shipper`
  dispatch
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:98` — the `iwe-verifier`
  dispatch
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:73` — the in-place route
  for `iwe-shipper`
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:16` — the saved-report
  lookup and save
- `.agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py:192` —
  `run_lookup`
- `.agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py:213` —
  `run_save`
- `.agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py:153` —
  `catalog_digest`
- `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md:13` — one Shipper per
  plan
- `.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md:12` — one
  Implementer per plan
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:14` — the in-place follow
  of `iwe-planner`
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md:164` — the Shipper
  re-dispatch after a revision
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:19` and
  `.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md:19` — the
  orchestrator running `## Running the loop`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:97` —
  `BROKEN_METADATA`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:280` —
  `MetadataResolver`, which walks a source's ancestors for masking rules, in the
  working tree or a revision's tree
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:555` —
  `Replayer`, the masked before/after comparison `--replay` runs
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:654` —
  `digest_commit`, the ancestry boundary for a replay verdict
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:673` —
  `replay_verdict`, the `RESTAMP`/`REFRESH` rule
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:369` —
  `source_digest_for_paths`
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py:283`
  — `read_plan_state`, the remote-default-branch plan read
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py:347`
  — `next_iteration`, the three sources of used iterations
