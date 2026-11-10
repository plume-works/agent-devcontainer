# Devcontainer state Specification

## Purpose

Defines where the devcontainer keeps agent credentials, per-instance agent
state, and the Python environment, and which of them devcontainer instances
share.

## Requirements

### Requirement: only Claude Code credentials are shared across instances

The `agentdev-agents-auth` volume SHALL be declared with the literal `name:
agentdev-agents-auth` and `external: true`, mounted at `/root/.agents-auth`,
and created on the host by `devcontainer-init.sh`. `CLAUDE_SECURESTORAGE_CONFIG_DIR`
SHALL point Claude Code's credential store at `/root/.agents-auth/claude`. The
`agentdev-claude` and `agentdev-opencode` volumes SHALL stay Compose-project
scoped, so each worktree, clone, or Codespace keeps its own agent state,
OpenCode logins included.

#### Scenario: a second worktree opens

- **WHEN** a second worktree of a repository starts its devcontainer after the
  first logged in to Claude
- **THEN** Claude Code is logged in, and OpenCode asks for its own login

### Requirement: ~/.claude.json is a link into the agent volume

The create phase SHALL keep `~/.claude.json` as a symlink to
`/root/.claude/claude.json` on the `agentdev-claude` volume, replacing a regular
file found at `~/.claude.json` rather than migrating it.

#### Scenario: a fresh container starts on an existing volume

- **WHEN** the create phase runs in a new container whose home holds a regular
  `~/.claude.json`
- **THEN** `~/.claude.json` becomes a link to the volume's `claude.json`

### Requirement: the Python environment lives on the uv volume

In the devcontainer, `UV_PROJECT_ENVIRONMENT` SHALL be `/uv/venvs/ws-project`, on
the same `/uv` volume as `UV_CACHE_DIR`, and nothing SHALL link it into the
workspace. `agentdev-runtime project sync` SHALL remove a `.venv` that is a
symlink into `/uv/venvs/`, and SHALL report and keep any other `.venv`.

#### Scenario: a checkout holds a legacy .venv link

- **WHEN** project sync runs in a workspace whose `.venv` links into
  `/uv/venvs/`
- **THEN** the link is removed

#### Scenario: a checkout holds a real .venv

- **WHEN** project sync runs in a workspace whose `.venv` is a directory
- **THEN** it is reported and left in place

## Rationale

### Share credentials, isolate path-bearing state

Compose prefixes a volume with its project name unless `name:` is literal, and
that prefix is what isolates instances; for credentials the isolation was the
defect, since every worktree demanded a fresh login. The rest of each agent's
state records absolute workspace paths, so sharing it would point one worktree's
sessions at another's directories. OpenCode v2 keeps logins in its SQLite
database beside its sessions and never writes `auth.json`, so there is nothing
to share; the maintainer accepted a login per worktree. Docker named volumes are
directory-backed, so mounting one at `~/.claude.json` would replace the file with
an empty directory. Worktrees on one host share one Claude credential file, and
claude.ai refresh tokens are single-use, so two concurrent refreshes can race
and leave the loser at `Login expired`; a fresh `/login` in any container
recovers every instance.

### The uv environment is out of tree at a fixed path

uv hardlinks packages from its cache only within one filesystem, and the
workspace bind mount is another one, so an in-tree `.venv` silently copies every
package. The `agentdev-uv` volume is project-scoped, so the path needs no
per-workspace component, and a constant is cheap to repeat in
`UV_PROJECT_ENVIRONMENT` and the four VS Code settings that take a path. Host
checkouts and CI keep an in-tree `.venv`, reached through `uv run` as everywhere.

Rejected:

- **An in-tree `.venv`.** It breaks cache-to-environment hardlinking.
- **A `.venv` symlink to the out-of-tree environment.** A second name for one
  environment that goes stale when the path changes, contradicting `uv run`.
