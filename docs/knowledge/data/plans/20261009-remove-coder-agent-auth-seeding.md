---
type: plan
created: 2026-10-09
description: Delete the Coder-secret seeding of Claude and Codex credentials, gate Claude Remote Control autostart on a live claude.ai login, run Claude workspace pre-approval in every container with an opt-out, and split the agent-auth spec in two.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-09T00:00:00Z
sources:
- resource: .devcontainer/devcontainer-init.sh
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/scripts/preapprove-claude-workspace.sh
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .github/actions/run-claude-responder/action.yml
---

# Remove Coder agent auth seeding; keep Claude Remote Control autostart

## Context

[Devcontainer agent authentication and Claude Remote
Control](../spec/devcontainer-agent-auth.md) seeds native Claude and Codex
credential documents from the Coder user secrets `AGENTDEV_CLAUDE_JSON` and
`AGENTDEV_CODEX_JSON` into each nested devcontainer. Claude.ai rotates its
refresh token on refresh, so one snapshot copied into several workspaces stays
valid only in the first workspace that refreshes; the others reach
`Login expired`. Codex seeding shares the same mechanism and goes with it. The
spec's own "one refresh owner" requirement already rules out the use the feature
was built for. The maintainer decided to delete the seeding outright; no
consumer uses it, so there is no deprecation period.

Claude Remote Control autostart stays. Its current gate treats a non-empty
`.credentials.json` as a login, but a rejected refresh leaves a non-empty file
with emptied tokens, so autostart launches into a dead login.

The shared `agentdev-agents-auth` volume ([Agent auth
persistence](../architecture/agent-auth-persistence.md)) is a separate decision
and stays: a `/login` inside any container persists there.

## Approach

Remove every part of the seeding path: the two Coder variables, the transfer
directory written by `initializeCommand`, its bind mount, and the scripts that
consume it.

`claude-remote-control-start.sh` keeps its opt-in variable, tmux idempotence,
and `env -u CLAUDE_CODE_OAUTH_TOKEN`, and replaces the file check with
`claude auth status --json`: it starts only when `loggedIn` is `true` and
`authMethod` is `"claude.ai"`. A setup-token login cannot run Remote Control, so
the method is checked in addition to `loggedIn`. The script runs from
`postStartCommand.sh` and may be run by hand after a later `/login`.

`preapprove-claude-workspace.sh` drops its autostart gate and runs in every
container from `postCreateCommand.sh`, skipped only when
`AGENTDEV_SKIP_CLAUDE_PREAPPROVE` is non-empty — the same convention as
`AGENTDEV_SKIP_XPRA` and `AGENTDEV_SKIP_PRE_COMMIT`. The CI responder sets it so
that `enableAllProjectMcpServers` does not reach the headless responder, whose
`.mcp.json` names an `mcp-gateway` server that CI does not run.

The spec is retired and split: `spec/claude-remote-control` (autostart and
pre-approval) and `spec/devcontainer-git-credentials` (Git identity passthrough
and the `gh` credential helper), since neither half is about agent auth once
seeding is gone.

Rejected:

- A deprecation warning when either Coder variable is still set: no consumer
  uses the feature.
- Gating pre-approval on `AGENTDEV_SKIP_XPRA`: that variable names the remote
  desktop, not headlessness.
- Pre-approval with no opt-out: it would enable every project MCP server in the
  CI responder.

## Implementation Steps

### Task 1: Delete the seeding path

**Files:** Delete: `.devcontainer/scripts/prepare-agent-auth-seed.sh`,
`.devcontainer/scripts/seed-agent-auth.sh`,
`.devcontainer/scripts/workspace-seed-key.sh`,
`scripts/tests/test_seed_agent_auth.py`,
`scripts/tests/test_devcontainer_init_seed_key.py`; Modify:
`.devcontainer/devcontainer-init.sh`, `.devcontainer/docker-compose.yml`,
`.devcontainer/scripts/postCreateCommand.sh`,
`.devcontainer/scripts/postStartCommand.sh`

- [x] Remove the seed block from `devcontainer-init.sh` (the comment, the
  `seed_key` and `AGENTDEV_AUTH_SEED_DIR` lines, the
  `prepare-agent-auth-seed.sh` call, and the `.env` echo), the
  `/run/agentdev-auth-seed` bind mount from `docker-compose.yml`, and the
  `seed-agent-auth.sh` calls (with the postStart comment above it) from both
  lifecycle scripts; delete the three scripts and their two test files.
  `AGENTDEV_CLAUDE_AUTOSTART` and the four `GIT_*` passthroughs in
  `docker-compose.yml` stay.
  - **Evidence:** commit "Delete Coder agent auth seeding" on `ai-autostart`;
    `docker-compose.yml:69-73` keeps the autostart and `GIT_*` entries.
