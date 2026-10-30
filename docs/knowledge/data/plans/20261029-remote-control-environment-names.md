---
type: plan
stage: done
created: 2026-10-29
completed: 2026-10-30
release:
- features/remote-control-environment-names
description: Give the dev container a hostname derived from its launcher — coder-<workspace>, vscode-<host>-<checkout>, or cli-<host>-<checkout> — so Claude Remote Control environments are identifiable.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T02:00:00Z
sources:
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/devcontainer-init.sh
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: scripts/tests/test_container_hostname.py
---

# Name Remote Control environments after their launcher

## Context

Claude Remote Control registers its environment with `machine_name` set to the
process's `os.hostname()`; `--name` and `--remote-control-session-name-prefix`
name sessions only. Without an explicit `hostname`, a Compose service's
container is named after its Docker container ID, so Coder workspaces would be
indistinguishable in Claude Desktop. The feature is [Remote Control environment
names](../features/remote-control-environment-names.md).

## Approach

The initialize command runs on the launching machine before Compose creates the
container, so it can see who launched it. `devcontainer-init.sh` derives the
name itself and writes it to the Compose `.env` as `CONTAINER_HOSTNAME`, and the
`devcontainer` service takes `hostname` from it. The naming rule, set by the
maintainer:

``` text
1. if CODER_WORKSPACE_NAME is set: "coder-${CODER_WORKSPACE_NAME}"
2. if normal run on PC/mac in vscode: "vscode-${HOSTNAME}-<checkout-stem>"
3. if coming up from cli, pass through: "cli-${HOSTNAME}-<checkout-stem>"
```

Renaming the environment from inside the container was rejected: no Claude flag
or variable overrides `machine_name`. The init script derives the name inline,
reading nothing under `.devcontainer/scripts/`: a consumer migrated to the
agentdev image keeps `devcontainer-init.sh` but deletes
`.devcontainer/scripts/`.

Assumptions recorded for minor details the rule leaves open:

- **Coder is checked first**, so a Coder workspace keeps its `coder-` name
  whatever VS Code variables are also set.
- **VS Code is detected by `VSCODE_PID` or `VSCODE_IPC_HOOK`**, which the VS
  Code extension host exports to the initialize command.
- **`${HOSTNAME}` is the short hostname.** The domain is dropped, so a Mac's
  `.local` suffix does not appear.
- **The name is normalised to one RFC 1123 label**: lowercase, other characters
  as hyphens, at most 63 characters.
- **Compose falls back to `agentdev`** when `CONTAINER_HOSTNAME` is unset, so a
  direct `docker compose` run still starts.

## Implementation Steps

### Task 1: Derive the hostname

**Files:** Modify: `.devcontainer/devcontainer-init.sh`; Create:
`scripts/tests/test_container_hostname.py`

- [x] The init script derives the name per the rule and assumptions above,
  reading nothing under `.devcontainer/scripts/`; tests run the real init script
  in a scratch checkout and cover each launcher, Coder precedence over VS Code
  variables, domain and case normalisation, invalid characters, and the
  63-character limit.
  - **Evidence:** commits c60bfb9 and a2917d1, the second setting both VS Code
    markers in the Coder precedence test;
    `uv run pytest scripts/tests/test_container_hostname.py` — 8 passed, and 1
    fails when the Coder and VS Code checks are swapped; `shellcheck` clean.

### Task 2: Apply it to the dev container

**Files:** Modify: `.devcontainer/devcontainer-init.sh`,
`.devcontainer/docker-compose.yml`

- [x] The init script writes `CONTAINER_HOSTNAME` to `.devcontainer/.env`, and
  the `devcontainer` service sets `hostname: ${CONTAINER_HOSTNAME:-agentdev}`.
  - **Evidence:** commit c60bfb9; `test_compose_sets_the_hostname` passed;
    pre-commit hooks passed.

### Task 3: Confirm the Coder name on a rebuilt workspace

- [x] Rebuild a Coder workspace's dev container and confirm `hostname` inside it
  and the Remote Control environment in Claude Desktop both read
  `coder-<workspace name>`.
  - **Evidence:** agent-dev2's dev container rebuilt from commit 2415d3a;
    `hostname` inside it reads `coder-agent-dev2`, and the init step wrote
    `CONTAINER_HOSTNAME=coder-agent-dev2`; the maintainer confirmed the Remote
    Control environment shows the new name.

### Task 4: Confirm the VS Code name on a laptop

