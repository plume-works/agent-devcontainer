---
type: bug
description: The description label of agentdev-base says that the image holds a default policy, but the image contains no firewall allowlist and no agent policy.
stage: pending
severity: low
sources:
- resource: docker/base/agentdev-base.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/deploy/agentdev-deploy.Dockerfile
---

# Bug: The agentdev-base label says that the image holds a default policy

## Symptom

The `org.opencontainers.image.description` label of `agentdev-base` is
"Lifecycle-neutral agentdev tools, staged catalog, and default policy." The
image contains no firewall allowlist and no agent policy, so a consumer who
reads the label expects a policy that the image does not have.

## Reproduction

1. Read the last `LABEL` of `docker/base/agentdev-base.Dockerfile`: it names a
   default policy.
2. Search the same file for `firewall-allowlist`: there is no match.
3. Search `docker/devcontainer/agentdev-devcontainer.Dockerfile` and
   `docker/deploy/agentdev-deploy.Dockerfile`: each one copies
   `.devcontainer/firewall-allowlist.txt` into `/etc/agentdev/`.

## Root cause

The two runtime images copy the allowlist, and the runtime writes the agent
policy at each start. Nobody changed the label of `agentdev-base` when the
policy files moved from the base image.

## Potential solution

Remove "and default policy" from the label.
