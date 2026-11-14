---
type: adr
stage: accepted
description: The expo optional bundle only prepares a consumer for EAS builds; Expo's own plugin owns the agent workflow, and EXPO_TOKEN passes through the shared devcontainer descriptor.
---

# The Expo bundle prepares EAS builds and leaves the workflow to Expo

The official `expo@claude-plugins-official` plugin owns the agent workflow for
Expo. The `expo` optional bundle only prepares the consumer. It adds a `bun` pin
in each `eas.json` build profile and the EAS hosts in the allowlist. It also
adds the token file of the EAS Simulator to `.gitignore`. `EXPO_TOKEN` passes to
every container through
`.devcontainer/devcontainer.json#containerEnv.EXPO_TOKEN`, because `eas` reads
an empty token as no token.

## Considered Options

- Pass the token only in the Expo setup. Rejected: an Expo-only edit to
  `.devcontainer/devcontainer.json` makes each later devcontainer update a
  manual merge.
- Keep the token on the shared auth volume. Rejected: the token belongs to the
  host environment, where its owner can limit and cancel it.

## Consequences

- The bundle adds no `tracked_paths`. It edits files that the consumer already
  has, and `eas.json`. As a result, no diff shows its edits. At each update,
  update mode compares the Expo setup steps of the consumption guide with the
  files of the consumer.
- The setup writes no trust or security setting of the bridge, because only the
  Mac gives trust to a workspace.
