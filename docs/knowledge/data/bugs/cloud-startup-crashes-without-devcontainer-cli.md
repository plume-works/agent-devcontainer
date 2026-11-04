---
type: bug
description: On a fresh Claude Code cloud host, .claude/startup.py crashed while checking the devcontainer CLI version, so it never installed the CLI and the devcontainer never came up.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-04T03:10:00Z
sources:
- resource: .claude/startup.py
- resource: scripts/tests/test_cloud_startup.py
stage: done
severity: high
---

# Bug: cloud startup crashes before installing the devcontainer CLI

## Symptom

The environment setup script of a fresh Claude Code cloud session fails right
after `==> Bringing up devcontainer` with
`startup: error: [Errno 2] No such file or directory: 'devcontainer'`. The
devcontainer never starts, so no project tool, `git commit`, or `git push` works
until someone runs the startup by hand.

## Reproduction

1. Start a Claude Code cloud session on a host whose `PATH` has no
   `devcontainer` executable.
2. Let the environment run `.claude/startup.py setup`, or run
   `.claude/startup.py resume` with the devcontainer not running.
3. The run exits 1 at `Bringing up devcontainer` with the `[Errno 2]` error.

## Root cause

`install_devcontainer_cli()` installs the CLI only when
`output('devcontainer', '--version')` does not report the pinned version.
`output()` was documented to return an empty string when its command fails, but
it called `subprocess.run` without handling `FileNotFoundError`. A missing
executable raised instead of reading as a failed command, so the install step
that would have provided the executable never ran.

## Fix

`output()` returns an empty string when the command is not installed, so the
version check reads a missing CLI as outdated and installs it.
`test_output_of_a_missing_command_is_empty` in
`scripts/tests/test_cloud_startup.py` covers the missing-command case.
