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

#### Scenario: a script runs from a consuming repository's plugin cache

- **WHEN** a skill script runs on a host where no project environment exists
- **THEN** every import resolves from the standard library or the plugin itself

#### Scenario: a script needs a third-party parser

- **WHEN** a script needs a capability only a third-party package offers
- **THEN** the script implements it on the standard library instead of importing
  the package

### Requirement: scripts reach bin/ through a path resolved from their own file

A skill script SHALL reach the plugin's shared modules by inserting the `bin/`
directory, resolved from its own file location
(`Path(__file__).resolve().parents[3] / 'bin'`), into `sys.path`, and a `bin/`
script SHALL insert its own directory. No script SHALL resolve a path relative
to this repository. Code two skills share SHALL live in `bin/`; a skill SHALL
NOT import a sibling skill's code.

#### Scenario: the plugin is installed into a cache

- **WHEN** a skill script runs from the plugin cache rather than this checkout
- **THEN** it imports `result_codes` and `skill_common` from the cache's own
  `bin/`

#### Scenario: two skills need the same helper

- **WHEN** a second skill needs code one skill's `agent-code/` holds
- **THEN** the code moves to `bin/`, and neither skill imports from the other's
  directory

### Requirement: command lines handed to a shell are quoted by bash_quote

A catalog script that prints or builds a command line a shell will re-read SHALL
quote each word with `skill_common.bash_quote`, which reproduces bash's
`printf %q`.

#### Scenario: a printed command carries a shell metacharacter

- **WHEN** `parse-actions-url.py` prints a `gh` command or a `KEY=value` line
  whose value holds a space or a metacharacter
- **THEN** the shell that reads the line sees the word the script meant

### Requirement: the macOS bootstrap is the one zsh script

`bin/macos-bootstrap.zsh` SHALL be the only catalog script that is not Python.
It is a user-run command, not a skill script, and SHALL NOT follow the `RESULT=`
contract. The `shellcheck` pre-commit hook SHALL exclude it. Its behaviour
belongs to `macos-native-bootstrap`.

#### Scenario: the pre-commit shellcheck hook runs on the catalog

- **WHEN** the `shellcheck` hook runs over every file
- **THEN** it does not check `bin/macos-bootstrap.zsh`

### Requirement: the Python lint check finds ruff without installing anything

`bin/python_lint_check.py` SHALL run ruff's format check and then its lint check
on the targets it is given, or on the repository root when given none. It SHALL
take ruff from the repository's uv project through `uv run --no-sync`, else from
an executable `.venv/bin/ruff` in the repository, else from `PATH`, and SHALL
exit non-zero, telling the user to run `uv sync`, when none of the three has it.
It SHALL never sync or install a package.

#### Scenario: a uv project carries ruff

- **WHEN** the check runs in a repository whose uv project provides ruff
- **THEN** it runs that ruff through `uv run --no-sync`, and changes no
  installed package even when `pyproject.toml` has unsynced edits

#### Scenario: no ruff anywhere

- **WHEN** neither uv, an in-tree `.venv`, nor `PATH` provides ruff
- **THEN** the check exits non-zero and names `uv sync` as the fix

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
