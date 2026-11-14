---
type: adr
stage: accepted
description: A skill names its bundled code by a path relative to the skill under agent-code/, and ${CLAUDE_SKILL_DIR} appears only in allowed-tools.
---

# Bundled code is relative to the skill, under agent-code/

Each host tells the model that a relative path in a `SKILL.md` starts at the
directory of the skill. As a result, a skill body names its code as
`agent-code/<script>`. Only Claude Code replaces `${CLAUDE_SKILL_DIR}`, so it
stays in `allowed-tools`, which only Claude Code reads and which needs an
absolute path. `references/` keeps its name, because agents read its pages and
do not execute them.

## Considered Options

- `${CLAUDE_SKILL_DIR}` in skill bodies, with a replacement step for each host.
  Rejected: each host other than Claude Code needs its own step.
- Relative paths under the Agent Skills name `scripts/`. Rejected: a path can
  start at the working directory. Then it runs the script of the consumer with
  the same name, and nothing fails.

## Consequences

- A path in a script starts at the file of the script, never at the repository,
  because a repository path does not exist in the plugin cache.
- A skill script never imports the code of a different skill. Code that two
  skills share goes into the `bin/` directory of the plugin.
