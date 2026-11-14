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
- `--tools ""` removes each built-in tool, and `--disallowedTools "*"` removes
  each MCP tool. The reviewer runs with no hooks, so the `Stop` hook of the
  plugin does not run in the review.
- The orchestrator collects the owner paths and summaries and puts them into the
  input, because the reviewer cannot read a file.
- The environment of the reviewer sets `SELF_IMPROVE_REVIEWER=1`, so a session
  that the reviewer starts does not look for a lesson. It does not hold
  `SELF_IMPROVE_STATE_DIR` or `CLAUDE_PLUGIN_DATA`.
- `SELF_IMPROVE_REVIEW_EFFORT` sets the effort. An empty value removes an
  inherited `CLAUDE_CODE_EFFORT_LEVEL`, so the review runs at the default of the
  CLI.
