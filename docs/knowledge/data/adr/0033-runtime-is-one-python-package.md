---
type: adr
stage: accepted
description: The runtime images run one Python package, agentdev_runtime, behind one CLI, and agentdev-base does not contain it.
---

# The runtime is one Python package that the base image does not contain

The two runtime images need lifecycle code. They run one Python package,
`agentdev_runtime`, as a uv tool. The package has one command,
`agentdev-runtime`, and it is not on PyPI. `agentdev-base` does not contain the
package, so a consumer can run the base image without a lifecycle.
`agentdev-deploy` and `agentdev-devcontainer` start from `agentdev-base` and
install the package.

## Considered Options

- Separate standard-library scripts on the system interpreter. Rejected: they
  need a PyPI download at container start or a search for apt packages, and a
  separate checksum file for each script.
