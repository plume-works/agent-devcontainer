---
type: plan
created: 2026-10-11
description: Mount a persistent volume at /var/lib/containerd in the coder-ide-baseline workspace container so the nested Docker's containerd image store survives a workspace restart alongside /var/lib/docker.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-11T19:00:00Z
sources:
- resource: https://github.com/plume-works/coder-ide-baseline/blob/349d8d6/template/main.tf
- resource: https://docs.docker.com/engine/storage/containerd/
- resource: https://containerd.io/docs/2.2/snapshotters/readme/
---

# Persist the Coder workspace containerd image store

## Context

Coder workspaces from
[plume-works/coder-ide-baseline](https://github.com/plume-works/coder-ide-baseline)
run a nested Docker engine under Sysbox. Docker 29 uses the containerd image
store by default on fresh installs, and the workspace engine reports
`driver-type: io.containerd.snapshotter.v1`. With that store, Docker keeps
container records, volumes, and the BuildKit cache in `/var/lib/docker`, while
image blobs, manifests, the image database, and unpacked layers live under
`/var/lib/containerd`.

The template persists only `/var/lib/docker` (`docker_volume.docker_lib`). Every
workspace restart recreates the workspace container, which discards
`/var/lib/containerd`. The records that survive in `/var/lib/docker` (the Dev
Container's container and BuildKit cache entries) then refer to image content
that no longer exists, so the Dev Container can neither restart nor rebuild from
them: [Bug: Coder workspace Dev Container is lost on
restart](../bugs/coder-devcontainer-lost-on-restart.md).

The Dev Container therefore does not survive a restart, and nothing that runs in
it on agent start runs either. This blocks the restart-based live check that
[Start Claude Remote Control from the Coder
agent](20261011-coder-claude-remote-control.md) needs.

## Approach

Add a second per-workspace `docker_volume`, shaped like `docker_lib`, and mount
it at `/var/lib/containerd` in `docker_container.workspace`. Both halves of the
engine's storage then persist together. This follows the pattern this
repository's own Dev Container uses: the docker-in-docker feature gives it
separate volumes for `/var/lib/docker` and `/var/lib/containerd`.

Sysbox already mounts a host directory at
`/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs` inside the
workspace. How that mount interacts with a user volume on the parent directory
is unverified. Task 1 settles it before the template changes. If the Sysbox
mount shadows the volume at that path, the snapshotter directory needs its own
persistent volume too, and Task 2 carries whichever layout Task 1 confirms.

Rejected: turning off the containerd image store
(`"features": {"containerd-snapshotter": false}` in the workspace `daemon.json`)
and keeping everything in the persisted `/var/lib/docker`. That would be simpler
and use less disk. But it pins the workspace engine to Docker's legacy storage
path and gives up local multi-platform images and attestations. The maintainer
chose to stay on Docker's default store.

## Implementation Steps

### Task 1: Settle the Sysbox mount layout

**Files:** none (live workspace, in `plume-works/coder-ide-baseline`)

- [ ] In a workspace started from a draft template version (not promoted to
  active) that adds the `/var/lib/containerd` volume, record from `mount` inside
  the workspace container whether
  `/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs` is backed by the
  new volume or by a separate Sysbox mount. Record the result under
  `## Verification results`, along with the layout Task 2 adopts.

### Task 2: Add the containerd volume to the template

**Files:** Modify (in `plume-works/coder-ide-baseline`): `template/main.tf`

- [ ] Add `docker_volume.containerd_lib` named
  `coder-${data.coder_workspace.me.id}-containerd`, with the same
  `lifecycle { ignore_changes = all }` and `coder.*` labels as
  `docker_volume.docker_lib`. Mount it in `docker_container.workspace` at
  `/var/lib/containerd`, next to the `/var/lib/docker` mount, plus any
  snapshotter mount that Task 1 requires. `terraform validate` passes.
- [ ] Push the template version to Coder.

### Task 3: Prove images survive a restart

**Files:** none (live workspace)

- [ ] In a workspace on the new template version whose Dev Container has been
  built, run `coder restart`. The Dev Container comes back up without a rebuild:
  the agent log shows no `Building` step, `docker images` inside the workspace
  still lists the `vsc-agent-devcontainer-*` image, and the `repo` sub-agent
  reports healthy.

### Task 4: Reset workspaces created before the volume

**Files:** none (each existing workspace)

- [ ] For each workspace that predates the template change, after its first
  start on the new version: remove the stale Dev Container container and run
  `docker builder prune -af`, so `/var/lib/docker` no longer holds records that
  point at content the new, empty volume lacks. Restart, and confirm that the
  Dev Container builds and comes up healthy.

## Spec changes

None — no behavioral change. The change lives in the Coder template, outside
this repository's specs.

## Verification

- `terraform validate` in `coder-ide-baseline/template`.
- Task 3's restart check on a fresh workspace, and Task 4's on each existing
  one.
- After a restart, the Dev Container's agent-start scripts run. One observable
  sign: `tmux -L claude-remote ls` lists the `claude-remote` session in a
  workspace logged in to claude.ai.

## Out of scope

- Turning off the containerd image store (the rejected alternative).
- Automating Task 4's one-time reset in the template's startup script.
- Disk-usage limits or pruning policy for the workspace volumes.

## Key references

Verified anchor points (line numbers as of 2026-10-11), in
`plume-works/coder-ide-baseline` at `349d8d6`:

- `template/main.tf:193` — `coder_devcontainer.repo`
- `template/main.tf:263` — `docker_volume.home_volume`
- `template/main.tf:289` — `docker_volume.docker_lib`, the shape to copy
- `template/main.tf:326` — `docker_container.workspace`
- `template/main.tf:379` — `runtime = "sysbox-runc"`
- `template/main.tf:392` — the `/var/lib/docker` volume mount
