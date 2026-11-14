---
type: bug
description: The fish_setup role writes dev.fish into the build user's home. The home volume starts empty. Thus the fish PATH setup is not in the home of the account that runs the container.
stage: pending
severity: low
sources:
- resource: ansible/roles/fish_setup/tasks/main.yml
- resource: docker/base/agentdev-base.Dockerfile
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
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
