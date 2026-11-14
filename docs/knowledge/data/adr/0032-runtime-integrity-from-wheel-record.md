---
type: adr
stage: accepted
description: The runtime refuses to start when its installed files are different from the RECORD file of the installed wheel.
---

# The wheel RECORD is the integrity record of the runtime

A derived image that replaces, adds, or removes a runtime file runs lifecycle
code that nobody tested. For this reason, `agentdev_runtime.integrity::verify`
compares the installed files with the `RECORD` file of the installed wheel, and
the runtime refuses a difference. The refusal tells the user to use the hook
directories and the documented environment variables.

## Considered Options

- A checksum file that the image build writes for each file. Rejected: it is a
  second record of the data that `RECORD` already holds, and it needs its own
  build step.

## Consequences

- The bootstrap does the check before all other work. Each file in `RECORD` must
  have its recorded hash, and the installed directories of the package must hold
  no other file. The check ignores Python bytecode.
- The check ignores a source checkout, because its egg-info records no file.
- The check finds accidental and partial edits. It is not a security boundary:
  an image that deletes the metadata of the package or writes a new `RECORD`
  passes it.
- `/usr/local/bin/agentdev-runtime` is a symbolic link into the environment of
  the tool, so a bind mount on it replaces a recorded file. A test that must
  replace the program of one service sets `AGENTDEV_SUPERVISOR_CONFIG` to its
  own configuration.
