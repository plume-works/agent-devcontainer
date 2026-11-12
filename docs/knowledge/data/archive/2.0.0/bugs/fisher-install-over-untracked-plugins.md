---
type: bug
description: Pinning the fish plugins by spec made fish_setup fail on any host whose plugins were installed unpinned, because fisher refuses to install over files it does not track.
sources:
- resource: ansible/roles/fish_setup/tasks/main.yml
stage: done
severity: medium
---

# Bug: Fisher install over untracked plugins

## Symptom

`fish_setup` fails at *Install fisher* with

```
fisher: Cannot install "jorgebucaran/fisher@4.4.8": please remove or move
conflicting files first:
        ~/.config/fish/functions/fisher.fish
        ~/.config/fish/completions/fisher.fish
```

and the play aborts before `bass` is reached.

## Reproduction

Run the role against any host provisioned before the plugins were pinned — every
published `agent-desktop` image, and so every warm build layered on one.

## Root cause

`fisher install <owner>/<repo>@<ref>` refuses to overwrite files it does not
already track under that exact spec. A host provisioned by the unpinned role has
`jorgebucaran/fisher` and `edc/bass` in `fish_plugins`, with no `@ref`, so the
pinned spec is absent from the file, the version guard decides an install is
needed, and the install then collides with the files the untracked entry owns.
The guard and the installer disagreed about what "installed" means.

## Fix

The role writes the pinned specs into `fish_plugins` and runs `fisher update`,
which reconciles the tree to that file — installing what is listed, updating
what moved, and removing what is not. That converges from an empty system and
from one carrying the same plugins under a different spec, which is exactly the
case `fisher install` rejects.

## Key references

- `ansible/roles/fish_setup/tasks/main.yml#name` —
  `Collect the pinned fish plugin specs`, the wanted list the role converges to
- `ansible/roles/fish_setup/tasks/main.yml#name` —
  `Collect the installed fish plugin specs`, the guard's view of what is
  installed
- `ansible/roles/fish_setup/tasks/main.yml#name` —
  `Record the pinned fish plugin list`, writing the specs into `fish_plugins`
- `ansible/roles/fish_setup/tasks/main.yml#name` —
  `Reconcile the installed fish plugins with the pinned list`, the
  `fisher update` that replaced the install
- `ansible/roles/fish_setup/defaults/main.yml#fish_setup_fisher_version` —
  `fish_setup_fisher_version`, with `fish_setup_bass_ref`
