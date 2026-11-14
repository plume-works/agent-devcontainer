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

- The check finds accidental and partial edits. It is not a security boundary.
