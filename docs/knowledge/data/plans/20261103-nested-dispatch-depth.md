---
type: plan
created: 2026-11-03
release:
- features/nested-agent-dispatch
description: Set Claude Code's and OpenCode's subagent nesting limit to 5 in the devcontainer on every container start, so a dispatched catalog agent can dispatch another on both harnesses.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-03T06:10:00Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/claude_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: docs/knowledge/data/architecture/nested-subagent-dispatch.md
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
subagent dispatch](../architecture/nested-subagent-dispatch.md)).

## Approach

`agentdev-runtime state agent-policy`, which already restores OpenCode's
permission policy on every container start, also sets the two depth values:

- `experimental.subagent_depth` to `5` in the OpenCode config
  `opencode_config.apply_policy` already patches, keeping every other
  `experimental` key.
- `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` to `"5"` in Claude Code's
  `settings.json`, keeping every other key, through `claude_state.update_json`.

Both are restored when a session changes them, like the permission policy.

Rejected: writing the Claude Code value from the `agentic_tools` Ansible role at
image build. `~/.claude` is the `agentdev-claude` volume
(`.devcontainer/devcontainer.json`), which hides the image's
`~/.claude/settings.json` once the volume holds a file.

Assumption: Claude Code's `settings.json` is resolved from `CLAUDE_CONFIG_DIR`
when it is set, and from `~/.claude` otherwise, as Claude Code resolves it.

## Implementation Steps

### Task 1: OpenCode nests to depth 5

**Files:** Modify:
`py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py`,
`py_packages/agentdev_runtime/tests/test_opencode_config.py`

- [ ] `apply_policy` sets `experimental.subagent_depth` to `5`, keeps every
  other `experimental` key and its position, and restores a changed value; tests
  cover a config without `experimental`, one with other `experimental` keys, and
  one with a different depth.

### Task 2: Claude Code nests to depth 5

**Files:** Modify:
`py_packages/agentdev_runtime/agentdev_runtime/claude_state.py`,
`py_packages/agentdev_runtime/agentdev_runtime/agent_state.py`,
`py_packages/agentdev_runtime/tests/test_claude_state.py`

- [ ] A `claude_state` function sets `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`
  to `"5"` in `settings.json` under `CLAUDE_CONFIG_DIR` or `~/.claude`, keeping
  every other key, including the `cc-filter` `hooks`; tests cover a missing
  file, a file with other `env` entries and `hooks`, and a different value.
- [ ] `apply_agent_policy` calls it after `opencode_config.configure`, so both
  `agentdev-runtime lifecycle ready` and the standalone supervisor's core phase
  apply it; a test runs `agentdev-runtime state agent-policy` against a scratch
  home and reads both files.

### Task 3: Record the depth limits

**Files:** Modify:
`docs/knowledge/data/architecture/nested-subagent-dispatch.md`

- [ ] `## Host behavior` records, for Claude Code 2.1.316: the variable
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` sets the nesting limit; when it is
  unset, a server-side flag sets the limit, falling back to 3; the agent at the
  limit is not offered the `Agent` tool, and nothing reports an error. It also
  records that the devcontainer sets both harnesses to 5, and replaces the
  2.1.306 version the section names.

## Spec changes

[Devcontainer OpenCode policy](../spec/devcontainer-opencode-policy.md) — the
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

`devcontainer-claude-policy` — a new spec for Claude Code's managed settings.

``` markdown
## ADDED Requirements

### Requirement: devcontainer Claude Code nests subagent dispatch to depth 5

On every container start, `agentdev-runtime state agent-policy` SHALL set
`env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` to `"5"` in the Claude Code
`settings.json` under `CLAUDE_CONFIG_DIR`, or under `~/.claude` when that
variable is unset, preserving every other key.

#### Scenario: a container starts with no Claude Code settings

- **WHEN** the container starts and `settings.json` does not exist
- **THEN** it is created holding only the managed `env` value.

#### Scenario: the settings carry hooks and other environment values

- **WHEN** `settings.json` holds `hooks` and other `env` entries
- **THEN** those values survive and the managed value is set.

#### Scenario: a session changed the depth

- **WHEN** `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` holds a different value
- **THEN** the next container start restores `"5"`.
```

## Verification

- `uv run pytest py_packages/agentdev_runtime/tests/test_opencode_config.py py_packages/agentdev_runtime/tests/test_claude_state.py`
- In a rebuilt devcontainer, the fixture in [Nested subagent
  dispatch](../architecture/nested-subagent-dispatch.md) extended to five levels
  reaches depth 5 on Claude Code, read from each subagent's `.meta.json`
  `spawnDepth`.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Any catalog agent gaining the `Agent` tool or dispatching another agent; the
  first is `iwe-shipper` dispatching `iwe-verifier`, in its own plan.
- The requirement in [IWE workflow skills](../spec/iwe-workflow-skills.md) that
  no agent the Implement loop dispatches dispatches another.
- Raising the depth outside the devcontainer, such as on a native macOS host.

## Key references

Verified anchor points (line numbers as of 2026-11-03):

- `py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py:44` —
  `apply_policy`; `:83` — `configure`
- `py_packages/agentdev_runtime/agentdev_runtime/claude_state.py:18` —
  `update_json`; `:35` — `preapprove`
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py:104` —
  `apply_agent_policy`
- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py:152` — the `ready`
  step calls `apply_agent_policy`
- `py_packages/agentdev_runtime/agentdev_runtime/workspace.py:171` — the
  standalone core phase calls `apply_agent_policy`
- `docs/knowledge/data/spec/devcontainer-opencode-policy.md:26` — Requirement:
  devcontainer OpenCode runs with unrestricted filesystem access
- `docs/knowledge/data/architecture/nested-subagent-dispatch.md:18` —
  `## Host behavior`
- `ansible/roles/agentic_tools/tasks/cc_filter.yml` — merges the `cc-filter`
  `hooks` into `~/.claude/settings.json` at image build
