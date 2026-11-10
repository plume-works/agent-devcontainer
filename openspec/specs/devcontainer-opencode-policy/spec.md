# Devcontainer OpenCode policy Specification

## Purpose

Defines the OpenCode action and filesystem permission policy inside the
devcontainer, which is itself the isolation boundary.

## Requirements

### Requirement: devcontainer OpenCode runs with unrestricted filesystem access

On every container start, `agentdev-runtime lifecycle ready` SHALL, through
`agentdev-runtime state agent-policy`, set `$schema` to
`https://opencode.ai/config.json`, `permission["*"]` to `"allow"`,
`permission.external_directory["/**"]` to `"allow"`, and
`experimental.subagent_depth` to `5` in the OpenCode `opencode.json` resolved
from `OPENCODE_CONFIG_DIR`, `XDG_CONFIG_HOME`, or the user's default config
directory. The config directory SHALL have mode `0700` and the file SHALL have
mode `0600`.

#### Scenario: a container starts with no OpenCode config

- **WHEN** the container starts and `opencode.json` does not exist
- **THEN** it is created with the schema, both permission rules, and the nesting
  depth at mode `0600`.

#### Scenario: the config carries catalog and user settings

- **WHEN** `opencode.json` contains a plugin list, unrelated top-level keys,
  additional permission rules, or other `experimental` keys
- **THEN** those values survive and the managed values are set.

#### Scenario: the config directory contains JSON and JSONC

- **WHEN** `opencode.jsonc` contains comments or trailing commas and exists
  alongside `opencode.json`
- **THEN** the configure step patches the higher-precedence JSONC config,
  preserves its setting values, and leaves `opencode.json` unchanged.

#### Scenario: a session changed the policy

- **WHEN** any managed value holds a different value
- **THEN** the next container start restores the approved value.

#### Scenario: the config is malformed

- **WHEN** the existing `opencode.json` is not valid JSON
- **THEN** the configure step fails and leaves the file unchanged.

### Requirement: the OpenCode configure step is consumer-independent

`agentdev-runtime state agent-policy` SHALL take its pinned JSONC parser
dependency from the `agentdev_runtime` package installed in the image, without
depending on the consumer workspace's Python project or installed packages.

#### Scenario: a consumer repository has no Python project

- **WHEN** the devcontainer starts for a repository without `pyproject.toml`
- **THEN** the OpenCode policy is still configured.

## Rationale

### The devcontainer is the isolation boundary

OpenCode runs inside the devcontainer without permission prompts because the
container is what isolates it. The policy runs late in `lifecycle ready`, after
the supervised services and authentication, so a malformed config fails the
start hook visibly without keeping those services down. OpenCode gives
`opencode.jsonc` precedence over `opencode.json` within one directory, which is
why the JSONC file is patched when it exists; JSONC is parsed with pinned
`json5`, written back as strict JSON, and duplicate keys are rejected rather
than read ambiguously.

Rejected:

- **Replace the whole config with the managed object.** It would remove the
  catalog bridge and user settings.
- **Patch only `opencode.json`.** An existing `opencode.jsonc` loads later and
  could override the policy.
- **Parse JSONC or edit text locally.** Comments, trailing commas, strings, and
  duplicate keys need a maintained parser.
- **Fold the policy into catalog reinstallation.** Registration runs on create
  and attach and depends on a bridge plugin; the policy must be restored on
  every start.
