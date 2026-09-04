---
type: codebase
description: Builds Xpra and its HTML5 client from pinned tags, installs VirtualGL from GitHub releases, and adds Mesa software rendering.
source: ansible/roles/xpra_setup
source_digest: sha256:9470828b4489b4bdee4f40dbd1694839ced71189da6ea175e33319633787f198
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
sources:
- id: code
  resource: ansible/roles/xpra_setup
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

Verified anchor points (line numbers as of 2026-09-04):

- `ansible/roles/xpra_setup/tasks/main.yml:4` — Xpra `v6.4.3` clone
- `ansible/roles/xpra_setup/tasks/main.yml:28` — xpra-html5 `v19` clone
- `ansible/roles/xpra_setup/tasks/main.yml:45` — VirtualGL from releases
