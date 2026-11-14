---
type: adr
stage: accepted
description: The image build installs validate_agent_files from the build context as a uv tool, not from PyPI.
---

# validate_agent_files comes from the build context

The image build installs `validate_agent_files` from the build context, as it
stages the catalog. For this reason, the image and `validate_agent_files` come
from the same commit, and the release of the package stays in this repository.
The build reads the version of the installed package and fails when it is not
the pin `VALIDATE_AGENT_FILES_VERSION`, so the image label gives the installed
version.

## Considered Options

- Publish `validate_agent_files` to PyPI. Rejected: it needs a package name, a
  release workflow, and trusted publishing, and it separates the release of the
  package from the release of the image.

## Consequences

- The tool environment is in `/opt/uv-tools`, outside the home, so a home volume
  cannot hide it.
