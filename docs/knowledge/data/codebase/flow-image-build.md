---
type: codebase
description: From a push to a published multi-arch agent-desktop image and the Renovate digest bump that points the devcontainer at it.
source:
- .github/workflows/ci.yml
- docker
- ansible
- devcontainer-compose-pins.yml
commit: eb60f60450c6009b076bc51993b49a924653eaa4
verified:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:09:00Z
stale_after: 2026-12-02
generated:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:09:00Z
sources:
- id: code
  resource: .github/workflows/ci.yml
  title: the code this map describes, read at commit eb60f60
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
   later job is skipped — `.github/workflows/ci.yml:34`
3. `build-dev-image` runs once per architecture; `Set base image refs` reuses
   the published `edge` image as the Ansible base unless the run is on `main`, a
   tag, a merge group, or a `[ci:clean_build]` commit —
   `.github/workflows/ci.yml:97`
4. `docker/ansible/Dockerfile` builds `ubuntu-ansible`, then
   `agent-desktop.Dockerfile` is built `FROM` that digest with the catalog and
   validator version pins as build args — `.github/workflows/ci.yml:128-158`, in
   [docker/](docker.md)
5. The desktop Dockerfile's `RUN` mounts the checkout at `/provision` and runs
   the [playbook](ansible.md) with every capability on; the `perm_probe` guards
   bracket the roles and the catalog and validator roles verify their pins —
   `docker/desktop/agent-desktop.Dockerfile:41`
6. `merge-dev-image` merges the per-arch digests into one `edge` manifest and
   emits `image_pinned` — `.github/workflows/ci.yml:165`
7. `dev-container-ci` rewrites `devcontainer-compose-pins.yml` to that digest
   and builds and smoke-tests the [devcontainer](devcontainer.md) with
   `devcontainers/ci` — `.github/workflows/ci.yml:233-262`
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
