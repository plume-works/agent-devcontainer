---
type: architecture
description: The agentdev runtime is one Python package, agentdev_runtime, installed as a uv tool in the two runtime images and run as the agentdev-runtime CLI; its integrity is the installed distribution's RECORD, the firewall runs from the bootstrap, and a container with no supervisor starts only CBM.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T02:20:03Z
sources:
- resource: py_packages/agentdev_runtime/pyproject.toml
- resource: py_packages/agentdev_runtime/agentdev_runtime/cli.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/settings.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/integrity.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: .github/actions/run-claude-responder/action.yml
---

# agentdev runtime package

## Decision

The runtime of the `agentdev-devcontainer` and `agentdev-deploy` images is one
Python package, `py_packages/agentdev_runtime/`, with one console script,
`agentdev-runtime`. PID 1 and its supervisor, the health probes, every
supervised service, the lifecycle commands, the bootstrap, the firewall, and
Xpra are subcommands of that one CLI, grouped by the runtime's concerns.

Both images install it the way the `validate_agent_files` role installs the
validator: `uv tool install --reinstall --python /usr/bin/python3` from the
build context, into `/opt/uv-tools` with the entry point on `/usr/local/bin`,
with no cache and no interpreter download. The package pins `supervisor` and its
`setuptools<85` requirement, `json5`, and `pyyaml`, so the images carry no apt
`supervisor` and nothing resolves a dependency at container start.
`agentdev-base` stays lifecycle-neutral and never carries it.

`agentdev_runtime.settings` parses every environment value the runtime reads,
once, with one default per variable, keyed by profile where the profiles differ;
the package README lists them. One state module owns the `state.json`,
retry-request, and failure-record shapes for writer and reader alike.

## Integrity

A derived image that replaced, added, or removed a runtime file would run
lifecycle code nobody tested. Before the bootstrap does anything else it checks
the installed `agentdev_runtime` distribution against its `RECORD`: every
recorded file must hash as recorded, and no file may sit in the package's
installed directories that `RECORD` does not name, bytecode aside. A failure
refuses to start and names the supported extension points, the hook directories
and documented environment. A source checkout, whose egg-info records nothing,
is not checked. The check catches accidental or partial edits and is not a
security boundary: an image that deletes the distribution's metadata or rewrites
its `RECORD` passes it.

The image's entry point `/usr/local/bin/agentdev-runtime` is a symlink into the
tool's environment, so a bind mount over it replaces a recorded file; a test
that needs to swap one phase points `AGENTDEV_SUPERVISOR_CONFIG` at its own
configuration instead.

## Firewall

`agentdev-runtime firewall apply` runs as root from the bootstrap in both
profiles, before supervisord starts `dockerd`, so the flush keeps the engine's
rules and no sudoers entry is needed. The `devcontainer_firewall` Ansible role
installs only `iptables` and `ipset`; it carries no script and no sudoers entry.
A set `FIREWALL_ALLOWLIST` names the allowlist in both profiles. Unset, a Dev
Container reads its checkout's allowlist when present and the image copy
otherwise, and deploy reads the image copy.

## A container with no supervisor

A GitHub `container:` job runs no image entrypoint and accepts no `--entrypoint`
option, and `claude-code-action` is a composite action that runs in the job's
own runtime, so the supervisor can never be PID 1 there. Such a job runs
`agentdev-runtime lifecycle created`,
`agentdev-runtime lifecycle ready --no-wait`, and
`agentdev-runtime lifecycle attached`. `ready --no-wait` is one function: start
the CBM daemon, then the per-start repairs. Nothing else starts: a review job
needs CBM and the checkout's catalog, and never the keyring, the firewall, or a
desktop.

## Rejected alternatives

- **Loose standard-library scripts on the system interpreter.** Keeps either a
  PyPI fetch at container start or an apt dependency hunt, and keeps the
  per-file sha256 manifest.
- **Bash shims under the old `/opt/agentdev-runtime/*.sh` names.** Ruled out in
  favour of one CLI; nothing outside the images calls those paths.
- **Porting the legacy no-supervisor starters.** Preserves a second start path
  with its own keyring, firewall, and Xpra handling that no caller needs.
- **Keeping `init-firewall.sh` as bash behind a Python wrapper.** Ruled out; the
  policy is one module with its rule sequence under test.
- **Starting the supervisor in the background inside the responder's container
  job.** Needs a privileged job container for the profile's core `dockerd` and
  buys only the deletion of the one no-supervisor function.
- **Running the responder as a host job through `devcontainers/ci`.** Gives the
  supervisor PID 1 but loses `claude-code-action` and its `claude[bot]`
  authentication.