- [x] `grep -rn 'AGENTDEV_CLAUDE_JSON\|AGENTDEV_CODEX_JSON\|AUTH_SEED\|seed-agent-auth\|workspace-seed-key\|prepare-agent-auth-seed' .devcontainer scripts .github`
  prints nothing; `shellcheck` passes on the edited scripts.
  - **Evidence:** commit "Delete Coder agent auth seeding": `git grep` of the
    pattern over the three trees finds nothing (the only filesystem hit is the
    ignored, regenerated `.devcontainer/.env`); `shellcheck` clean on
    `devcontainer-init.sh`, `postCreateCommand.sh`, `postStartCommand.sh`;
    `uv run pytest scripts/tests/test_preapprove_claude_workspace.py scripts/tests/test_claude_remote_control_start.py`
    11 passed.

### Task 2: Gate autostart on a live claude.ai login

**Files:** Modify: `.devcontainer/scripts/claude-remote-control-start.sh`,
`scripts/tests/test_claude_remote_control_start.py`

- [x] Replace the credential-file check with `claude auth status --json`; start
  only when it exits 0 with `loggedIn: true` and `authMethod: "claude.ai"`,
  otherwise print the reason and exit 0. Check that `claude` and `tmux` exist
  before calling `claude`. Drop the `AGENTDEV_CLAUDE_AUTH_PATH` /
  `CLAUDE_SECURESTORAGE_CONFIG_DIR` path logic.
  - **Evidence:** commit "Gate Remote Control autostart on a live claude.ai
    login" (`claude-remote-control-start.sh:16-32`); `shellcheck` clean; with
    `CLAUDE_CONFIG_DIR` and `CLAUDE_SECURESTORAGE_CONFIG_DIR` on an empty
    directory the script prints the not-logged-in skip and exits 0.
- [x] Tests drive a fake `claude` that prints a chosen status document: starts
  on a claude.ai login; skips when autostart is unset, when `loggedIn` is false,
  when `authMethod` is not `claude.ai`, and when `claude auth status` fails;
  existing session reuse and `CLAUDE_CODE_OAUTH_TOKEN` removal still hold.
  `uv run pytest scripts/tests/test_claude_remote_control_start.py` passes.
  - **Evidence:** commit "Gate Remote Control autostart on a live claude.ai
    login": `uv run pytest scripts/tests/test_claude_remote_control_start.py` 10
    passed, real-tmux cases included; 4 of them fail against the previous
    credential-file gate.

### Task 3: Run pre-approval in every container, with an opt-out

**Files:** Modify: `.devcontainer/scripts/preapprove-claude-workspace.sh`,
`.devcontainer/scripts/postCreateCommand.sh`,
`.github/actions/run-claude-responder/action.yml`,
`scripts/tests/test_preapprove_claude_workspace.py`

- [x] Replace the `AGENTDEV_CLAUDE_AUTOSTART` gate with a skip when
  `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` is non-empty; update its spec-key comments
  to `spec/claude-remote-control`.
  - **Evidence:** commit "Pre-approve Claude workspace state in every container"
    (`preapprove-claude-workspace.sh:3,6,50`); `shellcheck` clean.
- [x] Set `AGENTDEV_SKIP_CLAUDE_PREAPPROVE: '1'` in the responder's "Run
  devcontainer lifecycle scripts" step.
  - **Evidence:** commit "Pre-approve Claude workspace state in every container"
    (`run-claude-responder/action.yml:101`), asserted by
    `test_ci_responder_opts_out`.
- [x] Tests: pre-approval runs with autostart unset; skips when the opt-out is
  set; the post-create ordering test asserts the call follows the
  `~/.claude.json` symlink instead of the deleted seeding call; a test asserts
  the responder action sets the opt-out.
  `uv run pytest scripts/tests/test_preapprove_claude_workspace.py` passes.
  - **Evidence:** the ordering test landed with commit "Delete Coder agent auth
    seeding", the rest with "Pre-approve Claude workspace state in every
    container";
    `uv run pytest scripts/tests/test_preapprove_claude_workspace.py` 6 passed,
    4 of which fail against the previous script and action.

