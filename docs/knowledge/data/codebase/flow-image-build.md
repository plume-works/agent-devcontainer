---
type: codebase
description: From a push to a published multi-arch agent-desktop image and the Renovate digest bump that points the devcontainer at it.
source:
- .github/workflows/ci.yml
- docker
- ansible
- devcontainer-compose-pins.yml
source_digest: sha256:cc15bf18d5db54c77182b017b4636227758c81c5db212bacc0d3bb92b3170a92
verified:
  by: claude-code/opus-5.5
  at: 2026-10-19T16:30:00Z
stale_after: 2027-01-17
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T16:30:00Z
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
   `.github/workflows/primary-checks.yml:53`, in
   [workflows](github/workflows.md)
2. `ci.yml`'s `paths-filter` job applies the `image` filter from [the
   paths-filter action](github/actions.md); nothing matched means every later
   job is skipped — `.github/workflows/ci.yml:35`
3. `build-dev-image` runs once per architecture; `Set base image refs` reuses
   the published `edge` image as the Ansible base unless the run is on `main`, a
   tag, a merge group, or a `[ci:clean_build]` commit —
   `.github/workflows/ci.yml:99`
4. `docker/ansible/Dockerfile` builds `ubuntu-ansible`, then
   `agent-desktop.Dockerfile` is built `FROM` that digest with the catalog and
   validator version pins as build args, and `agent-opencode.Dockerfile` `FROM`
   the desktop digest just built — `.github/workflows/ci.yml:130-175`, in
   [docker/](docker.md)
5. The desktop Dockerfile's `RUN` mounts the checkout at `/provision` and runs
   the [playbook](ansible.md) with every capability on; the `perm_probe` guards
   bracket the roles and the catalog and validator roles verify their pins —
   `docker/desktop/agent-desktop.Dockerfile:41`
6. `merge-dev-image` merges each image's per-arch digests into its own `edge`
   manifest and emits `image_pinned` and `opencode_image_pinned` —
   `.github/workflows/ci.yml:182`
7. `dev-container-ci` rewrites `devcontainer-compose-pins.yml` to that digest
   and builds and smoke-tests the [devcontainer](devcontainer.md) with
   `devcontainers/ci`, then runs the repository's pytest suites inside it —
   `.github/workflows/ci.yml:260-301`. Alongside it, `opencode-acceptance` runs
   `test-agent-runtime.sh` on the merged `agent-opencode` digest on each native
   architecture, and `finished` requires both —
   `.github/workflows/ci.yml:309-347`
8. After the merge to `main`, the self-hosted Renovate bot
   (`.github/workflows/renovate.yml`) opens and automerges one PR bumping the
   digest in `devcontainer-compose-pins.yml` and in every workflow container job
   that pins it; that PR runs the Renovate-config validation inside the new
   image — `.github/renovate.json:45-53`. The `agent-opencode` deployment pin in
   `opencode-compose-pins.yml` advances the same way, gated by native acceptance
   of the proposed digest instead of a build — `.github/renovate.json:54-62`

## Failure modes

- A catalog or validator version that disagrees with its pin fails step 5
  (`stage_catalog.yml:68`, `validate_agent_files/tasks/main.yml:93`) rather than
  publishing a mislabeled image.
- Non-root ownership of `/usr/local` fails step 5 at the `final` probe.
- Missing `edge` image in step 3 falls back to a scratch build; slower, not
  wrong.
- The digest pins sit outside the `image` filter; moving one under
  `.devcontainer/` or `docker/` would make step 8 retrigger steps 2–7 forever.
- A failed native `agent-opencode` acceptance fails `finished`, so neither image
  is reported green.
