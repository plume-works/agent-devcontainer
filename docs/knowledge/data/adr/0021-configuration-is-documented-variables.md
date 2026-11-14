---
type: adr
stage: accepted
description: The runtime reads its configuration only from the documented variables, and it runs no configured value through a shell.
---

# Configuration is documented variables, never shell code

The runtime reads its configuration only from the variables that
`agentdev_runtime.settings` documents. A consumer extends the runtime only
through these variables and the hook directories of the image. Two variables
name commands: `AGENTDEV_HEALTH_COMMAND` and `AGENTDEV_BOOTSTRAP_COMMAND`. The
runtime splits each into a list of arguments and runs it without a shell.

## Considered Options

- Command strings that a shell evaluates. Rejected: each configured value then
  becomes shell code, with the risks of quotes and injection.

## Consequences

- `agentdev_runtime.settings` reads each variable one time and gives it one
  default. Where the runtime profiles need different values, the default changes
  with the runtime profile. An empty value gets the default.
- `py_packages/agentdev_runtime/README.md` lists each variable, and
  `py_packages/agentdev_runtime/tests/test_settings.py::test_the_readme_lists_every_variable`
  fails when one is missing.
- A failed hook makes its lifecycle command fail.
  `py_packages/agentdev_runtime/agentdev_runtime/hooks.py::run` refuses a hook
  directory in the workspace, so a mounted repository cannot add a hook.
