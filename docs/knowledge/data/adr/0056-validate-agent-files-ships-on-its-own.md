---
type: adr
stage: accepted
description: validate_agent_files is a separate package with its own pyproject.toml and a test suite that uses no fixture of this repository.
---

# validate_agent_files is a separate package

`py_packages/validate_agent_files/` is a separate released package with its own
`pyproject.toml`. Its tests use no fixture of this repository. The image
installs it as an isolated uv tool at `/usr/local/bin/validate_agent_files`, so
a consumer has it without the publisher-only source.

## Considered Options

- One test suite for the validator and the plugin. Rejected: the released
  package then needs the fixtures of this repository.

## Consequences

- A full template copy deletes `py_packages/validate_agent_files/` as
  publisher-only source. The consumer then runs `validate_agent_files` from the
  image, without `uv run`, also in a CI job that runs in the image.
