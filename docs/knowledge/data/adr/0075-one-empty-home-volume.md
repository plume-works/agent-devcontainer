---
type: adr
stage: accepted
description: The Dev Container runs as a non-root agent account remapped to the host user, whose whole home is one home volume that starts empty.
---

# The agent account has one empty home volume for each instance

The Dev Container uses the account model of the standalone runtime. A non-root
`agent` account is the remapped account of the host user. Its whole home is on
one home volume that starts empty. The volume gets a copy of the content of an
image home one time, and an image upgrade never updates it. As a result, the
image has an empty `/home/agent`. The UID update of the devcontainer CLI fails
the build when the home is not there.

## Considered Options

- A volume on `/root`, with root as the user. Rejected: the base image builds
  shell configuration, `gh` extensions, and tool state into `/root`. A volume
  there keeps all of it at the image of the first create phase.
- A volume on `/root` that the image refreshes at each start. Rejected: it
  overwrites the edits of the user and needs an ownership decision for each
  file.
- An account that the container start creates, as the standalone runtime does.
  Rejected: the UID update of the devcontainer CLI needs an account that the
  image defines.
- One volume for each state directory. Rejected: each new piece of state needs
  its own volume decision, and single files such as `~/.claude.json` need
  symlinks.

## Consequences

- The image defines `agent` as 1000:1000. Its metadata sets `remoteUser: agent`
  and `updateRemoteUserUID: true`, and mounts the home volume
  `agentdev-home-${devcontainerId}` at `/home/agent`
  (`docker/devcontainer/agentdev-devcontainer.Dockerfile`). The user of the
  container stays root, and PID 1 runs each user service as `agent`.
- Docker gives the owner of the empty `/home/agent` to a new volume, so the
  volume starts empty and the remapped account owns it.
- The UID and GID of the remapped account must be able to write the host
  checkout. The root bootstrap refuses a checkout that the account cannot write,
  and names the UID that it needs.
- The repository owner supports no root host. On a root host, the devcontainer
  CLI does not remap `agent`, which stays 1000:1000, and the root bootstrap
  refuses the checkout that root owns.
- The base image writes its `PATH` and history configuration into
  `/etc/bash.bashrc` and `/etc/fish/conf.d/`, so an empty home gets it.
- A test that needs root has the `requires_root` marker, and pytest skips it in
  a run as `agent`. The root-test launcher runs these tests as root through
  `sudo`.
- The uv cache, interpreters, and environments are on the home volume, with no
  separate `/uv` volume.
- Editor servers such as `~/.vscode-server` stay on the home volume with no
  cleanup. The owner accepted unlimited growth, and a broken server installation
  that stays after a rebuild. The owner did not accept a location off the volume
  for these servers, or a removal of old server versions in the create phase.
- The fish configuration that the `fish_setup` role writes into the home of the
  build user does not go into the home of the `agent` account.
