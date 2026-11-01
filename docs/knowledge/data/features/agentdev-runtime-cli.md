---
type: feature
stage: implemented
description: One agentdev-runtime Python CLI, installed in the runtime images as an embedded uv tool package, replaces the lifecycle shell scripts, the Xpra launcher, and the firewall script, and the Codex Cloud bootstrap is removed.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T02:20:03Z
sources:
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: .devcontainer/scripts/runtime-health.sh
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: ansible/roles/validate_agent_files/tasks/main.yml
- resource: docker/desktop/start-xpra.sh
- resource: ansible/roles/devcontainer_firewall/files/init-firewall.sh
- resource: .codex/setup-codex-cloud.sh
- resource: .github/actions/run-claude-responder/action.yml
---

# agentdev-runtime CLI

## Purpose

The runtime images carry their lifecycle as shell scripts that call one another
by path and each re-read the environment with their own defaults, beside a
Python supervisor that models the same settings and writes the state those
scripts parse back with jq. One Python package with one CLI gives the runtime a
single settings model, a single state schema, and an installed,
dependency-complete distribution in place of scripts that resolve dependencies
from PyPI at container start.

## Behaviour

- `agentdev-runtime` is the console script of the `agentdev_runtime` package
  under `py_packages/`, installed into `agentdev-deploy` and
  `agentdev-devcontainer` as an isolated uv tool on the system interpreter, the
  way `validate_agent_files` is installed. `agentdev-base` stays
  lifecycle-neutral and does not carry it.
- Every supervised program, lifecycle phase, probe, and operator command is a
  subcommand: `supervisor`, `health`, `bootstrap`, `firewall`, `docker`,
  `keyring`, `xpra`, `cbm`, `state`, `catalog`, `workspace`, `project`, `git`,
  `remote-control`, `opencode`, `coder`, `lifecycle`, and `doctor`. The image
  `ENTRYPOINT`, `HEALTHCHECK`, supervisord program commands, and the
  `devcontainer.metadata` lifecycle commands name these subcommands.
- The package pins `supervisor`, `json5`, and `pyyaml`. The images stop
  installing supervisor from apt, and no runtime step resolves a dependency over
  the network.
- The behaviour behind each command is unchanged: profiles, probes, recovery
  budgets, readiness, the failure latch, the catalog override, CBM daemon
  handling, Remote Control, and the firewall's default-DROP policy with its
  self-verification.
- One detection is added: `project hooks` warns about each `language: system`
  pre-commit hook whose executable is missing, and `doctor` requires `gitleaks`
  and `actionlint`, as [Bug: a workspace on a pre-pin image has no gitleaks or
  actionlint and nothing says
  so](../bugs/workspace-image-lacks-hook-binaries.md) asks.
- A container with no supervisor socket, such as a GitHub Actions `container:`
  job, runs `agentdev-runtime lifecycle ready --no-wait`, which starts only the
  CBM daemon before the per-start repairs. The shell starters for keyring,
  firewall, and Xpra outside the supervisor are removed.
- The runtime verifies its installed distribution against the wheel's recorded
  file hashes in place of a sha256 manifest over `/opt/agentdev-runtime`, which
  no longer exists.
- The Xpra launcher and the firewall script move into the package. The firewall
  needs no sudoers entry, since it runs as root from the bootstrap.
- The Codex Cloud bootstrap `.codex/setup-codex-cloud.sh` and every reference to
  it are removed.

## Edge cases

- A derived image that edits a file in the tool environment fails the
  bootstrap's distribution check, as a patched `/opt/agentdev-runtime` fails
  today.
- A `container:` job has no supervisor and no mounts;
  `lifecycle ready --no-wait` tolerates the missing mounts and starts CBM
  itself.
- Operator commands named in the READMEs (`runtime-health.sh status`,
  `runtime-supervisor.py retry`) are renamed; a reader following old text gets a
  missing-file error, never silent success.
- A consumer that still copies `.devcontainer/scripts/` follows the consumption
  guide's migration to the image-provided lifecycle; no shims keep the old names
  alive.

## Open questions

- Whether in-repo CI consumers should run supervisor-mode images, so the
  no-supervisor start can be removed entirely, is a separate exploration.