- [x] Open the checkout in a container from VS Code on macOS and confirm the
  hostname reads `vscode-<short host>-<checkout>`.
  - **Evidence:** the maintainer's Mac `robomac` checkout at commit df90d99,
    which contains c60bfb9, opened from VS Code; `hostname` inside the container
    reads `vscode-robomac-agent-devcontainer`.

## Spec changes

[Claude Remote Control](../spec/claude-remote-control.md), inserted before
"Remote Control inherits the Coder agent's environment":

``` markdown
## ADDED Requirements

### Requirement: the dev container hostname names its launcher

Claude Remote Control names its environment after the container hostname, and
no Claude option overrides that name. `devcontainer-init.sh` SHALL write
`CONTAINER_HOSTNAME` to the Compose `.env`, and the `devcontainer` service SHALL
take its `hostname` from it. The init script SHALL derive the value itself,
reading no file under `.devcontainer/scripts/`, which a consumer migrated to the
agentdev image does not keep. It checks, in this order of precedence:

- `coder-<CODER_WORKSPACE_NAME>` when `CODER_WORKSPACE_NAME` is set;
- `vscode-<host>-<checkout>` when `VSCODE_PID` or `VSCODE_IPC_HOOK` is set,
  which the VS Code extension host exports to the initialize command;
- `cli-<host>-<checkout>` otherwise.

`<host>` is the launching machine's hostname without its domain, and
`<checkout>` is the base name of the checkout directory. The value SHALL be one
RFC 1123 label: lowercase, every run of other characters replaced by one hyphen,
no leading or trailing hyphen, and at most 63 characters.

#### Scenario: a Coder workspace starts the dev container

- **WHEN** the initialize command runs with `CODER_WORKSPACE_NAME=agent-dev2`
- **THEN** the container hostname, and so the Remote Control environment name,
  is `coder-agent-dev2`, whatever VS Code variables Coder also sets.

#### Scenario: VS Code on a laptop starts the dev container

- **WHEN** VS Code on `Antons-MBP.local` opens the `agent-devcontainer` checkout
  in a container
- **THEN** the hostname is `vscode-antons-mbp-agent-devcontainer`.

#### Scenario: the devcontainer CLI starts the dev container

- **WHEN** `devcontainer up` runs on `builder` for the `agent-devcontainer`
  checkout outside VS Code and Coder
- **THEN** the hostname is `cli-builder-agent-devcontainer`.
```

The spec's `description` gains the clause "and the dev container's hostname,
which names the Remote Control environment, says where the container came from",
and its `sources` gain `.devcontainer/devcontainer-init.sh` and
`scripts/tests/test_container_hostname.py`.

## Verification

- `uv run pytest scripts/tests/test_container_hostname.py` passes.
- `shellcheck .devcontainer/devcontainer-init.sh` is clean.
- `uv run pytest scripts/tests/test_template_consume_migration.py` passes: a
  consumer holding only the migrated descriptor files starts a Dev Container. CI
  runs it in the Dev Container runtime acceptance jobs.
- Tasks 3 and 4: the rebuilt containers' hostnames match the rule, and Claude
  Desktop lists the Coder environment as `coder-<workspace name>`.

## Out of scope

- The standalone `agent-opencode` and deploy runtimes under `docker/`, whose
  containers are not created through this Compose file.
- Distinguishing two containers of the same checkout opened by the same launcher
  on one machine.
- Renaming environments of containers that are not recreated.

## Key references

Verified anchor points (line numbers as of 2026-10-30):

- `.devcontainer/devcontainer-init.sh:32` — short host, domain dropped
- `.devcontainer/devcontainer-init.sh:35` — Coder branch, checked first
- `.devcontainer/devcontainer-init.sh:37` — VS Code detection
- `.devcontainer/devcontainer-init.sh:44` — 63-character limit
- `.devcontainer/devcontainer-init.sh:52` — `CONTAINER_HOSTNAME` written to
  `.env`
- `.devcontainer/docker-compose.yml:59` — `devcontainer` service `hostname`
- `.devcontainer/scripts/claude-remote-control-start.sh:53` — session `--name`
  and prefix, which this plan leaves unchanged
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:1138`
  — the migration deletes `.devcontainer/scripts/`
- `scripts/tests/test_container_hostname.py:20` — `checkout`, the scratch
  checkout the tests run the init script in
- `scripts/tests/test_template_consume_migration.py:39` —
  `test_the_migrated_descriptor_runs_no_copied_script`
