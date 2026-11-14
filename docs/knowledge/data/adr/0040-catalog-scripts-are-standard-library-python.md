---
type: adr
stage: accepted
description: Catalog scripts are standard-library Python that share code through bin/ on sys.path, and only the macOS bootstrap is zsh.
---

# Catalog scripts are standard-library Python

Catalog scripts are standard-library Python on `#!/usr/bin/env python3`. They
share code through `bin/` on `sys.path`, because a plugin cache has no install
step. `Path(__file__)` gives the same result in a checkout and in a cache.
`bin/macos-bootstrap.zsh` is zsh, because it installs the `python3` that the
other scripts use. `/bin/zsh` is the one modern shell on each supported macOS.

## Considered Options

- A Python package installed into the plugin. Rejected: a plugin cache has no
  install step, so the package is not there when the scripts run.
- Bash wrappers around Python helpers. Rejected: the lint and the tests of each
  language see only half of one algorithm.
- Shell scripts that use `jq`, `awk`, and `sed`. Rejected: each tool is a host
  dependency that a consumer possibly does not have, and only a run of the full
  script tests the logic.

## Consequences

- The rule applies to each script in `bin/` and in `skills/*/agent-code/` of the
  agentdev plugin. A script can use `python3` and the tools that it runs, such
  as `git` and `gh`, and nothing that is installed for it.
- A skill never imports the code of a different skill. Code that two skills
  share goes into `bin/`.
- When a script gives a command line to a shell,
  `.agents/plugins/agentdev/bin/skill_common.py::bash_quote` quotes it as bash
  `printf %q` does. As a result, the shell reads the words that the script sent.
- A macOS host that runs agents without a Dev Container gets only the catalog.
  `curl` gets `.agents/plugins/agentdev/bin/macos-bootstrap.zsh` before the
  plugin is there, and it installs that `python3`. `/bin/bash` on macOS is
  version 3.2.
- `shellcheck` cannot read zsh, so the `shellcheck` hook does not check the
  bootstrap. The bootstrap is a command that a user runs, not a skill script, so
  it does not write a `RESULT=` line.
