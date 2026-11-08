---
type: bug
stage: done
severity: medium
description: The agentdev-base provisioning step bind-mounts the whole repository as its build context, so any change anywhere in the repository invalidates the cached Ansible layer and every image-touching run reprovisions from scratch.
sources:
- resource: docker/base/agentdev-base.Dockerfile
- resource: .dockerignore
- resource: .github/actions/docker/build-push-action/action.yml
- resource: .github/workflows/ci.yml
- resource: https://github.com/plume-works/agent-devcontainer/actions/runs/41371706407
---

# Bug: Image provisioning layer is keyed on the whole repository

## Symptom

Every CI run that builds the images reprovisions `agentdev-base` with Ansible
from the start, even when nothing the playbook reads has changed. On `main` the
step takes about 9 minutes per architecture (run 41371706407, "Build agentdev
base image", amd64: 8.7 min).

## Reproduction

1. Build `docker/base/agentdev-base.Dockerfile` with the repository root as the
   context.
2. Edit a file the build never reads, such as a document under
   `docs/knowledge/`.
3. Build again with the same builder. The provisioning `RUN` re-executes instead
   of reporting `CACHED`, although `ansible/`, the catalog, and the validator
   sources are unchanged.

## Root cause

The provisioning `RUN` in `docker/base/agentdev-base.Dockerfile` mounts
`--mount=type=bind,readonly,target=/provision` with no `source`, which binds the
entire build context. The context is the repository root, and `.dockerignore` is
a deny-list that drops only `.git`, `.github`, `.claude`, `.devcontainer`, and
caches, so the context carries `docs/`, `scripts/`, the compose pin files,
`uv.lock`, and every test. BuildKit keys a `RUN` on the contents of its bind
mounts, so a change to any of those files invalidates the layer, and the GitHub
Actions layer cache configured in the `build-push-action` composite action never
hits for it.

The build reads only `ansible.cfg`, `ansible/`, `docker/bin/gh`, the catalog
(`.claude-plugin/`, `.agents/`), `py_packages/validate_agent_files/`,
`py_packages/agentdev_runtime/`, `docker/desktop/entrypoint.sh`, the runtime
`supervisord.conf` files, and `.devcontainer/firewall-allowlist.txt` — the list
`.dockerignore`'s own header states but does not enforce.

## Potential solution

Make `.dockerignore` an allow-list of the files the build reads, and split the
provisioning `RUN` so each step bind-mounts only its own inputs. A change to
`docs/`, `scripts/`, or the tests then leaves the provisioning layers cached.

## Fix

`.dockerignore` is now an allow-list of the inputs the image builds read, and
the single `agentdev-base` provisioning `RUN` is split into three — the Ansible
roles, the validator, and a new `agent_catalog` role — each bind-mounting only
its own inputs and selecting its roles by tag. The Ubuntu base is pinned by
digest and refreshed weekly by Renovate, `ubuntu-ansible` is built without
per-run labels so its digest stays stable, and `agentdev-base` starts from its
per-architecture manifest. A change outside a step's inputs now leaves that step
`CACHED`; a catalog-only change reruns only the catalog step. Shipped by [Narrow
the image build context](../plans/20261102-narrow-image-build-context.md).

## Key references

- `docker/base/agentdev-base.Dockerfile › "RUN --mount=type=cache,target=/var/cache/apt,sharing=locked"`
  — provisioning `RUN` with the whole-context bind mount at `/provision`
- `.dockerignore › "The image build context is the repository root; keep it"` —
  header listing the inputs the build consumes
- `.github/actions/docker/build-push-action/action.yml#runs.steps.Build and push Docker image.env.REGISTRY_CACHE`
  — GHA and registry layer cache wiring
- `.github/workflows/ci.yml#jobs.build-dev-image.steps.name` —
  `Set base image refs`, clean build on `main`, warm start from
  `agentdev-base:edge` elsewhere
