---
type: bug
description: The guide's custom-image setup names only the validator and catalog mounts, but the Dev Container and deploy Dockerfiles also mount py_packages/agentdev_runtime and CI tests more publisher trees, so the second choice still gives a build that fails.
stage: pending
severity: medium
sources:
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: .github/workflows/ci.yml
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: the consumption guide's custom-image choices omit the runtime package input

## Symptom

A kept custom-image bundle must build from an explicit choice. The guide tells
the consumer that the base Dockerfile reads the validator and catalog source,
and that the second choice removes those steps. The other Dockerfiles also read
`py_packages/agentdev_runtime`, and CI runs tests and path filters on more
publisher trees. A consumer who makes the second choice gets a build that cannot
find its inputs.

## Reproduction

1. Follow
   `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#optional-custom-image-setup`
   and make the second choice.
2. Delete the publisher source as step 2 of the full-copy workflow tells.
3. Build `docker/devcontainer/agentdev-devcontainer.Dockerfile`: the mount
   `source=py_packages/agentdev_runtime` fails.

## Root cause

`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#optional-custom-image-setup`
names only the mounts of `docker/base/agentdev-base.Dockerfile`.
`docker/devcontainer/agentdev-devcontainer.Dockerfile` and
`docker/deploy/agentdev-deploy.Dockerfile` bind-mount
`py_packages/agentdev_runtime`. `.github/workflows/ci.yml` runs pytest on
`py_packages`, `.agents/plugins/agentdev/tests`,
`.agents/plugins/self-improve/tests`, and `scripts/tests`, and filters on
`compose.opencode*.yml`.
