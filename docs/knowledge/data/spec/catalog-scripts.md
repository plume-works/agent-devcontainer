---
type: spec
description: The language and import rules for every script the agentdev catalog ships under bin/ and skills/*/agent-code/ — standard-library-only Python that reaches the shared bin/ modules through a path resolved from its own file, never a sibling skill's code, and bash_quote for every command line handed to a shell — with bin/macos-bootstrap.zsh the one exception.
sources:
- resource: .agents/plugins/agentdev/bin/python_lint_check.py
- resource: .agents/plugins/agentdev/bin/result_codes.py
- resource: .agents/plugins/agentdev/bin/skill_common.py
- resource: .agents/plugins/agentdev/bin/pr_restack_all.py
- resource: .agents/plugins/agentdev/skills/extract-github-actions-logs/agent-code/parse-actions-url.py
- resource: .agents/plugins/agentdev/skills/skill-scripts/SKILL.md
- resource: .agents/plugins/agentdev/bin/macos-bootstrap.zsh
- resource: .agents/AGENTS.md
- resource: .pre-commit-config.yaml
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .agents/plugins/agentdev/skills/create-skill/SKILL.md
---

# Catalog scripts

## Purpose

Defines what a script shipped by the agentdev catalog may be written in and may
depend on. The catalog runs from the plugin cache of any consuming repository,
on whatever host runs the agent, so its scripts depend on `python3` and the
tools they drive and on nothing installed for them. The `RESULT=` output
contract the scripts follow belongs to the `skill-scripts` skill.

## Requirements

### Requirement: catalog scripts are standard-library Python

Every script under the agentdev plugin's `bin/` and `skills/*/agent-code/`,
except `bin/macos-bootstrap.zsh`, SHALL be Python started by
`#!/usr/bin/env python3` and SHALL import only the standard library, the
plugin's shared `bin/` modules, and modules beside it in its own `agent-code/`.
It SHALL depend on nothing installed for it beyond `python3` and the external
tools it drives, such as `git` and `gh`.

#### Scenario: a script needs a third-party parser

- **WHEN** a script needs a capability only a third-party package offers
- **THEN** the script implements it on the standard library instead of importing
  the package

## Rationale

### Standard-library Python reaching bin/ through sys.path

Catalog scripts are standard-library Python on `#!/usr/bin/env python3`, sharing
code through `bin/` on `sys.path`, because a plugin cache has no install step
and `Path(__file__)` resolves the same in a checkout and in a cache. The macOS
bootstrap is zsh because it provisions the `python3` every other script runs on,
and `/bin/zsh` is the one modern shell every supported macOS ships (its
`/bin/bash` is 3.2).

Rejected:

- **A Python package installed into the plugin.** A plugin cache has no install
  step, so the package would be absent exactly where the scripts run.
- **Bash wrappers around Python helpers.** One algorithm split across two
  languages is tested and linted as neither.
- **Shell scripts with `jq`, `awk`, and `sed` for the hard parts.** Each tool is
  a host dependency the consuming repository may lack, and the logic between
  them is untestable short of running the whole script.

### Bundled code is named relative to the skill, under agent-code/

Every host tells the model that a relative path in a `SKILL.md` resolves against
the skill's directory: Claude Code prints the skill's base directory, and the
OpenCode bridge appends a base-directory footer. `${CLAUDE_SKILL_DIR}` is a text
substitution only Claude Code performs, so it stays in `allowed-tools`, which
only Claude Code reads and whose permission patterns need an absolute path. The
directory is `agent-code/`, not the Agent Skills convention `scripts/`: a
relative `scripts/<script>` resolved against the working directory instead of
the skill can run a consuming repository's own same-named script rather than
fail. `references/` keeps its name because its pages are read, not executed.

Rejected:

- **Keeping `${CLAUDE_SKILL_DIR}` in skill bodies with per-host substitution.**
  Every host other than Claude Code would need its own substitution step.
- **Relative paths under the name `scripts/`.** A miss runs the consuming
  repository's script instead of failing.

### A terminating signal is named, then re-raised

`bin/result_codes.py` names a terminating signal in `RESULT=`, restores the
signal's default handler, and re-sends the signal to its own process, so a shell
caller observes a real signal death, a negative `returncode`, and an interrupted
pipeline stops as it would for any other program.

Rejected:

- **`sys.exit(128 + signum)`.** The caller sees a normal exit whose status only
  resembles a signal death.
