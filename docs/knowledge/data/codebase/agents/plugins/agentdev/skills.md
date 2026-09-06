---
type: codebase
description: The 36 skills the agentdev plugin ships, grouped by family, with the ones that bundle scripts or reference pages.
source: .agents/plugins/agentdev/skills
source_digest: sha256:91520236b4a57e3c8f119ed79167538951496ee0a1c0279886bd7f5c95490b96
verified:
  by: codex/gpt-5
  at: 2026-09-06T19:05:00Z
stale_after: 2026-12-05
generated:
  by: codex/gpt-5
  at: 2026-09-06T19:05:00Z
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

| Family                            | Count | Skills                                                                                                                                                                                                                                           |
| --------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Git and pull requests             | 13    | `git-commit`, `git-merge-resolve`, `update-branch`, `pr-open`, `pr-sync`, `pr-gen-description`, `pr-review`, `pr-feedback-resolution`, `pr-eval-review-needed`, `pr-request-ai-review`, `pr-discover-ai-responder`, `pr-merge`, `pr-merge-chain` |
| Review, CI, and formatting        | 6     | `code-review-standards`, `extract-github-actions-logs`, `get-codeql-data`, `local-reformat`, `semantic-refactor-audit`, `sync-super-linter-tool-versions`                                                                                        |
| Escalation and the catalog itself | 6     | `microvm-sandbox`, `remote-codespace-session`, `create-agent`, `create-skill`, `skill-scripts`, `template-consume`                                                                                                                               |
| IWE knowledge-graph workflow      | 11    | `iwe-audit`, `iwe-explore`, `iwe-implement`, `iwe-implement-all`, `iwe-map`, `iwe-plan`, `iwe-setup`, `iwe-ship`, `iwe-ship-all`, `iwe-verify`, `iwe-weekly`                                                                                     |

Skills with bundled scripts: `extract-github-actions-logs`, `git-merge-resolve`,
`iwe-explore`, `iwe-map`, `iwe-plan`, `pr-discover-ai-responder`,
`pr-gen-description`, `pr-open`, `pr-review`, `remote-codespace-session`,
`template-consume`, `update-branch`. Skills with `references/` pages:
`semantic-refactor-audit`, `template-consume`.

## How it works

A `SKILL.md` is loaded into the conversation when the user invokes it or when
its description matches the request; `disable-model-invocation: true` limits a
skill to explicit invocation. Scripts are bash or Python, pull in the matching
[result-code helpers](bin.md), and end every path with `RESULT=<NAME>` on
stdout; the `SKILL.md` carries a table keyed on those names. `iwe-map`'s
`stale-map-docs.py` is the Python case: it fingerprints the tracked source
behind every `data/codebase/` doc, normalizing content that an
`iwe-map.digest_ignore` rule in an `.agent.metadata.json` designates
machine-managed so an automerged pin bump does not register as a change. Its
`--explain` flag prints one `MASK` line per applied rule, and it adds
`BROKEN_METADATA` (exit 5) to the shared result vocabulary for metadata it
cannot read, compile, or apply to a masked text file. The IWE family runs
against the [knowledge workspace](../../../docs/knowledge.md).
`template-consume` optionally copies the repository's IWE seed into a consumer,
then hands onboarding to `iwe-setup` and `iwe-map`; update mode tracks only the
reusable knowledge scaffold and never replaces consumer-owned project memory.
Its state is split three ways: the `template-consume` section of the consumer
root's `.agent.metadata.json` is the only machine-parsed record of the adopted
ref and the tracked paths — `check-updates.sh` reads nothing else, and a legacy
`.agentdev-template.json` is consolidated into it on the next update;
`.agentdev-template-progress.md` is the consumer-owned task and choice ledger
that survives an interrupted setup; and `data/template-adoption` summarizes the
episode for a consumer that kept the knowledge base.

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

Verified anchor points (line numbers as of 2026-09-06):

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
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:62` —
  `BROKEN_METADATA`
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:228` —
  `MetadataResolver`, which walks a source's ancestors for masking rules
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:289` —
  `source_digest_for_paths`
