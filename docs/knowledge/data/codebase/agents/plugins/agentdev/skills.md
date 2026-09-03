---
type: codebase
description: The 36 skills the agentdev plugin ships, grouped by family, with the ones that bundle scripts or reference pages.
source: .agents/plugins/agentdev/skills
commit: eb60f60450c6009b076bc51993b49a924653eaa4
verified:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:12:49Z
stale_after: 2026-12-02
generated:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:12:49Z
sources:
- id: code
  resource: .agents/plugins/agentdev/skills
  title: the code this map describes, read at commit 37fcab8
---

# Catalog skills

Each skill is a directory holding `SKILL.md` — frontmatter per the Agent Skills
specification plus Claude Code's `disable-model-invocation` — and optionally
`scripts/` and `references/`. A skill reaches its own files through
`${CLAUDE_SKILL_DIR}` and a sibling through its namespaced name.

## Public surface

| Family                            | Count | Skills                                                                                                                                                                                                                                           |
| --------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Git and pull requests             | 13    | `git-commit`, `git-merge-resolve`, `update-branch`, `pr-open`, `pr-sync`, `pr-gen-description`, `pr-review`, `pr-feedback-resolution`, `pr-eval-review-needed`, `pr-request-ai-review`, `pr-discover-ai-responder`, `pr-merge`, `pr-merge-chain` |
| Review, CI, and formatting        | 6     | `code-review-standards`, `extract-github-actions-logs`, `get-codeql-data`, `local-reformat`, `semantic-refactor-audit`, `sync-super-linter-tool-versions`                                                                                        |
| Escalation and the catalog itself | 6     | `microvm-sandbox`, `remote-codespace-session`, `create-agent`, `create-skill`, `skill-scripts`, `template-consume`                                                                                                                               |
| IWE knowledge-graph workflow      | 11    | `iwe-audit`, `iwe-explore`, `iwe-implement`, `iwe-implement-all`, `iwe-map`, `iwe-plan`, `iwe-setup`, `iwe-ship`, `iwe-ship-all`, `iwe-verify`, `iwe-weekly`                                                                                     |

Skills with bundled scripts: `extract-github-actions-logs`, `git-merge-resolve`,
`iwe-explore`, `iwe-map`, `iwe-plan`, `pr-discover-ai-responder`,
`pr-gen-description`, `pr-open`, `pr-open`, `pr-review`,
`remote-codespace-session`, `remote-codespace-session`,
`remote-codespace-session`, `remote-codespace-session`, `template-consume`,
`update-branch`. Skills with `references/` pages: `semantic-refactor-audit`,
`template-consume`.

## How it works

A `SKILL.md` is loaded into the conversation when the user invokes it or when
its description matches the request; `disable-model-invocation: true` limits a
skill to explicit invocation. Scripts source the shared
[result-code helpers](bin.md) and end every path with `RESULT=<NAME>` on stdout,
and the `SKILL.md` carries a table keyed on those names. The IWE family runs
against the [knowledge workspace](../../../docs/knowledge.md).

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

Verified anchor points (line numbers as of 2026-09-03):

- `.agents/plugins/agentdev/skills/create-skill/SKILL.md:1` — the authoring
  rules every skill follows
- `.agents/plugins/agentdev/skills/skill-scripts/SKILL.md:1` — the script
  contract
