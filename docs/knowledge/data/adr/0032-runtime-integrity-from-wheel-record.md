---
type: adr
stage: accepted
---

# The wheel RECORD is the integrity record of the runtime

A derived image that replaces, adds, or removes a runtime file runs lifecycle
code that nobody tested. For this reason, `agentdev_runtime.integrity@verify`
compares the installed files with the `RECORD` file of the installed wheel, and
the runtime refuses a difference. The refusal names the file and directs the
consumer to the hook directories under `/etc/agentdev/hooks/` and the documented
environment variables instead.

## Considered Options

- A checksum file that the image build writes for each file. Rejected: it is a
  second record of the data that `RECORD` already holds, and it needs its own
  build step.

## Consequences

- The check finds accidental and partial edits. It is not a security boundary: a
  derived image that deliberately deletes the metadata of the package or
  rewrites its `RECORD` passes it.
- `/usr/local/bin/agentdev-runtime` is a symbolic link into the environment of
  the tool, so a bind mount on it replaces a recorded file. A test that must
  replace the program of one service sets `AGENTDEV_SUPERVISOR_CONFIG` to its
  own configuration.
