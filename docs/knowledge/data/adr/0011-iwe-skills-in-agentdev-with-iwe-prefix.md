---
type: adr
stage: accepted
description: The IWE workflow skills are in the agentdev catalog, and their names keep the iwe- prefix.
---

# The IWE workflow skills are in agentdev, with an iwe- prefix

The maintainer put the IWE workflow skills in the `agentdev` catalog, so that
only one catalog has versions and installs. As a result, `agentdev` ships a
workflow that needs an IWE graph. The names keep the `iwe-` prefix, because
`plan`, `ship`, and `verify` alone look like skills of the same kind as the
`pr-*` skills in the same directory.

## Considered Options

- A separate `iwe` plugin. Rejected: it is a second catalog to version and
  install.
- The skills in `.claude/skills/`. Rejected: each consumer then gets them
  outside the supported install path.
