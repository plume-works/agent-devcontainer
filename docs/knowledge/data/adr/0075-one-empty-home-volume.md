---
type: adr
stage: accepted
description: The Dev Container runs as a non-root agent account remapped to the host user, whose whole home is one home volume that starts empty.
---

# The agent account has one empty home volume for each instance

The Dev Container uses the account model of the standalone runtime. A non-root
`agent` account is the account of the host user: the devcontainer CLI changes
its UID and GID to those of the host user. Its whole home is on one home volume
that starts empty. Anything built into an image home would be copied into the
volume once and never updated by an image upgrade. As a result, the image ships
`/home/agent` empty. The UID update of the devcontainer CLI re-owns the home of
the account and fails the build when the home is missing.

## Considered Options

- A volume on `/root`, with root as the user. Rejected: the base image builds
  shell configuration, `gh` extensions, and tool state into `/root`. A volume
  there freezes all of it at the image of the first create phase.
- A volume on `/root` that is refreshed from the image at each start. Rejected:
  it overwrites the edits of the user and needs an ownership decision for each
  file.
- An account that the container start creates, as the standalone runtime does.
  Rejected: the UID update of the devcontainer CLI needs an account that the
  image defines.
- One volume for each state directory. Rejected: each new piece of state needs
  its own volume decision, and single files such as `~/.claude.json` need
  symlink workarounds.

## Consequences

- Docker gives the owner of the empty `/home/agent` to a new volume, so the
  volume starts empty and the remapped account owns it.
- The repository owner supports no root host. On a root host, the devcontainer
  CLI does not remap `agent`, which stays 1000:1000, and
  `agentdev-runtime bootstrap` refuses the checkout that root owns.
- Editor servers such as `~/.vscode-server` stay on the home volume with no
  cleanup. The owner accepted the risk of unbounded growth, and of a broken
  server installation that survives a rebuild. The owner declined a location off
  the volume for these servers, and a removal of old server versions in the
  create phase.
