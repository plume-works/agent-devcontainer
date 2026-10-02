---
type: codebase
description: The 38 skills the agentdev plugin ships, grouped by family, with the ones that bundle scripts or reference pages.
source: .agents/plugins/agentdev/skills
source_digest: sha256:07fe84b03c9e825f1875c956d0b8880acaa9ded6e2600a270f9d348117c77351
verified:
  by: claude-code/opus-5.5
  at: 2026-10-02T14:10:00Z
stale_after: 2026-12-31
generated:
  by: claude-code/opus-5.5
  at: 2026-10-02T14:10:00Z
sources:
- id: code
  resource: .agents/plugins/agentdev/skills
---

# Catalog skills

Each skill is a directory holding `SKILL.md` — frontmatter per the Agent Skills
specification plus Claude Code's `disable-model-invocation` — and optionally
`scripts/` and `references/`. A skill reaches its own files through
`${CLAUDE_SKILL_DIR}` and a sibling through its namespaced name.

## Public surface

| Family                            | Count | Skills                                                                                                                                                                                                                                                             |
| --------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Git and pull requests             | 14    | `git-commit`, `git-new-branch`, `git-merge-resolve`, `update-branch`, `pr-open`, `pr-sync`, `pr-gen-description`, `pr-review`, `pr-feedback-resolution`, `pr-eval-review-needed`, `pr-request-ai-review`, `pr-discover-ai-responder`, `pr-merge`, `pr-merge-chain` |
| Review, CI, and formatting        | 6     | `code-review-standards`, `extract-github-actions-logs`, `get-codeql-data`, `local-reformat`, `semantic-refactor-audit`, `sync-super-linter-tool-versions`                                                                                                          |
| Escalation and the catalog itself | 6     | `microvm-sandbox`, `remote-codespace-session`, `create-agent`, `create-skill`, `skill-scripts`, `template-consume`                                                                                                                                                 |
| IWE knowledge-graph workflow      | 12    | `iwe-audit`, `iwe-capture`, `iwe-explore`, `iwe-implement`, `iwe-implement-all`, `iwe-map`, `iwe-plan`, `iwe-setup`, `iwe-ship`, `iwe-ship-all`, `iwe-verify`, `iwe-weekly`                                                                                        |

Skills with bundled scripts: `extract-github-actions-logs`, `git-commit`,
`git-new-branch`, `git-merge-resolve`, `iwe-capture`, `iwe-explore`, `iwe-map`,
`iwe-plan`, `pr-discover-ai-responder`, `pr-gen-description`, `pr-open`,
`pr-review`, `remote-codespace-session`, `template-consume`, `update-branch`.
Skills with `references/` pages: `semantic-refactor-audit`, `template-consume`.

## How it works

A `SKILL.md` is loaded into the conversation when the user invokes it or when
its description matches the request; five IWE workflow skills use
`disable-model-invocation: true` to require explicit invocation, while `iwe-map`
remains model-invocable for workflow handoffs. Scripts are bash or Python, pull
in the matching [result-code helpers](bin.md), and end every path with
`RESULT=<NAME>` on stdout; the `SKILL.md` carries a table keyed on those names.
`iwe-capture` and `iwe-plan` each bundle a `close-issue.sh` that parses its
arguments and delegates the view-then-close step to the shared
`close_issue_with_comment` helper, so both report the same results. `iwe-map`'s
`stale-map-docs.py` is the Python case: it fingerprints the tracked source
behind every `data/codebase/` doc, normalizing content that an
`iwe-map.digest_ignore` rule in an `.agent.metadata.json` designates
machine-managed so an automerged pin bump does not register as a change. The
metadata files themselves stay out of that fingerprint; a rule reaches a digest
only as the pattern and replacement that applied. Its `--explain` flag prints
one `MASK` line per applied rule, and it adds `BROKEN_METADATA` (exit 5) to the
shared result vocabulary for metadata it cannot read, compile, or apply to a
masked text file. The IWE family runs against the
[knowledge workspace](../../../docs/knowledge.md). `template-consume` optionally
copies the repository's IWE seed into a consumer, then hands onboarding to
`iwe-setup` and `iwe-map`; update mode tracks only the reusable knowledge
scaffold and never replaces consumer-owned project memory. Its state is split
three ways: the `template-consume` section of the consumer root's
`.agent.metadata.json` is the only machine-parsed record of the adopted ref and
the tracked paths — `check-updates.sh` reads nothing else, and a legacy
`.agentdev-template.json` is consolidated into it on the next update;
`.agentdev-template-progress.md` is the consumer-owned task and choice ledger
that survives an interrupted setup; and `data/template-adoption` summarizes the
episode for a consumer that kept the knowledge base.

`git-new-branch.sh` and `git-commit.sh` share the default-branch lookup in
`bin/git-default-branch.sh`: the first falls back to it when `--base` does not
exist on the remote, the second refuses to commit on the branch it names and,
when a configured remote's default is unknown, refuses with `DEFAULT_UNKNOWN`.
`git-new-branch.sh` stashes only with `--stash` and pops only the entry it
created, located by its commit.

`pr-open`'s `push-branch.sh` is the push path for `pr-open`, `pr-sync`,
`update-branch`, `pr-feedback-resolution`, and `pr-merge`. Before it pushes, and
before it reports `ACTION=none` for a head the upstream already has, it runs
`iwe-map`'s `stale-map-docs.py` in a temporary detached worktree at the branch
head and prints `MAP_CHECK=<fresh|skipped|stale|failed|overridden>`; a stale map
exits `MAP_STALE` (6) and a check without a verdict `MAP_CHECK_FAILED` (7),
neither pushing. A commit without `.iwe/config.toml` is not checked, and
`--skip-map-check` bypasses the check.

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

Verified anchor points (line numbers as of 2026-10-02):

- `.agents/plugins/agentdev/skills/create-skill/SKILL.md:1` — the authoring
  rules every skill follows
- `.agents/plugins/agentdev/skills/skill-scripts/SKILL.md:1` — the script
  contract
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:22` — the marker
  section that selects setup or update mode
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:61` — the progress
  document
- `.agents/plugins/agentdev/skills/template-consume/scripts/check-updates.sh:124`
  — the only read of the marker section
- `.agents/plugins/agentdev/skills/iwe-capture/scripts/close-issue.sh:109` — the
  shared issue-closing call, identical in `iwe-plan`
- `.agents/plugins/agentdev/skills/pr-open/scripts/push-branch.sh:87` —
  `check_map_freshness`, the push-time map gate
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:74` —
  `BROKEN_METADATA`
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:230` —
  `MetadataResolver`, which walks a source's ancestors for masking rules
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:291` —
  `source_digest_for_paths`
