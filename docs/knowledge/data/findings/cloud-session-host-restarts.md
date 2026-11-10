---
type: finding
description: A Claude Code cloud session's host is reclaimed after a few idle minutes and cold-boots on the next inbound event, keeping its disk and losing every process; the cost lands on whatever must be restarted on each boot.
sources:
- resource: .claude/startup.py
- resource: .claude/CLAUDE.cloud.md
- resource: https://code.claude.com/docs/en/claude-code-on-the-web
---

# Cloud session host restarts

## Measurement

Transcripts of every cloud session from 2026-11-03 to 2026-11-05, about 45 host
boots across 22 sessions, were checked against `uptime`, the worker handoff
events, and the commands running at the time.

- Every reboot followed an idle stretch: between turns, or while a turn waited
  on an `AskUserQuestion` answer. None interrupted a running command, image
  build, `docker pull`, test run, or subagent.
- The boot lands 0–2 minutes before the next inbound event: a user message, an
  answer to a pending question, a pull request event, or `/compact`.
- Idle stretches of 5 minutes or more with nothing running usually ended in a
  reboot; a 3.5-minute one did not. A background command kept the host up
  through quiet stretches of 20–40 minutes.
- A session kept in focus in the app still rebooted after about 10 idle minutes.

The host is a Firecracker VM with 4 vCPUs, 15 GiB of RAM, no swap, and a fixed
per-session disk allowance that `df` does not show.

## Hypotheses eliminated

- **Memory exhaustion.** No OOM kill, `Killed`, or exit 137 appears in any
  transcript, and a fresh boot used 1.2 of 15 GiB.
- **Crashes under load.** No reboot happened while work was running.
- **Full disk.** The disk allowance ran out four times, each during
  multi-architecture image pulls; no reboot followed directly.
- **The session losing focus.** A session in focus rebooted all the same.

What remains is the platform reclaiming an idle worker and starting a fresh one
when the next event arrives.

## What a reboot keeps and loses

- **Kept:** the whole disk — the checkout, `./.tmp`, Docker images, stopped
  containers and volumes, and `/var/run` with its pid files.
- **Lost:** every process — the host `dockerd`, the agent proxy relay, the
  devcontainer, and any background command.
- **Moved:** the agent proxy's loopback port changes on each boot.

## Consequences for the devcontainer setup

Every reboot has to restore the host `dockerd`, the proxy relay, and the
devcontainer before a tool runs, because the toolchain lives only in the
container. [Cloud session
devcontainer](../../../../openspec/specs/cloud-session-devcontainer/spec.md#rationale)
records how `.claude/startup.py resume` restores them and the faults it already
handles: the moving proxy port, a container created without the session's
environment, and stale `docker.pid` and `containerd.pid` files.

Two costs remain with that design:

- **Late detection.** The reboot happens just before a turn starts, but an agent
  learns of it only when a Docker or `devcontainer exec` call fails. A
  `devcontainer exec` that fails without output lets a turn carry on as if its
  tools had run.
- **Proxy relay down with the container up.** In one session, `git push` and
  `gh` inside a running devcontainer failed with `Proxy CONNECT aborted` after
  three reboots until `startup.py resume` was run by hand. The likely cause, not
  confirmed, is that the session's branch predated the `SessionStart` hook that
  runs `resume`.

## Closing

The idle reclaim is the platform's, and nothing in this repository changes it.
The response is to make a reboot cheap rather than to prevent it: [Cloud session
host toolchain](../features/cloud-session-host-toolchain.md) proposes
provisioning the toolchain on the session host itself, keeping Docker and the
devcontainer for image builds and tests only.

The startup this finding constrains is specified in [Cloud session
devcontainer](../../../../openspec/specs/cloud-session-devcontainer/spec.md).
