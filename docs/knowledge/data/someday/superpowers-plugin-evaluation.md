---
type: someday
description: Examine the superpowers@claude-plugins-official plugin as a replacement for the iwe skills and the tdd skill of the agentdev catalog, or as an addition to them.
sources:
- resource: https://github.com/anthropics/claude-plugins-public
- resource: .agents/plugins/agentdev/skills/
---

# Examine the superpowers plugin with the iwe and tdd skills

The `superpowers@claude-plugins-official` plugin supplies skills that make
plans, implement them, and do test-driven development. These skills do the same
work as the `iwe-*` skills and the `tdd` skill of the agentdev catalog. When the
two sets of skills load together, their instructions do not agree. Thus
`.claude/settings.json` does not enable the plugin.

Examine the plugin for two possible results:

- **Replacement.** A superpowers skill replaces an agentdev skill that does the
  same work.
- **Addition.** The two plugins load together, and each skill has a scope that
  does not overlap with a skill in the other plugin.

## Promotion criteria

Promote this idea to a plan when you have a comparison of each superpowers skill
with its agentdev skill. The comparison must give, for each pair, the choice to
keep, to replace, or to share, and the reason.
