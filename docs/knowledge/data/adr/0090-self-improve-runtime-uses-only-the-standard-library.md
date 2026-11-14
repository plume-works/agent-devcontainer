---
type: adr
stage: accepted
description: The self-improve runtime imports only the Python standard library, and one executable file is the entry point for each hook and skill.
---

# The self-improve runtime uses only the standard library

The hooks of `self-improve` run in the environment of Claude Code. Each hook
except the `Stop` hook has a time limit of five seconds. The hooks must let the
session continue when they fail. A third-party import needs a step that installs
the package, in the code that must be the most reliable. As a result, the
runtime imports only the standard library, and
`.agents/plugins/self-improve/agent-code/si` is the one entry point for each
hook and skill.

## Considered Options

- Third-party packages that the plugin installs when it needs them. Rejected:
  each failed installation then needs an alternative procedure, in the code that
  must not fail.
- One executable file for each operation. Rejected: each file then repeats the
  entry logic that lets a failed hook continue, which is the most important
  code.
- A `pyproject.toml` for the plugin, as `py_packages/validate_agent_files/` has.
  Rejected: that package has its own releases, and the plugin does not.

## Consequences

- `.agents/plugins/self-improve/tests/unit/test_no_runtime_deps.py` reads each
  runtime import and fails on an import outside the standard library.
- `.agents/plugins/self-improve/agent-code/si` uses the first Python 3.12 or
  later interpreter that it finds. A hook can get a shell where `python3` is an
  old virtual environment.
