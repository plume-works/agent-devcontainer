---
type: adr
stage: accepted
description: The self-improve reviewer runs with no tools and no hooks, and gets its effort level from an environment variable, not from a flag.
---

# The self-improve reviewer holds no tools

The reviewer reads all of its evidence on standard input. It runs with each tool
removed, all hooks disabled, and one turn. A process with no tools has nothing
to limit, so its isolation does not depend on a correct list of permitted paths.

## Considered Options

- A read-only list of the files that the reviewer can read. Rejected: it limits
  what a tool can open, which is weaker than no tool.
- The `--effort` flag. Rejected: a CLI that does not know the flag stops each
  review, and a failed review shows nothing. The CLI does not use an unknown
  environment variable, so the review runs at the default effort.

## Consequences

- `.agents/plugins/self-improve/selfimprove/reviewer.py::build_command` sets the
  flags, and
  `.agents/plugins/self-improve/selfimprove/reviewer.py::build_environment` sets
  `CLAUDE_CODE_EFFORT_LEVEL`.
