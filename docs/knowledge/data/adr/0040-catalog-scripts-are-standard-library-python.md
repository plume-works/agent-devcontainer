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
