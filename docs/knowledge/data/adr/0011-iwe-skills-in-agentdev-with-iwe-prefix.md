---
type: adr
stage: accepted
description: The IWE workflow skills are in the agentdev catalog, and their names keep the iwe- prefix.
---

# The IWE workflow skills are in agentdev, with an iwe- prefix

The maintainer put the IWE workflow skills in the `agentdev` catalog, so that
the user installs only one catalog, with one version. As a result, `agentdev`
ships a workflow that needs an IWE graph. The names keep the `iwe-` prefix,
because `plan`, `ship`, and `verify` alone look like skills of the same kind as
the `pr-*` skills in the same directory.

## Considered Options

- A separate `iwe` plugin. Rejected: it is a second catalog that has its own
  version and installation.
- The skills in `.claude/skills/`. Rejected: each consumer then gets them
  outside the supported installation path.
