---
type: bug
description: The fish_setup role writes dev.fish into the build user's home. The home volume starts empty. Thus the fish PATH setup is not in the home of the account that runs the container.
stage: done
severity: low
sources:
- resource: ansible/roles/fish_setup/tasks/main.yml
- resource: docker/base/agentdev-base.Dockerfile
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
---

# Bug: the base image writes the fish `PATH` setup into the build user's home

## Symptom

The base image must write its shell `PATH` setup to `/etc/bash.bashrc` and
`/etc/fish/conf.d/`, and never into a home, because the home volume starts
empty. The `fish_setup` role writes `dev.fish`, which adds `$HOME/.local/bin` to
`PATH`, into the home of the build user. On a container with a home volume, fish
does not read that file.

## Reproduction

1. Build the base image.
2. `ls /etc/fish/conf.d/` in the image shows no `dev.fish`.
3. The file is at `<build user home>/.config/fish/conf.d/dev.fish`.

## Root cause

`ansible/roles/fish_setup/tasks/main.yml` › "Copy development fish
configuration" sets `dest: "{{ user_home }}/.config/fish/conf.d/dev.fish"`.
`docker/base/agentdev-base.Dockerfile` sends only the `bash_setup` and
`bun_setup` destinations to `/etc`.

## Fix

The `fish_setup` role is gone with the rest of Ansible
([ADR-0107](../../../adr/0107-devcontainer-image-on-plume-devcontainer-base.md)).
The image copies `docker/devcontainer/agentdev.fish` to
`/etc/fish/conf.d/agentdev.fish`, which adds `$HOME/.local/bin` and
`$HOME/.bun/bin` to `PATH` for every account.
