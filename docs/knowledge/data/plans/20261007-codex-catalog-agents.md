---
type: plan
created: 2026-10-07
description: Install every agentdev catalog agent into Codex as a generated TOML agent, at image build and on every Codex reinstall, so skills that dispatch a catalog agent work on Codex.
generated:
  by: claude-code/opus-5-5
  at: 2026-10-07T12:30:00Z
sources:
- resource: .agents/plugins/agentdev/agents
- resource: .devcontainer/scripts/reinstall-agentdev-codex.sh
- resource: ansible/roles/agentic_tools/tasks/install_catalog.yml
- resource: docs/knowledge/data/architecture/module-layout.md
---

# Install the catalog agents into Codex

## Context

Codex never loads the catalog's `agents/<stem>.agent.md` files, so no skill step
that dispatches a catalog agent can run there — see
[Codex never loads the agentdev catalog agents](../bugs/codex-catalog-agents-not-loaded.md).
Codex reads custom agents only as TOML from `.codex/agents/` or
`~/.codex/agents/`, and its plugin manifest has no field that carries them.

[Agent-owned Ship and Implement workflows](20261007-agent-owned-ship-implement.md)
depend on this: their coordinators dispatch catalog agents, which must exist on
all three harnesses.

## Approach

A stdlib-only Python script owned by the catalog,
`.agents/plugins/agentdev/bin/install-codex-agents.py`, installs the agents of
the plugin that ships it (`--plugin-root` overrides it) and writes one TOML
agent per `agents/<stem>.agent.md` into
`${CODEX_HOME:-$HOME/.codex}/agents/agentdev-<stem>.toml`:

- `name` — `<stem>`, the same name the OpenCode bridge gives the subagent.
- `description` — the file's `description`.
- `sandbox_mode` — `workspace-write` when `tools:` grants `Edit` or `Write`,
  otherwise `read-only`.
- `developer_instructions` — the file's body.

It then removes every `agentdev-*.toml` in that directory it did not just write,
so a dropped or renamed agent disappears, and touches no other file. Both
install paths call it: `reinstall-agentdev-codex.sh` after `codex plugin add`,
and the image build's Codex install in Ansible. The script lives in the catalog
so each catalog version installs its own agents.

Rejected:

- **Commit TOML under `.codex/agents/` in this repository.** A second copy of
  every agent kept in sync by hand, project-scoped so a consumer never gets it,
  and exactly the trampoline `architecture/module-layout` rules out.
- **Generate from TypeScript, sharing the OpenCode bridge's parser.** The bridge
  must stay free of runtime dependencies and runs inside OpenCode; the catalog's
  other install-time helpers and their tests are Python.

Assumption: the `agentdev-` filename prefix marks the files this script owns, so
a user-authored file with that prefix would be removed on reinstall.

## Implementation Steps

### Task 1: Generate Codex agents from the catalog

**Files:** Create: `.agents/plugins/agentdev/bin/install-codex-agents.py`,
`.agents/plugins/agentdev/tests/test_install_codex_agents.py`

- [x] Write the generator with the field mapping and stale-file removal in
  `## Approach`, reporting its outcome through `bin/result_codes.py`. Tests
  cover: one TOML per agent that `tomllib` parses back to the source description
  and body; both sandbox modes; removal of a stale `agentdev-*.toml`; a
  non-prefixed file left untouched; a second run producing identical files;
  `CODEX_HOME` honored.
  - **Evidence:** committed with this tick;
    `uv run pytest .agents/plugins/agentdev/tests/test_install_codex_agents.py`
    10 passed, the full plugin suite 124 passed, and `python-lint-check.sh`
    clean on both files.

### Task 2: Install the agents on every Codex reinstall

**Files:** Modify: `.devcontainer/scripts/reinstall-agentdev-codex.sh`

- [x] After `codex plugin add`, run the generator against `$catalog_root`, so
  postCreate installs the staged catalog's agents and postAttach installs the
  workspace's.
  - **Evidence:** committed with this tick; `shellcheck` clean; the script run
    against this checkout installed all five `agentdev-*.toml` agents, and run
    against an `/opt/agentdev` catalog that predates the generator it skipped
    the install and exited 0.

### Task 3: Install the agents at image build

**Files:** Modify: `ansible/roles/agentic_tools/tasks/install_catalog.yml`

- [x] After "Install the plugin for Codex", run the generator against the staged
  catalog root, so an image started without lifecycle hooks has the agents.
  - **Evidence:** committed with this tick; `uv run ansible-lint ansible` and
    `uv run ansible-playbook --syntax-check ansible/playbooks/setup-dev.yml`
    exit 0. The built image is Task 6.

### Task 4: Record the install-time agents in the module layout

