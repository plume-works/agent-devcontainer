---
type: adr
stage: accepted
---

# Catalog scripts have no file extension

An executable catalog script under a plugin's `bin/` or `skills/*/agent-code/`
has no `.py` extension, so it can only be run by its path. Run through
`python3`, a script misses its plugin's uv project and the `agentdev-lib`
package that ADR-0105 puts there; an extensionless file does not invite that
call. The shebang is `#!/usr/bin/env -S uv run --quiet --script`, because
`uv run` hands a path without `.py` back to the shell and the script would
invoke itself again. A module that scripts import keeps `.py` and has no
shebang. The maintainer made this decision.

## Consequences

- Tools that classify files by extension do not see these files as Python.
  `.ruff.toml` and the ruff hooks in `.pre-commit-config.yaml` include them by
  path, and a test loads one as a module through `SourceFileLoader`.
