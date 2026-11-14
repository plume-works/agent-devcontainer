---
type: adr
stage: accepted
description: OpenCode runs with full access, and the runtime merges the agent policy into the OpenCode configuration of the user at each start.
---

# OpenCode runs with full access, merged into its configuration at each start

The Dev Container is the isolation boundary, so OpenCode runs in it with no
prompts for actions or external directories. At each start, the runtime merges
the agent policy into the OpenCode configuration of the user and replaces only
the managed keys.

## Considered Options

- Replace the whole configuration with the policy. Rejected: it removes the
  OpenCode bridge and the settings of the user.
- Change only `opencode.json`. Rejected: an `opencode.jsonc` has priority over
  the policy.
- Parse or edit the JSONC text locally. Rejected: comments, trailing commas,
  strings, and duplicate keys need a maintained parser.
- Apply the policy when the catalog installs. Rejected: catalog registration
  runs only in the create phase and the attach phase, and only when a bridge
  plugin exists, but each start must restore the policy.

## Consequences

- The write changes JSONC to strict JSON. It keeps each setting value, but it
  does not keep the comments and the format.
- The start phase applies the policy after the required services are ready. As a
  result, a bad OpenCode configuration makes the start phase fail where the user
  can see it. The failure does not stop the services, and the file stays
  unchanged.