**Files:** Modify: `docs/knowledge/data/architecture/module-layout.md`

- [x] Restate the `.agents/plugins/agentdev/` single-source decision so it
  covers the generated Codex agents: the catalog stays the only source, and
  `~/.codex/agents/agentdev-*.toml` is an install-time artifact derived from it,
  never edited or committed.
  - **Evidence:** committed with this tick; `iwe schema validate` passes on the
    edited `data/architecture/module-layout`.

### Task 5: Codex dispatches a catalog agent in the devcontainer

- [x] With the catalog reinstalled through `reinstall-agentdev-codex.sh`,
  `codex exec` lists `durable-knowledge-auditor`, `principal-engineer`, and the
  `tdd-*` agents as spawnable, and a dispatch of `durable-knowledge-auditor` on
  a plan file returns its audit report.
  - **Evidence:** committed with this tick; Codex 0.156.1 after the reinstall
    listed all five catalog agents beside `default`, `explorer`, and `worker`,
    and `codex exec` dispatched `durable-knowledge-auditor` on this plan through
    `spawn_agent`: the child ran the agent file's body under a `read-only`
    sandbox and returned its audit table.

### Task 6: The built image carries the agents without lifecycle hooks

- [x] A container started from a freshly built `agent-desktop` image, with no
  lifecycle hook run, has `~/.codex/agents/agentdev-<stem>.toml` for every
  catalog agent.
  - **Evidence:** committed with this tick; a local
    `docker buildx build -f docker/desktop/agent-desktop.Dockerfile` of commit
    a9924a5 ran "Install the staged catalog agents for Codex", and
    `docker run --entrypoint /bin/bash` on the image, with no lifecycle hook,
    listed one `agentdev-<stem>.toml` per catalog agent: `read-only` for
    `durable-knowledge-auditor`, `workspace-write` for the other four.

## Spec changes

[Catalog lifecycle](../spec/catalog-lifecycle.md) — the install now writes files
Codex reads and removes files it previously wrote:

``` markdown
## ADDED Requirements

## Requirement: Codex receives the catalog agents as generated TOML agents

Every Codex install of the catalog — at image build, by postCreateCommand, and
on attach — SHALL write one `agentdev-<stem>.toml` agent per
`agents/<stem>.agent.md` into `${CODEX_HOME:-~/.codex}/agents/`, named `<stem>`,
carrying the file's description and body, with `sandbox_mode` `workspace-write`
when the agent's tools include `Edit` or `Write` and `read-only` otherwise. It
SHALL remove every `agentdev-*.toml` there that the current catalog does not
produce, and SHALL NOT modify any other file in that directory.

### Scenario: the catalog is installed into Codex

- **WHEN** `reinstall-agentdev-codex.sh` or the image build installs a catalog
  whose `agents/` holds `durable-knowledge-auditor.agent.md`
- **THEN** Codex lists `durable-knowledge-auditor` as a spawnable agent type,
  and dispatching it runs the agent file's body with a read-only sandbox.

### Scenario: an agent is removed from the catalog

- **WHEN** a catalog without `tdd-red.agent.md` is installed over one that had
  it
- **THEN** `agentdev-tdd-red.toml` no longer exists and every other catalog
  agent's file is current.

### Scenario: the user has their own Codex agents

- **WHEN** `~/.codex/agents/` holds `codebase-memory.toml` before an install
- **THEN** the file is unchanged after the install.
```

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_install_codex_agents.py`
- `shellcheck .devcontainer/scripts/reinstall-agentdev-codex.sh`
- `python-lint-check.sh` on the new script and test
- Tasks 5 and 6 are the end-to-end checks on Codex itself.

## Out of scope

- Agent-owned Ship and Implement workflows and the explicit-only gate on Codex
  skills — the next plan.
- Claude Code and OpenCode, which already load the catalog agents.
- Changing any agent's tools or body.

## Key references

Verified anchor points (line numbers as of 2026-10-07):

- `.devcontainer/scripts/reinstall-agentdev-codex.sh:65` — `codex plugin add`
- `.devcontainer/scripts/postCreateCommand.sh:92` — reinstall with the staged
  catalog
- `.devcontainer/scripts/postAttachCommand.sh:14` — reinstall with the workspace
  catalog
- `ansible/roles/agentic_tools/tasks/install_catalog.yml:74` — "Install the
  plugin for Codex"
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:92` — bridge names each
  subagent by `<stem>`
- `.agents/plugins/agentdev/bin/result_codes.py:1` — Python result-code helpers
- `docs/knowledge/data/architecture/module-layout.md:74` — single-source catalog
  decision
- `docs/knowledge/data/spec/catalog-lifecycle.md:18` — install requirement
