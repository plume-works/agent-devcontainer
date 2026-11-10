---
type: plan
created: 2026-11-03
release:
- features/nested-agent-dispatch
description: Set Claude Code's and OpenCode's subagent nesting limit to 5 in the devcontainer and the standalone runtime, so a dispatched catalog agent can dispatch another on both harnesses.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py
- resource: .devcontainer/docker-compose.yml
- resource: compose.opencode.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: openspec/specs/nested-agent-dispatch/spec.md
stage: done
completed: 2026-11-09
---

# Nest agent dispatch to depth 5 on both harnesses

## Context

[Nested agent dispatch](../features/nested-agent-dispatch.md) is the feature
this plan delivers, and [Nested dispatch from catalog
agents](../backlog/nested-catalog-agent-dispatch.md) is the backlog task it
replaces. The repository owner decided that both harnesses nest subagent
dispatch to depth 5, so later plans can have a dispatched catalog agent start a
fresh-context agent of its own, starting with `iwe-shipper` dispatching
`iwe-verifier`.

Claude Code 2.1.316 nests to depth 3 by default: the agent at the limit is not
offered the `Agent` tool, and nothing reports an error. The environment variable
`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` sets the limit. OpenCode refuses any
nested dispatch at its default `experimental.subagent_depth` of 1 ([Nested
subagent
dispatch](../../../../openspec/specs/nested-agent-dispatch/spec.md#rationale)).

## Approach

Each harness gets its limit where it reads it:

- **Claude Code** reads `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` from its
  environment. The `environment:` block of the `devcontainer` service in
  `.devcontainer/docker-compose.yml` and of the `opencode` service in
  `compose.opencode.yml` sets it to `5`.
- **OpenCode** reads `experimental.subagent_depth` from its config.
  `agentdev-runtime state agent-policy`, which already restores OpenCode's
  permission policy on every container start in both containers, sets it to `5`
  through `opencode_config.apply_policy`, keeping every other `experimental` key
  and restoring a changed value.

Rejected:

- Writing `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` into Claude Code's
  `settings.json` from `agentdev-runtime state agent-policy`. The repository
  owner chose the compose environment, which states the value where the
  container is defined.
- Writing it from the `agentic_tools` Ansible role at image build. `~/.claude`
  is the `agentdev-claude` volume (`.devcontainer/devcontainer.json`), which
  hides the image's `~/.claude/settings.json` once the volume holds a file.

Assumption: both compose files set the value as
`${CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH:-5}`, so a host value overrides the
default of 5 in the devcontainer, and a host or `runtime.env` value does so in
the standalone runtime.

## Implementation Steps

### Task 1: OpenCode nests to depth 5

**Files:** Modify:
`py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py`,
`py_packages/agentdev_runtime/tests/test_opencode_config.py`,
`scripts/tests/test_configure_opencode.py`

- [x] `apply_policy` sets `experimental.subagent_depth` to `5`, keeps every
  other `experimental` key and its position, and restores a changed value; tests
  cover a config without `experimental`, one with other `experimental` keys, and
  one with a different depth.
  - **Evidence:** commit 5f78f729 (`opencode_config.py::apply_policy`,
    `SUBAGENT_DEPTH`);
    `uv run pytest py_packages/agentdev_runtime/tests/test_opencode_config.py scripts/tests/test_configure_opencode.py scripts/tests/test_agent_runtime_state.py`
    — 25 passed, including `test_a_config_without_experimental_gains_the_depth`,
    `test_other_experimental_keys_keep_their_values_and_order`, and
    `test_a_changed_depth_is_restored`.

### Task 2: Claude Code nests to depth 5

**Files:** Modify: `.devcontainer/docker-compose.yml`, `compose.opencode.yml`,
`docker/deploy/runtime.env.example`; Test:
`scripts/tests/test_agent_runtime_compose.py`,
`scripts/tests/test_devcontainer_compose.py`

- [x] The `devcontainer` service in `.devcontainer/docker-compose.yml` and the
  `opencode` service in `compose.opencode.yml` set
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH: ${CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH:-5}`
  in their `environment:` blocks.
  - **Evidence:** commit e17c64a5; `docker compose config` of
    `.devcontainer/docker-compose.yml`, and of `compose.opencode.yml` with
    `opencode-compose-pins.yml`, renders the variable as `"5"` with it unset on
    the host, as the host's value when set, and as an `--env-file` value for the
    standalone runtime. Commit 51b054a5 documents the setting in
    `docker/deploy/runtime.env.example`;
    `uv run pytest scripts/tests/test_agent_runtime_compose.py` — 11 passed.
    Commit b62a2a0c adds
    `test_subagent_depth_defaults_to_five_and_takes_the_host_value` to
    `scripts/tests/test_agent_runtime_compose.py` and
    `scripts/tests/test_devcontainer_compose.py`; `uv run pytest` of both files
    — 13 passed.
- [x] In a container started from each compose file, the nesting fixture in
  [Nested subagent
  dispatch](../../../../openspec/specs/nested-agent-dispatch/spec.md#rationale),
  extended to five levels, reaches depth 5 on Claude Code, read from each
  subagent's `.meta.json` `spawnDepth`.
  - **Evidence:** commit e17c64a5. `docker compose run` of the `devcontainer`
    service (`.devcontainer/docker-compose.yml` with
    `devcontainer-compose-pins.yml`) and of the `opencode` service
    (`compose.opencode.yml` with `opencode-compose-pins.yml`), with the variable
    unset on the host: each container's environment held
    `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=5`, and on Claude Code 2.1.319 with
    `--model haiku` the fixture's chain of agents `d1` to `d4`, each dispatching
    the next, and leaf `d5` returned the leaf marker, with `.meta.json`
    `spawnDepth` 1 to 5 for `d1` to `d5`.

### Task 3: Record the depth limits

**Files:** Modify:
`docs/knowledge/data/architecture/nested-subagent-dispatch.md`

- [x] `## Host behavior` records, for Claude Code 2.1.316: the variable
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` sets the nesting limit; when it is
  unset, a server-side flag sets the limit, falling back to 3; the agent at the
  limit is not offered the `Agent` tool, and nothing reports an error. It also
  records that the devcontainer and the standalone runtime set both harnesses to
  5, and replaces the 2.1.306 version the section names.
  - **Evidence:** commits 18cd734f and 67582b9f
    (`docs/knowledge/data/architecture/nested-subagent-dispatch.md#host-behavior`);
    `iwe normalize` and `iwe schema validate` pass.

## Spec changes

[Devcontainer OpenCode
policy](../../../../openspec/specs/devcontainer-opencode-policy/spec.md) — the
managed values gain the nesting depth.

``` markdown
## MODIFIED Requirements

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
- **THEN** it is created with the schema, both permission rules, and the
  nesting depth at mode `0600`.

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
```

[Nested agent
dispatch](../../../../openspec/specs/nested-agent-dispatch/spec.md) — a new spec
for Claude Code's nesting limit in both containers.

``` markdown
## ADDED Requirements

### Requirement: Claude Code nests subagent dispatch to depth 5

The `devcontainer` service in `.devcontainer/docker-compose.yml` and the
`opencode` service in `compose.opencode.yml` SHALL set
`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` in the container environment to the
host's value when it is set, and to `5` otherwise.

#### Scenario: a container starts with no override

- **WHEN** either container starts and the host sets no
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`
- **THEN** Claude Code in the container nests subagent dispatch to depth 5.

#### Scenario: the host overrides the depth

- **WHEN** the host, or for the standalone runtime `runtime.env`, sets
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`
- **THEN** the container's Claude Code uses that value.
```

## Verification

- `uv run pytest py_packages/agentdev_runtime/tests/test_opencode_config.py`
- In a rebuilt devcontainer and a standalone runtime container, the fixture in
  [Nested subagent
  dispatch](../../../../openspec/specs/nested-agent-dispatch/spec.md#rationale)
  extended to five levels reaches depth 5 on Claude Code, read from each
  subagent's `.meta.json` `spawnDepth`.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Any catalog agent gaining the `Agent` tool or dispatching another agent; the
  first is `iwe-shipper` dispatching `iwe-verifier`, in its own plan.
- The requirement in [IWE workflow
  skills](../../../../openspec/specs/iwe-workflow-skills/spec.md) that no agent
  the Implement loop dispatches dispatches another.
- Raising the depth outside the devcontainer, such as on a native macOS host.

## Key references

- `py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py::apply_policy`
  — `apply_policy`;
  `py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py::configure`
  — `configure`
- `.devcontainer/docker-compose.yml#services.devcontainer.environment` — the
  `devcontainer` service's `environment:` block
- `compose.opencode.yml#services.opencode.environment` — the `opencode`
  service's `environment:` block
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py::apply_agent_policy`
  — `apply_agent_policy`
- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::ready` — the
  `ready` step calls `apply_agent_policy`
- `py_packages/agentdev_runtime/agentdev_runtime/workspace.py::Workspace.prepare`
  — the standalone core phase calls `apply_agent_policy`
- `docs/knowledge/data/spec/devcontainer-opencode-policy.md#requirement-devcontainer-opencode-runs-with-unrestricted-filesystem-access`
  — Requirement: devcontainer OpenCode runs with unrestricted filesystem access
- `docs/knowledge/data/architecture/nested-subagent-dispatch.md#host-behavior` —
  `## Host behavior`
