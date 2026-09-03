---
name: create-skill
description: Create, update, or review repository skills in the agentdev plugin catalog with concise discovery descriptions, progressive disclosure, and validation. Use when adding or refining a SKILL.md, diagnosing discovery, or packaging a repeatable agent workflow.
---

# Create Repository Skills

Use a general skill-authoring guide when the host provides one. Invoke it first for craft —
degrees of freedom, progressive disclosure, description triggering, and forward-testing:

- **Codex**: `$skill-creator`, a system skill under `~/.codex/skills/.system/skill-creator/`.
- **Claude Code**: `/skill-creator:skill-creator`, from the official plugin marketplace.

If neither is available, do that work yourself. The catalog rules below override a general
guide wherever they disagree.

## Where the Skill Lives

Create or update skills under `.agents/plugins/agentdev/skills/<skill-name>/` and edit them
in place. Pass `--path .agents/plugins/agentdev/skills` when scaffolding. Never edit from a
copy or create a separate Codex copy. Use a personal skill directory only when the user
explicitly asks for a user-wide skill.

The catalog ships as a plugin through `claude plugin install` and `codex plugin add`. The
edited repository files are the deliverable; do not create a separate `.skill` archive.

For an existing skill, read its `SKILL.md` and every resource it references before editing.
Preserve its directory and frontmatter `name` unless the user asks for a rename.

Scratch — including anything a skill-creator writes for evals, review, or forward-tests —
goes in `./.tmp/` at the repo root. Never `$TMPDIR`, never `/tmp/`, and never a
`<skill-name>-workspace/` sibling inside the catalog, which the plugin would ship and the
validator would walk.

## Frontmatter Follows the Agent Skills Spec, and There Is No `agents/openai.yaml`

`name` and `description` are required. Beyond them, use only keys the open Agent
Skills Specification defines — `license`, `compatibility`, `allowed-tools`, and
`metadata` — plus the Claude Code vendor key `disable-model-invocation`; the
validator accepts exactly this set. Ship a key only when the skill needs it:
`allowed-tools` when a skill runs bundled scripts
(`Bash(${CLAUDE_SKILL_DIR}/scripts/*)`), `disable-model-invocation` to suppress
implicit invocation. Do not invent keys outside this set.

Do not add the `agents/openai.yaml` that Codex's guide recommends and its `init_skill.py`
generates; delete it if a scaffold created one. Its `interface` block duplicates per skill
what `.codex-plugin/plugin.json` already declares once for the whole catalog. Add it only
for something frontmatter genuinely cannot express — `policy.allow_implicit_invocation` to
suppress implicit invocation, `dependencies.tools` for a hard tool dependency, or
`interface.icon_*` for required assets — and include only the keys that requirement needs.

Two forces pull on the description. Claude's guide pushes toward eager triggering, which is
right for the skill's own domain: claim the phrasings a user would actually type. But this
catalog runs more than two dozen skills competing for adjacent requests, so where nearby
work belongs to a sibling, name the boundary in prose the way
`/agentdev:code-review-standards` hands commits off to `/agentdev:git-commit`.

## Nothing May Reference Outside the Plugin

A skill runs from the plugin cache of whatever repository enables it, so a link that climbs
out of the plugin root resolves against the wrong tree. Name per-repository files —
`AGENTS.md`, lint configuration, the pull request template — in prose instead, and name the
host guides by path in prose rather than linking them. Use `${CLAUDE_SKILL_DIR}/...` within
one skill and a namespaced invocation for a sibling. The validator enforces this across
`SKILL.md`, `references/` pages, and the plugin README.

Put general repository rules in `AGENTS.md`, not in a skill that repeats them on every
invocation. Add no README, changelog, or quick-reference file to a skill directory.

## Gates Before Done

1. `uv run validate_agent_files --recommend . --require-marketplace claude codex` passes.
2. Every bundled script follows `/agentdev:skill-scripts`, and its result and exit code are
   pinned by a test in the plugin's `tests/` resolved from the plugin root — a hand-run is
   not enough. Then `uv run pytest .agents/plugins/agentdev/tests`.
3. Findings from the host guide's validation or forward-test pass are applied, and anything
   that did not improve correctness, clarity, or efficiency is removed.
