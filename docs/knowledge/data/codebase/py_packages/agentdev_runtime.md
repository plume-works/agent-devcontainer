---
type: codebase
description: The agentdev_runtime package and its agentdev-runtime CLI, which both runtime images install as a uv tool — PID 1 and its supervisor, the health probes, every supervised service, the bootstrap and firewall, the Dev Container lifecycle commands, and the doctor report.
source: py_packages/agentdev_runtime
source_digest: sha256:2a31381cb92d1731484c54d40425f03e8a31a1a34b9985728adc3f7d9297aa8a
verified:
  by: claude-code/opus-5.5
  at: 2026-10-31T07:49:53Z
stale_after: 2027-01-29
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T07:49:53Z
sources:
- id: code
  resource: py_packages/agentdev_runtime
---

# agentdev_runtime package

One Python package with one console script, `agentdev-runtime` (`pyproject.toml`
`[project.scripts]`). `agentdev-devcontainer` and `agentdev-deploy` install it
with `uv tool install` into `/opt/uv-tools`, with the entry point on
`/usr/local/bin`; it pins `supervisor`, `setuptools<85`, `tomlkit`, `json5`, and
`pyyaml`. Each module is one subcommand group; `cli.py` dispatches every group
except `settings` with its arguments untouched.

## Public surface

| Subcommand                                                                            | Module                                                                 | Does                                                                                                     |
| ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `supervisor run\|control\|exec\|retry`                                                | `supervisor.py`                                                        | PID 1, the controller event listener, the program wrapper that keeps a failure record, the retry request |
| `health <service>\|ready\|status`                                                     | `health.py`                                                            | per-service probes, the aggregate readiness the healthcheck reads, the status report                     |
| `bootstrap`                                                                           | `bootstrap.py`, `integrity.py`                                         | the root bootstrap: `RECORD` integrity, account and storage per profile, then the firewall               |
| `firewall apply`                                                                      | `firewall.py`                                                          | the opt-in egress firewall                                                                               |
| `docker run\|prune`, `keyring …`, `xpra …`, `cbm …`, `opencode …`, `remote-control …` | one module each                                                        | the supervised services and their probes                                                                 |
| `workspace …`, `project sync\|hooks`, `git …`, `state …`, `catalog install\|complete` | `workspace.py`, `project.py`, `git.py`, `agent_state.py`, `catalog.py` | deploy phases, the project environment, Git trust and credentials, agent state, catalog registration     |
| `lifecycle created\|ready\|attached\|hooks`                                           | `lifecycle.py`, `hooks.py`                                             | the Dev Container phase commands and the image hook runner                                               |
| `coder start`, `doctor`, `settings`                                                   | `coder.py`, `doctor.py`, `settings.py`                                 | the Coder agent start, the health report, the settings table                                             |

## How it works

`settings.py` declares every environment variable the runtime reads with one
default, keyed by profile where deploy differs; `Settings` resolves them once.
`state.py` owns `state.json`, the retry request, and the failure record.
`supervisor run` validates the settings, runs `bootstrap` as root, then runs
supervisord in-process; the `control` listener starts each profile's services in
dependency order (`DEPLOY_SERVICES`, `DEVCONTAINER_SERVICES`), gates them on
`health <service>`, and recovers within a budget. Every program in the shipped
`supervisord.conf` files is
`agentdev-runtime supervisor exec <name> agentdev-runtime …`.
`lifecycle ready --no-wait` is the start of a container with no supervisor: the
CBM daemon, then the per-start repairs.

## Depends on

- [docker](../docker.md) — the Dockerfiles install it and ship the
  `supervisord.conf` it runs; `.devcontainer/firewall-allowlist.txt` is the
  allowlist image copy.
- External tools it runs: supervisord (in-process), `dockerd`, `dbus-daemon`,
  `gnome-keyring-daemon`, `xpra`, `codebase-memory-mcp`, `opencode`, `claude`,
  `codex`, `gh`, `git`, `uv`, `pre-commit`, `tmux`, `iptables`, `ipset`,
  `setpriv`, `useradd`/`groupadd`/`usermod`, `visudo`.

## Invariants & gotchas

- Integrity covers the installed distribution: the image's
  `/usr/local/bin/agentdev-runtime` is a symlink into the tool's environment, so
  a bind mount over it trips the bootstrap's `RECORD` check.
- `settings.Settings.get` refuses an undeclared variable; the README table must
  list every declared one (`tests/test_settings.py`).
- Home-derived defaults follow `HOME`, falling back to `AGENTDEV_HOME`.
- `project hooks` warns, never fails, on a `language: system` hook whose
  executable is missing.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `py_packages/agentdev_runtime/agentdev_runtime/cli.py:124` — `PASSTHROUGH`
  subcommand table; `:167` — `main`
- `py_packages/agentdev_runtime/agentdev_runtime/settings.py:56` — `VARIABLES`;
  `:308` — `Settings`
- `py_packages/agentdev_runtime/agentdev_runtime/supervisor.py:210` —
  `DEPLOY_SERVICES`; `:227` — `DEVCONTAINER_SERVICES`; `:280` — `Controller`;
  `:894` — `run`
- `py_packages/agentdev_runtime/agentdev_runtime/state.py:127` — `current`, the
  stale-heartbeat read
- `py_packages/agentdev_runtime/agentdev_runtime/integrity.py:47` — `verify`
- `py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py:145` — `Deploy`;
  `:345` — `main`
- `py_packages/agentdev_runtime/agentdev_runtime/firewall.py:331` — `apply`
- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py:76` — `created`;
  `:141` — `ready`; `:158` — `attached`
- `py_packages/agentdev_runtime/agentdev_runtime/project.py:46` —
  `missing_executables`
- `py_packages/agentdev_runtime/agentdev_runtime/doctor.py:256` — `main`
