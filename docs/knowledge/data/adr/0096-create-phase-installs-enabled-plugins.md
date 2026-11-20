---
type: adr
stage: accepted
description: The create phase installs at user scope each plugin that the project settings enable from a marketplace other than the catalog root.
---

# The create phase installs the plugins that the project settings enable

An entry in `enabledPlugins` of `.claude/settings.json` does not install a
plugin. Claude Code installs it only after a user accepts the prompt that comes
when the user trusts the folder. Sessions in a Dev Container start from VS Code,
from Remote Control, or with no terminal, and no user accepts that prompt. Thus
the create phase runs `claude plugin install <plugin> --scope user` for each
enabled plugin from another marketplace. This is the decision of the maintainer.

## Consequences

- A failed installation gives a warning and does not stop the create phase.
- Each worktree session has the plugins, because the create phase installs them
  at user scope.
