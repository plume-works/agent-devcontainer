# Fish Shell Setup Role

This Ansible role sets up the fish shell for development. It installs fish, the
fisher package manager, and bass (for sourcing bash scripts from fish), then
drops a `conf.d/dev.fish` with the `find_up` and `xpra_display` helper
functions.

## Example Usage

```yaml
- name: Setup fish shell
  hosts: all
  roles:
    - { role: fish_setup, tags: ['fish_setup'] }
```
