---
type: codebase
description: Builds Xpra and its HTML5 client from pinned tags, installs VirtualGL from GitHub releases, and adds Mesa software rendering.
source: ansible/roles/xpra_setup
commit: eb60f60450c6009b076bc51993b49a924653eaa4
verified:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:04:51Z
stale_after: 2026-12-02
generated:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:04:51Z
sources:
- id: code
  resource: ansible/roles/xpra_setup
  title: the code this map describes, read at commit eb60f60
---

# xpra_setup role

The largest single addition to the image, behind `install_xpra`: a remote
desktop reachable through a browser.

## Public surface

- `xpra` and the HTML5 client on the image; started by
  [/start-xpra.sh](../../docker.md) at container start
- VirtualGL and Mesa/llvmpipe for GL inside the container

## How it works

Clones the Xpra repository at tag `v6.4.3` and installs it with `setup.py`, then
does the same for `xpra-html5` at `v19`; downloads the VirtualGL `.deb` for the
detected architecture from GitHub releases and installs it; installs the Mesa,
OpenGL, and Xvfb packages, including the software renderer.

## Depends on

`basic_prereqs` for build prerequisites and `extra_facts` for the architecture.
The port and display conventions are owned by the start script, not this role.

## Invariants & gotchas

- Both Xpra components are built from source at a pinned tag, not installed from
  apt; bumping means editing the tags in this role.
- Source clones are removed after installation so they never reach a layer.

## Key references

Verified anchor points (line numbers as of 2026-09-03):

- `ansible/roles/xpra_setup/tasks/main.yml:4` — Xpra `v6.4.3` clone
- `ansible/roles/xpra_setup/tasks/main.yml:28` — xpra-html5 `v19` clone
- `ansible/roles/xpra_setup/tasks/main.yml:45` — VirtualGL from releases