### Task 4: Repoint remaining spec references

**Files:** Modify: `.devcontainer/scripts/setup-gh-credential-helper.sh`

- [x] Its comment points at `spec/devcontainer-git-credentials`;
  `grep -rn 'devcontainer-agent-auth' .devcontainer scripts` prints nothing.
  - **Evidence:** commit "Point the gh credential helper at its new spec"
    (`setup-gh-credential-helper.sh:2`); the `grep` prints nothing;
    `uv run pytest scripts/tests/test_setup_gh_credential_helper.py` 6 passed.

### Task 5: Record the shared-volume refresh race

**Files:** Modify: `docs/knowledge/data/architecture/agent-auth-persistence.md`

- [ ] Add a consequence: worktrees on one host share a single credential file,
  so each sees the others' refreshes, but two Claude processes refreshing at the
  same moment can race on the single-use refresh token
  (anthropics/claude-code#21765); a known limitation. Add the issue URL to
  `sources`; `iwe schema validate` passes.

### Task 6: Refresh the codebase map

**Files:** Modify: `docs/knowledge/data/codebase/devcontainer.md`,
`docs/knowledge/data/codebase/devcontainer/scripts.md`,
`docs/knowledge/data/codebase/flow-devcontainer-lifecycle.md`, and any other doc
`stale-map-docs.py` reports

- [ ] Run `/agentdev:iwe-map` refresh so the map no longer lists the seed
  scripts, the transfer directory, or `spec/devcontainer-agent-auth`;
  `stale-map-docs.py` ends `RESULT=SUCCESS`.

## Spec changes

Retire [Devcontainer agent authentication and Claude Remote
Control](../spec/devcontainer-agent-auth.md) (`iwe delete` at Ship, replaced in
`data/spec.md` by the two new specs). Its `## Setup procedure` steps 1–3 and
`## Rotation and recovery` go with it; the `## Diagnose Login expired` section
moves to `spec/claude-remote-control` with its seed references removed.

``` markdown
## REMOVED Requirements

### Requirement: native authentication enters through Coder user secrets
Retired: shared credential snapshots break on refresh-token rotation; seeding is deleted.

### Requirement: initialization uses a private transfer directory
Retired with seeding.

### Requirement: live credentials are seeded once
Retired with seeding; credentials come only from a login inside a container,
persisted in the shared volume.

### Requirement: a Claude OAuth snapshot has one refresh owner
Retired: no mechanism distributes snapshots any more.

### Requirement: Remote Control is opt-in and idempotent
Moved, with a changed gate, to `spec/claude-remote-control`.

### Requirement: autostart pre-approves first-run Claude state
Moved, no longer tied to autostart, to `spec/claude-remote-control`.

### Requirement: Git identity reaches the nested container
Moved unchanged to `spec/devcontainer-git-credentials`.

### Requirement: HTTPS git uses the gh login
Moved unchanged to `spec/devcontainer-git-credentials`.
```

New `spec/claude-remote-control`:

``` markdown
## ADDED Requirements

### Requirement: Remote Control autostarts only on a live claude.ai login

`claude-remote-control-start.sh` SHALL start `claude /remote-control` in
exactly one detached tmux session named `claude-remote` only when
`AGENTDEV_CLAUDE_AUTOSTART=1` and `claude auth status --json` reports
`loggedIn: true` with `authMethod: "claude.ai"`. It runs from
`postStartCommand.sh` and may be run by hand. Repeated or concurrent runs SHALL
reuse a live session rather than create another. It SHALL skip startup when
`claude` or `tmux` is unavailable. The Claude process SHALL NOT receive
`CLAUDE_CODE_OAUTH_TOKEN`.

#### Scenario: the container restarts

- **WHEN** post-start runs while `claude-remote` is already live
- **THEN** it leaves the existing session running and creates no additional
  Claude process.

#### Scenario: the saved login has expired

- **WHEN** autostart is enabled and the credential file exists but
  `claude auth status --json` reports `loggedIn: false`
- **THEN** no session is started and the script exits successfully.

#### Scenario: only a setup token is available

- **WHEN** `claude auth status --json` reports `loggedIn: true` with an
  `authMethod` other than `claude.ai`
- **THEN** no session is started.

#### Scenario: the operator logs in after the container started

- **WHEN** an operator completes `/login` and runs the script by hand
- **THEN** `claude-remote` starts without a container restart.

### Requirement: every container pre-approves first-run Claude state

Unless `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` is non-empty, post-create SHALL record
in Claude's state file (`~/.claude.json`, written through its symlink into the
persistent volume) that onboarding is complete, the Remote Control confirmation
was seen, and the workspace is trusted. It SHALL set
`enableAllProjectMcpServers` in the workspace's `.claude/settings.local.json`
and SHALL keep any existing `disabledMcpjsonServers` list. Existing keys in
both files SHALL be preserved. The CI responder SHALL set the opt-out.

#### Scenario: a new workspace autostarts Remote Control

- **WHEN** a workspace is created with autostart enabled and a valid claude.ai
  login in the shared volume
- **THEN** `claude-remote` reaches `/rc active` with no terminal interaction and
  every project `.mcp.json` server enabled except those listed in
  `disabledMcpjsonServers`.

#### Scenario: autostart is not enabled

- **WHEN** a workspace is created without `AGENTDEV_CLAUDE_AUTOSTART`
- **THEN** the first interactive `claude` session shows no onboarding, trust,
  or project-MCP prompt.

#### Scenario: the CI responder runs the lifecycle scripts

- **WHEN** `postCreateCommand.sh` runs with `AGENTDEV_SKIP_CLAUDE_PREAPPROVE`
  set
- **THEN** neither `~/.claude.json` nor `.claude/settings.local.json` is
  modified.
```

New `spec/devcontainer-git-credentials`: the two requirements
`Git identity reaches the nested container` and `HTTPS git uses the gh login`
carried over verbatim from the retired spec, plus its step-2 paragraph on
supplying the `GIT_*` values through Coder.

## Verification

- `uv run pytest scripts/tests/test_claude_remote_control_start.py scripts/tests/test_preapprove_claude_workspace.py scripts/tests/test_setup_gh_credential_helper.py`
- The Task 1 `grep` prints nothing; `shellcheck` and pre-commit pass on every
  edited script.
- In this container, `.devcontainer/scripts/claude-remote-control-start.sh` with
  `AGENTDEV_CLAUDE_AUTOSTART=1` starts or reuses `claude-remote`
  (`tmux list-sessions -F '#{session_name}'`), and with `CLAUDE_CONFIG_DIR` and
  `CLAUDE_SECURESTORAGE_CONFIG_DIR` pointed at empty directories prints the
  not-logged-in skip (manual).
- A devcontainer rebuild completes with no `/run/agentdev-auth-seed` mount
  (`docker inspect` or `findmnt /run/agentdev-auth-seed` finds nothing).
- After merge, the next CI responder run completes and its lifecycle step logs
  the pre-approval skip.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- The shared `agentdev-agents-auth` volume and `link-codex-auth.sh`.
- Any mechanism that refreshes or distributes credentials across workspaces.
- Retrying autostart after a later `/login`; the script is run by hand.
- Changing `CLAUDE_SECURESTORAGE_CONFIG_DIR` or Claude's credential location.

## Key references

Verified anchor points (line numbers as of 2026-10-09):

- `.devcontainer/docker-compose.yml:69-73` — `AGENTDEV_CLAUDE_AUTOSTART` and
  `GIT_*` passthroughs (kept)
- `.devcontainer/scripts/postCreateCommand.sh:72` —
  `preapprove-claude-workspace.sh` call
- `.devcontainer/scripts/postStartCommand.sh:25` —
  `claude-remote-control-start.sh` call
- `.devcontainer/scripts/claude-remote-control-start.sh:16-32` — login gate
- `.devcontainer/scripts/claude-remote-control-start.sh:43-44` — tmux start
  without `CLAUDE_CODE_OAUTH_TOKEN`
- `.devcontainer/scripts/preapprove-claude-workspace.sh:3,6,50` — spec comment,
  opt-out gate, MCP comment
- `.devcontainer/scripts/setup-gh-credential-helper.sh:2` — spec comment
- `.github/actions/run-claude-responder/action.yml:95-107` — lifecycle step env
- `scripts/tests/test_claude_remote_control_start.py:32,69,88` —
  `run_with_fake_tmux`, start and skip tests
- `scripts/tests/test_preapprove_claude_workspace.py:67,75,83,89` —
  `test_runs_without_autostart`, `test_skips_when_opted_out`,
  `test_post_create_runs_after_state_symlink`, `test_ci_responder_opts_out`
- `docs/knowledge/data/spec/devcontainer-agent-auth.md:36-155` — requirements
  being retired or moved
