---
type: plan
created: 2026-10-18
release:
- features/opencode-full-access-config
description: Configure OpenCode for unrestricted filesystem access inside the devcontainer on every start while preserving unrelated user configuration.
generated:
  by: codex/gpt-5
  at: 2026-10-18T18:54:34Z
sources:
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .devcontainer/scripts/reinstall-agentdev-opencode.sh
- resource: docs/knowledge/data/architecture/explicit-only-workflow-agents.md
---

# Configure devcontainer OpenCode for full access

## Context

[OpenCode full-access config](../features/opencode-full-access-config.md) makes
the devcontainer, rather than OpenCode's permission prompts, the isolation
boundary. The maintainer approved an OpenCode config that allows every action
and every external directory. The policy must be restored on each container
start, as the existing Codex full-access policy is, while keeping OpenCode's
catalog bridge registration and unrelated user settings.

[Make OpenCode v2 the devcontainer default](20261018-opencode-v2-default.md)
also changes OpenCode lifecycle files, but its outcome is the v2 migration. This
policy has an independent contract and verification story and applies to either
supported OpenCode major, so it is separate work with no dependency on that
plan.

## Approach

Add `.devcontainer/scripts/configure-opencode.py`, a standard-library Python
script that resolves the same config directory as
`reinstall-agentdev-opencode.sh`, parses `opencode.json`, merges the managed
schema and permission entries, and replaces the file atomically. Existing
top-level keys, permission rules, external-directory rules, and the catalog
bridge plugin list survive; the three managed values are restored on every
start. `postStartCommand.sh` runs the script after the other runtime setup so a
configuration failure cannot prevent the firewall, keyring, or Xpra from
starting.

The config directory follows `OPENCODE_CONFIG_DIR`, then
`XDG_CONFIG_HOME/opencode`, then `~/.config/opencode`, matching the existing
bridge registration script. The directory and config file are left at modes
`0700` and `0600`, and malformed JSON fails without replacing the original.

Rejected:

- Folding the policy into `reinstall-agentdev-opencode.sh`: catalog registration
  happens on create and attach, not on every container start, and permission
  policy is independent of whether a catalog is present.
- Replacing the complete config with the approved object: that would delete the
  bridge plugin and user-defined OpenCode settings.
- A textual shell edit: JSON has a standard-library parser, so string matching
  need not define the configuration contract.

## Implementation Steps

### Task 1: Add the OpenCode policy patcher and tests

**Files:** Create: `.devcontainer/scripts/configure-opencode.py`,
`scripts/tests/test_configure_opencode.py`

- [ ] Tests first, then implement an executable standard-library Python script
  that creates or patches `opencode.json`, preserves unrelated configuration,
  overwrites conflicting managed values, is byte-idempotent after the first run,
  honors `OPENCODE_CONFIG_DIR` and `XDG_CONFIG_HOME`, writes atomically at mode
  `0600` under a mode-`0700` directory, and leaves malformed JSON unchanged
  while failing. The managed result is exactly:

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

### Task 2: Restore the policy on every container start

**Files:** Modify: `.devcontainer/scripts/postStartCommand.sh`

- [ ] Run `configure-opencode.py` with `configure-codex.py` at the end of every
  start, after service and authentication setup, and keep the lifecycle script
  shellcheck-clean.

### Task 3: Record the full-access design and refresh the codebase map

**Files:** Create:
`docs/knowledge/data/architecture/opencode-full-access-in-devcontainer.md`;
Modify: `docs/knowledge/data/architecture.md`,
`docs/knowledge/data/architecture/template-boundary.md`,
`docs/knowledge/data/codebase/devcontainer/scripts.md`,
`docs/knowledge/data/codebase/flow-devcontainer-lifecycle.md`

- [ ] Record the devcontainer isolation boundary, managed config values,
  merge/atomicity constraints, config-directory resolution, and rejected
  alternatives; add the script to the template inventory and refresh the
  affected codebase-map documents.

## Spec changes

New spec `data/spec/devcontainer-opencode-policy` — unrestricted filesystem
access is a security-sensitive behavior, so the contract is stated in full:

``` markdown
## ADDED Requirements

### Requirement: devcontainer OpenCode runs with unrestricted filesystem access

On every container start, `postStartCommand.sh` SHALL set `$schema` to
`https://opencode.ai/config.json`, `permission["*"]` to `"allow"`, and
`permission.external_directory["/**"]` to `"allow"` in the OpenCode
`opencode.json` resolved from `OPENCODE_CONFIG_DIR`, `XDG_CONFIG_HOME`, or the
user's default config directory. The config directory SHALL have mode `0700`
and the file SHALL have mode `0600`.

#### Scenario: a container starts with no OpenCode config

- **WHEN** the container starts and `opencode.json` does not exist
- **THEN** it is created with the schema and both permission rules at mode
  `0600`.

#### Scenario: the config carries catalog and user settings

- **WHEN** `opencode.json` contains a plugin list, unrelated top-level keys, or
  additional permission rules
- **THEN** those values survive and the three managed values are set.

#### Scenario: a session changed the policy

- **WHEN** any managed value holds a different value
- **THEN** the next container start restores the approved value.

#### Scenario: the config is malformed

- **WHEN** the existing `opencode.json` is not valid JSON
- **THEN** the configure step fails and leaves the file unchanged.

### Requirement: the OpenCode configure step is consumer-independent

The configure script SHALL use only the Python standard library and SHALL NOT
depend on the consumer workspace's Python project or installed packages.

#### Scenario: a consumer repository has no Python project

- **WHEN** the devcontainer starts for a repository without `pyproject.toml`
- **THEN** the OpenCode policy is still configured.
```

## Verification

- `uv run pytest scripts/tests/test_configure_opencode.py`
- `uv run ruff check .devcontainer/scripts/configure-opencode.py scripts/tests/test_configure_opencode.py`
- `uv run ruff format --check .devcontainer/scripts/configure-opencode.py scripts/tests/test_configure_opencode.py`
- `shellcheck .devcontainer/scripts/postStartCommand.sh`
- In a sandboxed config directory under `./.tmp`, run the patcher twice and
  confirm the second run is byte-identical, the bridge plugin entry survives,
  the three managed JSON values match the approved config, and modes are
  `0700`/`0600`.
- Start OpenCode in the devcontainer and confirm reading and writing a path
  outside the workspace does not prompt.
- `iwe normalize` and `iwe schema validate` pass after document edits.

## Out of scope

- OpenCode settings other than `$schema`, the wildcard action permission, and
  the all-filesystem external-directory permission.
- Making the policy optional or configurable per consumer.
- Changing catalog subagents' explicit deny rules, which continue to restrict
  tools independently of the user's global allow policy.
- Changing OpenCode installation, auth persistence, server startup, or the v2
  bridge API.

## Key references

Verified anchor points (line numbers as of 2026-10-18):

- `.devcontainer/scripts/postStartCommand.sh:25-31` — agent config and auth
  steps at the end of each container start
- `.devcontainer/scripts/reinstall-agentdev-opencode.sh:21-38` — OpenCode
  config-directory resolution and existing JSON merge/write behavior
- `scripts/tests/test_configure_codex.py:21-90` — neighboring devcontainer
  configuration test structure
- `docs/knowledge/data/architecture/template-boundary.md:89-114` — tracked
  devcontainer runtime inventory
- `docs/knowledge/data/codebase/flow-devcontainer-lifecycle.md:29-47` — current
  postStart lifecycle sequence
