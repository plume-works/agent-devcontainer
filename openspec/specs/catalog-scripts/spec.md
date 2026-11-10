# Catalog scripts Specification

## Purpose

Defines the language and dependencies of the scripts the agentdev catalog
ships, which run from any consuming repository's plugin cache on a host that
installs nothing for them.

## Requirements

### Requirement: catalog scripts are standard-library Python

Every script under the agentdev plugin's `bin/` and `skills/*/agent-code/`,
except `bin/macos-bootstrap.zsh`, SHALL be Python on `#!/usr/bin/env python3`
that imports only the standard library and the shared modules in `bin/`. A
script SHALL reach `bin/` by inserting it into `sys.path` resolved from its own
file location, never from a repository-relative path, and SHALL NOT import a
sibling skill's code; code two skills share SHALL live in `bin/`. A command line
a script hands to a shell SHALL be quoted with `skill_common.bash_quote`, which
reproduces bash's `printf %q`.

#### Scenario: a script runs from a consumer's plugin cache

- **WHEN** a skill script runs from the plugin cache of a repository that has no
  `uv` environment
- **THEN** it imports and runs with only `python3` and the tools it drives

#### Scenario: two skills need the same helper

- **WHEN** a helper is needed by scripts of two skills
- **THEN** it lives in `bin/`, and neither skill imports the other's
  `agent-code/`

### Requirement: the macOS bootstrap is zsh and outside shellcheck

`bin/macos-bootstrap.zsh` SHALL be a zsh script, run by `/bin/zsh`, and SHALL be
excluded from the `shellcheck` hook. It is a user-run command and SHALL NOT
follow the `RESULT=` output contract.

#### Scenario: pre-commit lints the catalog

- **WHEN** the `shellcheck` hook runs over every file
- **THEN** it skips `bin/macos-bootstrap.zsh`

## Rationale

### Python on the standard library, reached through sys.path

The catalog ships in the plugin cache of whatever repository enables it and runs
on whatever host runs the agent, where this repository's `uv` environment does
not exist, so a script may depend on `python3` and the tools it drives and on
nothing installed for it. `Path(__file__)` resolves the same in a checkout and a
cache, where a repository-relative path resolves nowhere. The macOS bootstrap is
the exception because it provisions that `python3` on a stock macOS host, fetched
with `curl` before the plugin exists; `/bin/zsh` is the one modern shell every
supported macOS ships, and its `/bin/bash` is 3.2. The output contract scripts
follow is the `skill-scripts` skill's.

Rejected:

- **A Python package installed into the plugin.** A plugin cache has no install
  step.
- **Bash wrappers around Python helpers.** One algorithm in two languages is
  tested and linted as neither.
- **Shell scripts with `jq`, `awk`, and `sed`.** Each is a host dependency, and
  the logic between them is untestable short of running the whole script.
