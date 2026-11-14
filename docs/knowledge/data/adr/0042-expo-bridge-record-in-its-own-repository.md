---
type: adr
stage: accepted
description: The full record of the VS Code Expo bridge lives in the graph of plume-works/vscode-expo-bridge, and this repository keeps only the configuration of the Expo bundle.
---

# The Expo bridge keeps its record in its own repository

The design, plans, bugs, and backlog of the VS Code Expo bridge, and its closed
items, live in the graph of `plume-works/vscode-expo-bridge`. This repository
keeps only the configuration of the `expo` optional bundle and its release
notes. It links to bridge documents by an absolute GitHub URL on `main`.

## Considered Options

- Keep closed bridge plans and fixed bugs here. Rejected: the record of one
  product is then in two repositories, and open bugs there link to closed plans
  here.
- Adopt the full template in the bridge repository. Rejected: it adds a
  devcontainer and a catalog that the bridge does not need. The bridge uses
  `/agentdev:iwe-bootstrap` alone for its project memory.

## Consequences

- The `expo` optional bundle adds no tracked path. Its edits are in files that
  the template tracks or that the consumer owns, so no diff shows them. For this
  reason, update mode compares the Expo edits with the consumption guide at each
  update.
- The setup writes no trust or security setting for the bridge in a file of the
  consumer. A workspace gets trust only on the Mac, when the bridge asks for it.
