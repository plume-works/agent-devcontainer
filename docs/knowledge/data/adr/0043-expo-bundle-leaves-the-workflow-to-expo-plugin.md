---
type: adr
stage: accepted
description: The expo optional bundle only prepares a consumer for EAS builds; Expo's own plugin owns the agent workflow, and EXPO_TOKEN passes through the shared devcontainer descriptor.
---

# The Expo bundle prepares EAS builds and leaves the workflow to Expo

The official `expo@claude-plugins-official` plugin owns the agent workflow for
Expo. The `expo` optional bundle only prepares the consumer for it. It pins
`bun` in every `eas.json` build profile, because EAS macOS workers do not
default to the image's bun, and the image's bun writes a `bun.lock` that an
older bun cannot read under `--frozen-lockfile`. It adds the EAS hosts to the
allowlist, and it adds `.env.eas-simulator`, where EAS Simulator writes a
session token, to `.gitignore`. `EXPO_TOKEN` passes to every container through
`.devcontainer/devcontainer.json#containerEnv.EXPO_TOKEN`: `eas` treats an empty
`EXPO_TOKEN` as no token, so the template-wide passthrough of an unset host
variable is inert.

## Considered Options

- Pass the token only in the Expo setup. Rejected: an Expo-only edit to the
  template-tracked `.devcontainer/devcontainer.json` makes every later
  devcontainer update a manual merge.
- Keep the token on the shared auth volume. Rejected: the token belongs to the
  hosting environment, where it can be scoped and revoked.

## Consequences

- The bundle adds no `tracked_paths`. It edits files that the consumer already
  has, and the consumer-owned `eas.json`, so no `tracked_paths` diff shows its
  edits. At each update, the update mode of `template-consume` compares the Expo
  setup steps of its consumption guide, `references/consumption-guide.md`, with
  the files of the consumer.
- The setup grants the Expo bridge no trust: it writes no trust or security
  setting into any consumer file, because a workspace is trusted only on the
  Mac.
