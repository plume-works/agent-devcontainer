---
type: architecture
description: Why devcontainer OpenCode sessions allow every action and external filesystem path, and how the policy is merged into JSON or JSONC on every start.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:32:14Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: https://opencode.ai/docs/config/
---

# OpenCode full access in the devcontainer

The devcontainer is the isolation boundary, so OpenCode runs inside it without
action or external-directory permission prompts. On every container start,
`agentdev-runtime state agent-policy` sets these managed values:

``` json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "*": "allow",
    "external_directory": {
      "/**": "allow"
    }
  }
}
```

The policy runs near the end of `agentdev-runtime lifecycle ready`, after the
supervised services are ready and the authentication setup. A malformed OpenCode
config therefore fails the start hook visibly without preventing those services
from starting, and the original config remains unchanged.

## Configuration contract

The config directory resolves from `OPENCODE_CONFIG_DIR`, then
`XDG_CONFIG_HOME/opencode`, then `~/.config/opencode`. OpenCode accepts both
JSON and JSONC and gives `opencode.jsonc` higher precedence within one config
directory, so the script patches that file when it exists and otherwise patches
`opencode.json`.

The managed values replace conflicts, while unrelated top-level settings,
additional permission rules, external-directory rules, and catalog plugin
registration survive. JSONC is parsed with pinned `json5==0.17.3` and normalized
to strict JSON when written; semantic values survive, but comments and original
formatting do not. Duplicate keys are rejected instead of being interpreted
ambiguously.

The config directory is mode `0700`, and the selected config is atomically
replaced at mode `0600` through a temporary file in the same directory. The
`opencode_config` module of the `agentdev_runtime` package carries `json5` as
the package's own dependency, so template consumers add no Python dependency.

## Rejected alternatives

- **Replace the whole config with the managed object:** this would remove the
  catalog bridge and user-defined settings.
- **Patch only `opencode.json`:** an existing `opencode.jsonc` loads later and
  could override the policy.
- **Implement JSONC parsing or textual edits locally:** comments, trailing
  commas, strings, and duplicate keys require a maintained parser.
- **Fold the policy into catalog reinstallation:** catalog registration runs on
  create and attach and is conditional on a bridge plugin; the permission policy
  must be restored independently on every start.
