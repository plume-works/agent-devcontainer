---
type: codebase
description: From a push to a published multi-arch agent-desktop image and the Renovate digest bump that points the devcontainer at it.
source:
- .github/workflows/ci.yml
- docker
- ansible
- devcontainer-compose-pins.yml
source_digest: sha256:cdde99a1b7badc145fb9d193afea55cb77028a3fdd6af53ca42842b73d4b9340
verified:
  by: claude-code/opus-5
  at: 2026-09-16T07:19:34Z
stale_after: 2026-12-15
generated:
  by: claude-code/opus-5
  at: 2026-09-16T07:19:34Z
sources:
- id: code
  resource: .github/workflows/ci.yml
---

# Flow: image build

What happens between a commit touching the image sources and a devcontainer
running the image it produced.

## Trace

1. A push or pull request enters `primary-checks.yml`; the `reformat` job runs
   first and `ci` follows only when its gate says `run_downstream` —
   `.github/workflows/primary-checks.yml:51`, in
   [workflows](github/workflows.md)
2. `ci.yml`'s `paths-filter` job applies the `image` filter from
   [the paths-filter action](github/actions.md); nothing matched means every
   later job is skipped — `.github/workflows/ci.yml:34`. The same job decides
   whether the run publishes: a pull request from a fork carries a read-only
   token, so it builds as a check and pushes nothing —
   `.github/workflows/ci.yml:59`
3. `build-dev-image` runs once per architecture; `Set base image refs` reuses
   the published `edge` image as the Ansible base unless the run is on `main`, a
   tag, a merge group, or a `[ci:clean_build]` commit —
   `.github/workflows/ci.yml:125`
4. `docker/ansible/Dockerfile` builds `ubuntu-ansible`, then
   `agent-desktop.Dockerfile` is built `FROM` that digest with the catalog and
   validator version pins as build args — a run that publishes nothing cannot
   pull the base it just built, so it builds on the published
   `ubuntu-ansible:edge` — `.github/workflows/ci.yml:156-203`, in
   [docker/](docker.md)
5. The desktop Dockerfile's `RUN` mounts the checkout at `/provision` and runs
   the [playbook](ansible.md) with every capability on; the `perm_probe` guards
   bracket the roles and the catalog and validator roles verify their pins —
   `docker/desktop/agent-desktop.Dockerfile:41`
6. `merge-dev-image` merges the per-arch digests into one `edge` manifest and
   emits `image_pinned`; it is skipped when the run publishes nothing, because
   no digest was pushed — `.github/workflows/ci.yml:211`
7. `dev-container-ci` rewrites `devcontainer-compose-pins.yml` to that digest
   and builds and smoke-tests the [devcontainer](devcontainer.md) with
   `devcontainers/ci`; with nothing published it keeps the committed pin —
   `.github/workflows/ci.yml:284-297`
8. After the merge to `main`, Renovate opens and automerges a PR bumping the
   digest in `devcontainer-compose-pins.yml` — `.github/renovate.json:16-23`

## Failure modes

- A catalog or validator version that disagrees with its pin fails step 5
  (`stage_catalog.yml:68`, `validate_agent_files/tasks/main.yml:81`) rather than
  publishing a mislabeled image.
- Non-root ownership of `/usr/local` fails step 5 at the `final` probe.
- Missing `edge` image in step 3 falls back to a scratch build; slower, not
  wrong.
- The digest pin sits outside the `image` filter; moving it under
  `.devcontainer/` or `docker/` would make step 8 retrigger steps 2–7 forever.
- A fork run verifies that both images build, nothing more: the desktop image is
  built on the published base rather than the one step 4 just built, so a change
  under `docker/ansible/` is never exercised by the desktop build.
