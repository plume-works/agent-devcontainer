---
type: bug
description: Codex shows agentdev skill bodies verbatim and never defines CLAUDE_SKILL_DIR, so every bundled-script step written as ${CLAUDE_SKILL_DIR}/scripts/... resolves to /scripts/... unless the model repairs the path itself.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-02T18:00:00Z
sources:
- resource: .agents/AGENTS.md
- resource: .agents/plugins/agentdev/skills
- resource: https://github.com/openai/codex/blob/444da31/codex-rs/ext/skills/src/fragments.rs
- resource: https://github.com/openai/codex/blob/444da31/codex-rs/ext/skills/src/catalog_prompt.rs
- resource: https://github.com/openai/codex/blob/444da31/codex-rs/hooks/src/engine/discovery.rs
stage: done
---

# Bug: Codex leaves `${CLAUDE_SKILL_DIR}` unresolved in agentdev skills

## Symptom

`.agents/AGENTS.md` requires a skill to reach its own files through
`${CLAUDE_SKILL_DIR}/...`, and 30 lines in the bodies of 16 agentdev `SKILL.md`
files name a bundled script that way, for example
`${CLAUDE_SKILL_DIR}/scripts/git-commit.sh -- -m "<subject>"`. Claude Code
replaces the variable with the skill's directory before the model sees the text.
Codex does not, so the agent receives the literal variable, and a shell that
runs the step as written expands it to empty and executes
`/scripts/git-commit.sh`, which does not exist.

The `allowed-tools` lines that also use the variable are read only by Claude
Code and are unaffected.

## Reproduction

Established from Codex source (`openai/codex` at `444da31`; the image ships
`@openai/codex` 0.159.2), not yet from a live run:

1. Codex wraps a selected skill as
   `<skill><name>…</name><path>…/SKILL.md</path>{contents}</skill>`, with the
   `SKILL.md` contents unchanged
   (`codex-rs/ext/skills/src/fragments.rs:92-107`).
2. `CLAUDE_SKILL_DIR` occurs nowhere in `codex-rs` outside tests. The only
   Claude-named variables Codex sets are `CLAUDE_PLUGIN_ROOT` and
   `CLAUDE_PLUGIN_DATA`, and only in the environment of plugin hooks
   (`codex-rs/hooks/src/engine/discovery.rs:265-270`).
3. Codex's skill instructions tell the model to resolve paths such as
   `scripts/foo.py` against the directory holding `SKILL.md`
   (`codex-rs/ext/skills/src/catalog_prompt.rs:29`); they say nothing about
   `${CLAUDE_SKILL_DIR}`.

A live run settles it: in Codex with the agentdev plugin enabled, invoke
`$agentdev:git-commit` and inspect the first shell command the agent issues.

## Root cause

The catalog's path convention is a Claude Code text substitution, and the Codex
plugin reuses the same skill bodies without any equivalent. A step works in
Codex only when the model notices the unresolved variable and rebuilds the path
from `<path>`.

## Fix

A skill references its own bundled code as `agent-code/<file>`, relative to the
skill directory, which Claude Code, Codex, and OpenCode all tell the model to
resolve against that directory. `${CLAUDE_SKILL_DIR}` survives only in the
Claude-only `allowed-tools` field. The directory is named `agent-code/` rather
than `scripts/` so that a path misresolved against the working directory cannot
run a consuming repository's own `scripts/`. The rule is in `.agents/AGENTS.md`;
the change shipped through
[Reference bundled skill code by skill-relative agent-code paths](../plans/20261001-skill-relative-agent-code.md).

## Key references

Verified anchor points (line numbers as of 2026-10-01):

- `.agents/AGENTS.md:33-35` — rule requiring `${CLAUDE_SKILL_DIR}/...` for a
  path inside a skill
- `.agents/plugins/agentdev/skills/git-commit/SKILL.md:33-34` — bundled-script
  steps written with the variable
- `.agents/plugins/agentdev/skills/git-commit/SKILL.md:4` — Claude-only
  `allowed-tools` use, unaffected
