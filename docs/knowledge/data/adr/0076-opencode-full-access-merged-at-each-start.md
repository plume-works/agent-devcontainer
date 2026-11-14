---
type: adr
stage: accepted
description: OpenCode runs with full access, and the runtime merges the agent policy into the OpenCode configuration of the user at each start.
---

# OpenCode runs with full access, merged into its configuration at each start

The Dev Container is the isolation boundary, so OpenCode runs in it with no
prompts for actions or external directories. At each start, the runtime merges
the agent policy into the OpenCode configuration of the user and replaces only
the managed keys
(`py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py::apply_policy`).

## Considered Options

- Replace the whole configuration with the policy. Rejected: it removes the
  OpenCode bridge and the settings of the user.
- Change only `opencode.json`. Rejected: an `opencode.jsonc` has priority and
  can override the policy.
- Parse or edit the JSONC text locally. Rejected: comments, trailing commas,
  strings, and duplicate keys need a maintained parser.
- Apply the policy when the catalog installs. Rejected: catalog registration
  runs only in the create phase and the attach phase, and only when a bridge
  plugin exists, but each start must restore the policy.

## Consequences

- The runtime parses the configuration with a pinned `json5` that
  `agentdev_runtime` declares itself, so template consumers add no Python
  dependency.
- The write changes JSONC to strict JSON. It keeps each setting value, but it
  does not keep the comments and the format.
- The policy sets `"*": "allow"` and `external_directory` `"/**": "allow"`. It
  keeps the other permission rules, the other external directory rules, and the
  bridge registration of the user.
- The configuration directory comes from `OPENCODE_CONFIG_DIR`, then from
  `XDG_CONFIG_HOME/opencode`, then from `~/.config/opencode`. The runtime
  changes `opencode.jsonc` when it exists, and `opencode.json` if not.
- The start phase applies the policy after the required services are ready. As a
  result, a bad OpenCode configuration makes the start phase fail where the user
  can see it, but it does not stop the services, and the file stays unchanged.
- The parser refuses a duplicate key, because its meaning is not clear.
- The runtime writes the file at mode `0600` through a temporary file in the
  same directory, and sets the directory to mode `0700`.
