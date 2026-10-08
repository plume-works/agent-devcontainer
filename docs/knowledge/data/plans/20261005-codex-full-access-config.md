---
type: plan
created: 2026-10-05
description: Add a postStart script that writes Codex's full-access sandbox and never-approve policy into config.toml, using tomlkit with PEP 723 inline dependencies so it keeps other tools' comment markers and needs nothing from a consumer's pyproject.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-05T12:00:00Z
sources:
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .devcontainer/firewall-allowlist.txt
---

# Configure devcontainer Codex for full access

## Context

Codex command-line sessions in the devcontainer start with Codex's own default
sandbox and approval prompts. The container is the isolation boundary, so the
maintainer wants Codex to run with `sandbox_mode = "danger-full-access"` and
`approval_policy = "never"` there; per the maintainer, Codex does not supply
those settings itself for CLI sessions. The settings belong in
`${CODEX_HOME:-~/.codex}/config.toml`, which is what CLI sessions read.

`config.toml` is shared with codebase-memory-mcp, whose installer owns sections
delimited by comment markers (`# >>> codebase-memory-mcp MCP >>>` …
`# <<< codebase-memory-mcp MCP <<<`) and locates them by those markers. Any
writer of this file must preserve comments.

## Approach

A Python script, `.devcontainer/scripts/configure-codex.py`, runs on every
container start from `postStartCommand.sh`. It parses `config.toml` with
`tomlkit`, sets the two top-level keys, and writes the result atomically through
a temporary file in the Codex home at mode `0600`, with the directory at `0700`.
`tomlkit` round-trips comments and formatting, so the codebase-memory-mcp
markers survive.

The script declares `tomlkit` in PEP 723 inline metadata and runs through
`uv run --script` (shebang `#!/usr/bin/env -S uv run --script`).
`.devcontainer/scripts/` ships to template consumers while `pyproject.toml` is
theirs to rewrite, so the dependency must travel with the script, not with the
project environment. PyPI is already on the firewall allowlist, and
`UV_CACHE_DIR` sits on the persistent `/uv` volume.

Rejected:

- `toml` (`python3-toml` apt or the `toml` PyPI package): its `dump` discards
  comments, erasing codebase-memory-mcp's section markers on every start.
- `tomlkit` as a project dev dependency run through plain `uv run`: a consumer
  whose `pyproject.toml` lacks it fails at container start.
- A shell/awk line edit: not a TOML parser; the maintainer chose a proper Python
  script.
- `codex --dangerously-bypass-approvals-and-sandbox` or an alias: per
  invocation, not a property of the container.

The call goes last in `postStartCommand.sh`, after `link-codex-auth.sh`. Any
position satisfies the ordering constraint (codebase-memory-mcp installs its
sections in postCreate, earlier), and putting it last means a failure here
cannot prevent the firewall, keyring, or Xpra from starting. An unparseable
`config.toml` fails the step loudly rather than being overwritten (assumption: a
corrupt config is better surfaced than replaced).

## Implementation Steps

### Task 1: Add the configure script

**Files:** Create: `.devcontainer/scripts/configure-codex.py`

- [x] Script with `#!/usr/bin/env -S uv run --script`, a PEP 723 block declaring
  `requires-python = ">=3.12"` and `dependencies = ["tomlkit"]`, type hints and
  PEP 257 docstrings, executable bit set. It honors `CODEX_HOME`, creates the
  home at `0700`, loads `config.toml` with `tomlkit.parse` (an empty document
  when absent), sets `sandbox_mode` and `approval_policy` at top level, and
  replaces the file atomically through a `0600` temporary file in the same
  directory.
  - **Evidence:** Commit on branch `codex-full-access-config` adding
    `configure-codex.py` (mode 100755); 2026-10-08 run against a copy of this
    container's `config.toml` added only the two keys above the
    codebase-memory-mcp marker, a second run was byte-identical, modes 700/600.
- [x] `ruff` clean under the repo's `.ruff.toml` (pre-commit hook).
  - **Evidence:** `uv run ruff check` and `ruff format --check` passed on the
    script; pre-commit hooks passed on the Task 1 commit.

### Task 2: Run it on every start

**Files:** Modify: `.devcontainer/scripts/postStartCommand.sh`

- [x] Call `"$script_dir/configure-codex.py"` as the last step, after
  `link-codex-auth.sh`.
  - **Evidence:** Commit on branch `codex-full-access-config` appending the call
    to `postStartCommand.sh`; `shellcheck` and pre-commit passed.

### Task 3: Tests

**Files:** Create: `scripts/tests/test_configure_codex.py` (beside the other
devcontainer script tests)

- [x] pytest cases, each with `CODEX_HOME` pointed at a `tmp_path`: absent
  config is created with both keys and modes `0700`/`0600`; existing other keys,
  tables, and marker comments survive byte-for-byte apart from the two managed
  keys; pre-existing different values are overwritten; a second run is a no-op
  on content.
  - **Evidence:** Commit on branch `codex-full-access-config` adding
    `scripts/tests/test_configure_codex.py`;
    `uv run pytest scripts/tests/test_configure_codex.py` — 4 passed.

