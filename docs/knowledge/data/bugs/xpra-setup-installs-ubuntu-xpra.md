---
type: bug
stage: done
description: The xpra_setup role never enables an Xpra apt repository, so agent-desktop and agent-opencode ship Ubuntu's xpra 3.1.5 instead of an Xpra 6.x build.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T19:04:34Z
sources:
- resource: ansible/roles/xpra_setup/tasks/main.yml
- resource: docker/desktop/start-xpra.sh
- resource: https://github.com/Xpra-org/xpra/blob/831ccc2b6828b17d31dcad40f2b318030028e837/setup.py
- resource: https://github.com/Xpra-org/xpra/tree/831ccc2b6828b17d31dcad40f2b318030028e837/packaging/repos/noble
---

# Bug: xpra_setup installs Ubuntu's xpra 3.1.5

## Symptom

`agent-desktop` and every image built on it, including `agent-opencode`, ship
`xpra 3.1.5+dfsg1-0.2ubuntu1` from Ubuntu's archive. `xpra --version` prints
`xpra v3.1.5`, and `/etc/apt/sources.list.d/` holds no Xpra entry, although the
role clones Xpra at the `v6.4.3` tag to set one up. Only the signing key
`/usr/share/keyrings/xpra.asc` is installed.

## Reproduction

1. Run any published image, for example
   `docker run --rm --entrypoint bash ghcr.io/plume-works/agent-opencode:<tag> -c 'xpra --version; ls /etc/apt/sources.list.d/'`.
2. It prints `xpra v3.1.5`, and the directory lists no `xpra*.sources` file.

## Root cause

The role runs `python3 /tmp/xpra/setup.py install-lts-repo` without a `chdir`.
That subcommand downloads the key to an absolute path, then copies
`packaging/repos/<codename>/xpra-lts.sources` by a path relative to the working
directory, so the copy fails. `setup.py` runs each step with `subprocess.run`
and ignores its exit status, so the task still succeeds. Its
`creates: /etc/apt/sources.list.d/xpra.list` guard never matches either, because
Xpra's definitions are deb822 `.sources` files. The following `apt: xpra` task
then resolves `xpra` from Ubuntu's archive.

The pinned tag would not have been honored even with a working copy: for noble,
`https://xpra.org/lts` serves 5.1.x and `https://xpra.org` serves the current
6.x stable release, so no repository installs exactly 6.4.3.

## Fix

The role installs Xpra from the stable repository (`https://xpra.org`) with no
`setup.py` step. It downloads `xpra.asc` with `get_url`, writes the deb822
source for the image's codename and architecture, refreshes the apt cache, and
installs `xpra` by name, unpinned as `architecture/ansible-apt-pins` records. It
then asserts that the installed `xpra` reports a major version of at least 6, so
a fallback to Ubuntu's package fails the build.

Xpra 6 needed two changes in `start-xpra.sh`. It rejects `--global-menus` and
`--dbus-proxy`, whose features it no longer has, so both flags are gone. It
names its X server `Xvfb-for-Xpra-N` rather than `Xvfb-for-Xpra-:N`, so
`reclaim_orphaned_display` accepts both names; otherwise a crashed Xpra's X
server keeps the display locked and every recovery attempt fails.

## Key references

Verified anchor points (line numbers as of 2026-10-19):

- `ansible/roles/xpra_setup/tasks/main.yml:14` — the Xpra stable repository
- `ansible/roles/xpra_setup/tasks/main.yml:23` — `apt: xpra`
- `ansible/roles/xpra_setup/tasks/main.yml:37` — the Xpra 6 version assertion
- `docker/desktop/start-xpra.sh:74` — `reclaim_orphaned_display`, matching both
  X server names at `:80`
- `setup.py:744-806` (Xpra `831ccc2b`) — `install_repo`, relative `cp` and
  unchecked `subprocess.run`, which the role no longer calls
