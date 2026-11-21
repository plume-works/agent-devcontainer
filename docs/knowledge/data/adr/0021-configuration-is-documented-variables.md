---
type: adr
stage: accepted
---

# Configuration is documented variables, never shell code

The runtime reads its configuration only from the variables that
`agentdev_runtime.settings` documents. A consumer extends the runtime only
through these variables and the hook directories of the image, under
`/etc/agentdev/hooks/`. The runtime splits each variable that names a command
into a list of arguments and runs it without a shell.

## Considered Options

- Command strings that a shell evaluates. Rejected: each configured value then
  becomes shell code, with the risks of quotes and injection.

## Consequences

- The runtime refuses a hook directory in the workspace, so a mounted repository
  cannot add a hook.
