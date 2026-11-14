---
type: adr
stage: accepted
description: The image build installs validate_agent_files from the build context as a uv tool, not from PyPI.
---

# validate_agent_files comes from the build context

The image build installs `validate_agent_files` from the build context, as it
stages the catalog. For this reason, the image and `validate_agent_files` come
from the same commit, and the release of the package stays in this repository.
The build compares the installed version with the pin
`VALIDATE_AGENT_FILES_VERSION`, so the image label gives the installed version.

## Considered Options

- Publish `validate_agent_files` to PyPI. Rejected: it needs a package name, a
  release workflow, and trusted publishing, and it separates the release of the
  package from the release of the image.
- Install it on the system interpreter or in a project environment. Rejected: a
  uv tool puts one entry point on `PATH` and changes neither of them.

## Consequences

- The build context must contain `py_packages/validate_agent_files/`.
- The `validate_agent_files` Ansible role has its own toggle,
  `install_validate_agent_files`, and its own variables.
