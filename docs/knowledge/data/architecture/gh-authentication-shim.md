---
type: architecture
description: gh is authenticated by a transparent PATH wrapper that derives a token from the host's git credential helper on every invocation, replacing a skill that asked the agent to remember an incantation.
generated:
  by: claude-code/opus-5
  at: 2026-09-04T00:00:00Z
sources:
- resource: docker/bin/gh
- resource: ansible/roles/github_cli/tasks/main.yml
- resource: https://github.com/Dr-QP/Dr.QP/pull/415
- resource: https://github.com/Dr-QP/Dr.QP/pull/403
---

# gh authentication shim

## Decision

`gh` authentication is a **wrapper on PATH**, not an instruction an agent has to
follow. `docker/bin/gh` derives `GH_TOKEN` from the host's git credential helper
and execs the real binary. The `github_cli` role bakes it into
`/usr/local/bin/gh`, ahead of `/usr/bin` on the default PATH, and prepends the
live workspace's `docker/bin` so a mounted checkout supersedes the baked-in
copy.

The wrapper's contract:

- an existing `GH_TOKEN` or `GITHUB_TOKEN` is never overwritten, so a CI or
  explicit token always wins;
- extraction is attempted only when a `credential.helper` is actually
  configured, and `git credential fill` runs under `timeout 2`;
- it is silent by default, logging to stderr only under `VERBOSE_GH`, so stdout
  stays clean for anything parsing `gh` output;
- a `GH_WRAPPER_ACTIVE` guard makes it do its work once per process tree;
- it exits 127 with a clear message when the real `gh` is missing.

## Why a wrapper rather than a documented procedure

A documented per-shell procedure places a prerequisite on every shell, and the
failure when it is skipped is an authentication error far from its cause.
Anything that shells out to `gh` without knowing the procedure fails the same
way.

A wrapper moves the work below the interface. Every caller is authenticated,
including tools that invoke `gh` themselves, and no agent action is required.

## Why it must fall through silently

The wrapper runs in environments where the credential trick does not apply — a
headless task runner, CI with its own token. Treating those as errors would make
`gh` unusable exactly where a token is already correctly supplied, so the
absence of a credential helper is a normal path, not a fault.

## Discovering the real binary

The wrapper walks PATH and skips every copy of itself, identified by a marker
string in the file, falling back to `/usr/bin/gh` only as a last resort. Two
copies are normally on PATH at once — the workspace copy and the image-baked one
— so resolving to a fixed path would either break when `gh` moves or make the
wrapper exec itself.

## Consequences

- `gh` behaves as an authenticated command everywhere in the container, which
  means a workflow can call it without an auth step.
- The wrapper is on the image's PATH, so it applies to a plain `docker run` of
  the image, not only to a devcontainer.
- The marker string is part of the wrapper's contract: detection matches the
  bare substring, so every copy on PATH is recognized regardless of which image
  layer it came from.
