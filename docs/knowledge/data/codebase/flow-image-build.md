---
type: codebase
description: From a push to a tested, promoted multi-arch agentdev image family and the Renovate digest bumps that point the Dev Container and the deployment at it.
source:
- .github/workflows/ci.yml
- .github/workflows/primary-checks.yml
- .github/actions/docker
- docker
- ansible
- devcontainer-compose-pins.yml
source_digest: sha256:ed68edbd169a0233f9b8ffedf8d4adcd179329ec31b31234308a90ae3e827248
verified:
  by: claude-code/opus-5.5
  at: 2026-10-29T21:16:01Z
stale_after: 2027-01-27
generated:
  by: claude-code/opus-5.5
  at: 2026-10-29T21:16:01Z
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
   the published `agentdev-base:edge` as the Ansible base unless the run is on
   `main`, a tag, a merge group, or a `[ci:clean_build]` commit —
   `.github/workflows/ci.yml:103`
4. `docker/ansible/Dockerfile` builds `ubuntu-ansible`, then
   `agentdev-base.Dockerfile` is built `FROM` that digest with the catalog,
   validator, and Playwright version pins, and `agentdev-deploy.Dockerfile` and
   `agentdev-devcontainer.Dockerfile` each `FROM` the base digest just built —
   `.github/workflows/ci.yml:142-205`, in [docker/](docker.md)
5. The base Dockerfile's `RUN` mounts the checkout at `/provision` and runs the
   [playbook](ansible.md) with every capability on; the `perm_probe` guards
   bracket the roles while the catalog, validator, and Playwright roles verify
   their pins — `docker/base/agentdev-base.Dockerfile:45`
6. `merge-dev-image` merges each of the four images' per-arch digests into its
   own manifest, tagged `sha-<commit>` only, and emits
   `devcontainer_image_pinned`, `deploy_image_pinned`, and the four digests —
   `.github/workflows/ci.yml:208`,
   `.github/actions/docker/multiarch-merge/action.yml:66`
7. Three test jobs run on each native architecture. `dev-container-ci` rewrites
   `devcontainer-compose-pins.yml` to the merged `agentdev-devcontainer`, pulls
   it in its own step, builds and smoke-tests the
   [devcontainer](devcontainer.md) with `devcontainers/ci`, launches the bundled
   Chromium against a data URL, then runs the repository's pytest suites inside
   it — `.github/workflows/ci.yml:271-361`. `deploy-acceptance` runs
   `test-agent-runtime.sh` on the merged `agentdev-deploy` —
   `.github/workflows/ci.yml:369`. `devcontainer-acceptance` pulls the merged
   `agentdev-devcontainer` and runs the direct and derived consumer fixtures,
   this repository's clone and worktree, and the template-consume migration end
   state through create, attach, restart, and rebuild —
   `.github/workflows/ci.yml:407`
8. `promote-dev-image`, once all three pass, points the event's moving tags
   (`edge`, the branch, `pr-<n>`, release versions) at the four tested digests
   with `imagetools create`, skipping a tag whose image's revision label names a
   descendant of this commit; `finished` requires it —
   `.github/workflows/ci.yml:454,515`,
   `.github/actions/docker/promote/action.yml:61,73`
9. After the merge to `main`, the self-hosted Renovate bot
   (`.github/workflows/renovate.yml`) opens and automerges one PR bumping the
   `agentdev-devcontainer` digest in `devcontainer-compose-pins.yml` and in
   every workflow container job that pins it; that PR runs the Renovate-config
   validation inside the new image — `.github/renovate.json:45-53`. The
   `agentdev-deploy` pin in `opencode-compose-pins.yml` advances the same way,
   gated by native acceptance of the proposed digest instead of a build —
   `.github/renovate.json:54-62`

## Failure modes

- A catalog, validator, or Playwright version that disagrees with its pin fails
  step 5 rather than publishing a mislabeled image; a missing Chromium fails the
  native smoke launch in step 7.
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
