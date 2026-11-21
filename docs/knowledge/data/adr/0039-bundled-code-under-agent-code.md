---
type: adr
stage: accepted
---

# Bundled code is relative to the skill, under agent-code/

Every host tells the model that a relative path in a `SKILL.md` resolves against
the skill's directory: Claude Code prints the skill's base directory, and the
OpenCode bridge appends a base-directory footer. A skill body therefore names
its code as `agent-code/<script>`. `${CLAUDE_SKILL_DIR}` is a text substitution
that only Claude Code performs, so it stays in `allowed-tools`, which only
Claude Code reads and whose permission patterns need an absolute path. The
directory is `agent-code/`, not the Agent Skills convention `scripts/`.
`references/` keeps its name, because its pages are read, not executed.

## Considered Options

- `${CLAUDE_SKILL_DIR}` in skill bodies, with a replacement step for each host.
  Rejected: each host other than Claude Code needs its own step.
- Relative paths under the Agent Skills name `scripts/`. Rejected: a relative
  `scripts/<script>` resolved against the working directory instead of the skill
  can run the consumer's own same-named script rather than fail.

## Consequences

- A path in a script resolves from the script's own file, never from the
  repository, because a repository path does not exist in the plugin cache, the
  copy of the plugin that the harness installs in the home directory.
