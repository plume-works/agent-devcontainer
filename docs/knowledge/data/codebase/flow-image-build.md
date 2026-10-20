---
type: codebase
description: From a push to a tested, promoted multi-arch agent-desktop image and the Renovate digest bump that points the devcontainer at it.
source:
- .github/workflows/ci.yml
- .github/workflows/primary-checks.yml
- .github/actions/docker
- docker
- ansible
- devcontainer-compose-pins.yml
source_digest: sha256:669e75bf5615e34f493a4c8b2e44a2351d856e805c2039e56e37ad60e5226d65
verified:
  by: claude-code/opus-5.5
  at: 2026-10-20T14:18:08Z
stale_after: 2027-01-18
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T05:06:00Z
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
   `.github/workflows/primary-checks.yml:54`, in
   [workflows](github/workflows.md); runs on `main` queue rather than cancel one
   another — `.github/workflows/primary-checks.yml:22-24`
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
6. `merge-dev-image` merges each image's per-arch digests into its own manifest,
   tagged `sha-<commit>` only, and emits `image_pinned`,
   `opencode_image_pinned`, and the three digests —
   `.github/workflows/ci.yml:182`,
   `.github/actions/docker/multiarch-merge/action.yml:66`
7. `dev-container-ci` rewrites `devcontainer-compose-pins.yml` to that digest
   and builds and smoke-tests the [devcontainer](devcontainer.md) with
   `devcontainers/ci`, then runs the repository's pytest suites inside it —
   `.github/workflows/ci.yml:265-306`. Alongside it, `opencode-acceptance` runs
   `test-agent-runtime.sh` on the merged `agent-opencode` digest on each native
   architecture — `.github/workflows/ci.yml:314`
8. `promote-dev-image`, once both pass, points the event's moving tags (`edge`,
   the branch, `pr-<n>`, release versions) at the three tested digests with
   `imagetools create`, skipping a tag whose image's revision label names a
   descendant of this commit; `finished` requires it —
   `.github/workflows/ci.yml:352,403`,
   `.github/actions/docker/promote/action.yml:61,73`
9. After the merge to `main`, the self-hosted Renovate bot
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
- A failed or cancelled test job skips step 8, so every moving tag keeps its
  previous digest and only `sha-<commit>` names the new build.
- A re-run of an older commit promotes nothing a newer run already moved; a
  revision outside the checkout's history, such as an earlier pull request merge
  commit, does not block promotion.
- The digest pins sit outside the `image` filter; moving one under
  `.devcontainer/` or `docker/` would make step 9 retrigger steps 2–8 forever.
