---
type: adr
stage: accepted
description: The image build installs the catalog for a consumer that runs only the image, and the create phase installs it again because the home volume hides what the build wrote.
---

# The image installs the catalog, and the create phase installs it again

The image build installs the catalog. As a result, a consumer that runs the
image with no volumes and no lifecycle commands resolves the `agentdev:*`
skills. The home volume of a Dev Container shadows everything that the build
wrote into a home directory, so the create phase installs the staged catalog
again at user scope.

## Considered Options

- Each consumer that runs only the image installs the catalog. Rejected: it
  duplicates the logic of the lifecycle commands, and it leaves the image
  carrying a staged catalog that looks installed but is not.

## Consequences

- `ansible/roles/agent_catalog/tasks/install_catalog.yml` does the same steps as
  `agentdev-runtime catalog install`. A change to one needs the same change to
  the other.
