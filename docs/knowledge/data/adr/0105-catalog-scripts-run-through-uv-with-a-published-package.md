---
type: adr
stage: proposed
supersedes:
- adr/0040-catalog-scripts-are-standard-library-python
---

# Catalog scripts run through uv and share code through a published package

Every catalog script runs through `uv run`, inside the uv project of its plugin.
Code that the scripts of more than one plugin use is the `agentdev-lib` package,
which is published to PyPI. A plugin pins the exact version of `agentdev-lib`,
and names no source for it, because the plugin's own files ship with the plugin.
A checkout of this repository runs its own copy of `agentdev-lib`. The image
runs a build of `agentdev-lib` from the source it was built from, not the copy
on PyPI. The maintainer made this decision.

A consumer outside the image needs `uv`. The first run of a script downloads
`agentdev-lib`.

## Considered Options

- Standard-library scripts that share modules through a directory on `sys.path`,
  as ADR-0040 decided. Rejected: each installed plugin is a separate copy, so a
  script in one plugin cannot reach the modules of another.
- A copy of the shared modules in each plugin, generated from one source.
  Rejected: copies to keep in step, one more set for each new plugin.
- A git source for the package. Rejected: a source in a plugin's own files
  cannot be overridden in a checkout, so a checkout would run the released
  package and not its own.

## Consequences

- A change to `agentdev-lib` needs a new version, and every plugin pin follows
  that version.
- A pushed version tag starts the release. The tag is pushed with a GitHub App
  token, because a tag pushed with the workflow's own token starts no workflow.
- `uv` is the parent of every script. A script that a terminating signal ends
  still prints its `SIGNAL_*` result, but its caller sees exit status 128 + the
  signal number, not a signal death.