### Task 4: Record the decision

**Files:** Create:
`docs/knowledge/data/architecture/codex-full-access-in-devcontainer.md`; Modify:
`docs/knowledge/data/architecture.md`,
`docs/knowledge/data/architecture/template-boundary.md`

- [x] Architecture doc stating the decision (container is the sandbox; Codex CLI
  sessions take the policy from `config.toml` unless a flag overrides it), the
  comment-preservation constraint, the consumer-independence constraint, and the
  rejected alternatives from `## Approach`; linked from `data/architecture.md`.
  - **Evidence:** Commit on branch `codex-full-access-config` adding
    `architecture/codex-full-access-in-devcontainer.md` and its hub link;
    `iwe schema validate` and pre-commit passed.
- [x] Add a `configure-codex.py` row to the `.devcontainer/scripts/` inventory
  table in `data/architecture/template-boundary`.
  - **Evidence:** Same commit adds the row after `link-codex-auth.sh` in the
    `template-boundary` inventory; `iwe schema validate` and prettier passed.

### Task 5: Refresh the codebase map

**Files:** Modify: `docs/knowledge/data/codebase/devcontainer/scripts.md`,
`docs/knowledge/data/codebase/flow-devcontainer-lifecycle.md`

- [x] Run `/agentdev:iwe-map` refresh so the script inventory and the postStart
  sequence list `configure-codex.py`.
  - **Evidence:** Commit on branch `codex-full-access-config` refreshing
    `codebase/devcontainer/scripts`, `codebase/flow-devcontainer-lifecycle`, and
    `codebase/devcontainer`; `stale-map-docs.py` ends `RESULT=SUCCESS`.

## Spec changes

New spec `data/spec/devcontainer-codex-policy` — this change disables Codex's
sandbox, so the contract is stated in full:

``` markdown
## ADDED Requirements

### Requirement: devcontainer Codex runs without sandbox or approval prompts

On every container start, `postStartCommand.sh` SHALL set the top-level keys
`sandbox_mode = "danger-full-access"` and `approval_policy = "never"` in
`${CODEX_HOME:-~/.codex}/config.toml`, leaving the Codex home at mode `0700`
and the file at mode `0600`.

#### Scenario: a container starts with no Codex config

- **WHEN** the container starts and `config.toml` does not exist
- **THEN** `config.toml` exists with both keys set, at mode `0600`

#### Scenario: the config carries other tools' sections

- **WHEN** `config.toml` holds codebase-memory-mcp's marker-delimited sections
- **THEN** every other key, table, and comment survives unchanged

#### Scenario: a session changed the policy

- **WHEN** `sandbox_mode` or `approval_policy` holds a different value
- **THEN** the next container start restores the managed values

### Requirement: the configure step needs nothing from the consumer project

The configure script SHALL declare its own dependencies inline (PEP 723) and
run through `uv`, independent of the workspace `pyproject.toml`.

#### Scenario: a consumer repository without tomlkit

- **WHEN** a template consumer's `pyproject.toml` does not list `tomlkit`
- **THEN** the container start still configures Codex
```

## Verification

- `uv run pytest scripts/tests/test_configure_codex.py`
- `.devcontainer/scripts/configure-codex.py` run by hand in this container, then
  `grep -E '^(sandbox_mode|approval_policy)' ~/.codex/config.toml` shows both
  keys and `grep -c 'codebase-memory-mcp MCP' ~/.codex/config.toml` still counts
  both markers; `stat -c %a ~/.codex/config.toml` prints `600`.
- `codex` CLI session started in the container runs a shell command without an
  approval prompt (manual).
- `shellcheck .devcontainer/scripts/postStartCommand.sh` and the pre-commit
  hooks pass.

## Out of scope

- Codex settings beyond `sandbox_mode` and `approval_policy`.
- Making the policy opt-out or configurable per consumer.
- Adding `toml`/`python3-toml` to `pyproject.toml` or the `dev_tools` apt list.

## Key references

Verified anchor points (line numbers as of 2026-10-05):

- `.devcontainer/scripts/postStartCommand.sh:29-31` — `link-codex-auth.sh` call,
  the new step goes after it
- `.devcontainer/scripts/postStartCommand.sh:9` — `codebase-memory-mcp-start.sh`
- `.devcontainer/firewall-allowlist.txt:30-31` — `pypi.org`,
  `files.pythonhosted.org`
- `docs/knowledge/data/architecture/template-boundary.md:95-111` — tracked
  `.devcontainer/` path inventory
- `docs/knowledge/data/codebase/devcontainer/scripts.md:30` — postStart row
- `docs/knowledge/data/codebase/flow-devcontainer-lifecycle.md:45-49` —
  postStart sequence
