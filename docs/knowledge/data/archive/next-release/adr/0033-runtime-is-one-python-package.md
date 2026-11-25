---
type: adr
stage: superseded
---

# The runtime is one Python package that the base image does not contain

The two runtime images need lifecycle code. They run one Python package,
`agentdev_runtime`, installed as a uv tool the way the validator is. The package
has one command, `agentdev-runtime`. It is not published to PyPI, because the
two runtime images are its only installs. `agentdev-base` never contains the
package, so the base image stays lifecycle-neutral and a consumer can run it
without a lifecycle. `agentdev-deploy` and `agentdev-devcontainer` start from
`agentdev-base` and install the package.

## Considered Options

- Loose standard-library scripts on the system interpreter. Rejected: they keep
  either a PyPI download at container start or a hunt for apt dependencies, and
  they need a separate per-file checksum manifest for integrity.
