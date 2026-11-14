---
type: adr
stage: accepted
description: The runtime reads its configuration only from the documented variables, and it runs no configured value through a shell.
---

# Configuration is documented variables, never shell code

The runtime reads its configuration only from the variables that
`agentdev_runtime.settings` documents. Two variables name commands:
`AGENTDEV_HEALTH_COMMAND` and `AGENTDEV_BOOTSTRAP_COMMAND`. The runtime splits
each into a list of arguments and runs it without a shell.

## Considered Options

- Command strings that a shell evaluates. Rejected: each configured value then
  becomes shell code, with the risks of quotes and injection.
