---
type: adr
stage: accepted
description: The image build installs the catalog for a consumer that runs the bare image, and the create phase installs it again because the home volume hides what the build wrote.
---

# The image installs the catalog, and the create phase installs it again

The image build installs the catalog. As a result, a consumer that runs the
image with no volumes and no lifecycle commands has the `agentdev:*` skills. The
home volume of a Dev Container hides all that the build wrote into a home
directory. As a result, the create phase installs the staged catalog again at
user scope.

## Considered Options

- Each consumer of the bare image installs the catalog. Rejected: it duplicates
  the logic of the lifecycle commands. Also, the image holds a staged catalog,
  but no client reads it.

## Consequences

- `ansible/roles/agent_catalog/tasks/install_catalog.yml` does the same steps as
  `agentdev-runtime catalog install`. A change to one needs the same change to
  the other.
