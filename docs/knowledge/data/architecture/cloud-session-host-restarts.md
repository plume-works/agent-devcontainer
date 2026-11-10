---
type: architecture
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

## Closing

The idle reclaim is the platform's, and nothing in this repository changes it.
The response is to make a reboot cheap rather than to prevent it. A toolchain
that lived only in a devcontainer made every boot restore the host `dockerd`, a
relay to the moved agent proxy port, and the container before any tool ran, and
an agent learned of the reboot only when a Docker call failed. Cloud sessions
therefore run no Docker and no devcontainer: [Cloud session host
toolchain](cloud-session-host-toolchain.md) provisions the toolchain on the
host's disk, which a reboot keeps.
