---
type: adr
stage: accepted
description: The IWE workflow skills are in the agentdev catalog, and their names keep the iwe- prefix.
---

# The IWE workflow skills are in agentdev, with an iwe- prefix

The maintainer put the IWE workflow skills in the `agentdev` catalog, so that
only one catalog is versioned and installed, accepting that `agentdev` ships a
workflow that assumes an IWE graph. The names keep the `iwe-` prefix although
`agentdev:` already namespaces them, because `plan`, `ship`, and `verify` alone
would read as peers of the `pr-*` skills in the same directory.

## Considered Options

- A separate `iwe` plugin. Rejected: it is a second catalog to version and
  install.
- Keep the skills under `.claude/skills/`. Rejected: every consumer would
  inherit them outside the supported install path.
