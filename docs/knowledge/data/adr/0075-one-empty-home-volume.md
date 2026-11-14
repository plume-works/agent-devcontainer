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
  there keeps all of it at the image of the first create.
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

- The repository owner supports no root host.
- The uv cache, interpreters, and environments are on the home volume, with no
  separate `/uv` volume.
- Editor servers such as `~/.vscode-server` stay on the home volume with no
  cleanup. The owner accepted unlimited growth, and a broken server install that
  stays after a rebuild.
- The fish configuration that the `fish_setup` role writes into the home of the
  build user does not go into the home of the `agent` account.
