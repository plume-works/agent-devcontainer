---
type: someday
description: Examine the superpowers@claude-plugins-official plugin as a replacement for, or a partner to, the iwe skills and the tdd skill of the agentdev catalog.
sources:
- resource: https://github.com/anthropics/claude-plugins-public
- resource: .agents/plugins/agentdev/skills/
---

# Examine the superpowers plugin with the iwe and tdd skills

The `superpowers@claude-plugins-official` plugin supplies skills for planning,
implementation, and test-driven development. These skills do the same work as
the `iwe-*` skills and the `tdd` skill of the agentdev catalog. When the two
sets of skills load together, their instructions conflict. Thus
`.claude/settings.json` does not enable the plugin.

Examine the plugin for two possible results:

- **Replacement.** A superpowers skill replaces an agentdev skill that does the
  same work.
- **Partner.** The two plugins load together, and each skill has a scope that
  does not overlap with a skill in the other plugin.

## Promotion criteria

Promote to a plan when a comparison of each superpowers skill with the agentdev
skill that does the same work exists. The comparison must give, for each pair,
the choice to keep, to replace, or to share, and the reason.
