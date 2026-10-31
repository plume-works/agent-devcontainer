---
type: codebase
description: Installs Xpra from the Xpra stable apt repository and its HTML5 client from a pinned tag, installs VirtualGL from GitHub releases, and adds Mesa software rendering.
source: ansible/roles/xpra_setup
source_digest: sha256:f788a1cf9b53394b5295e5ecfac00c4d31a361e5d2a01ceb89530d124d7d0aea
verified:
  by: claude-code/opus-5.5
  at: 2026-10-19T23:09:19Z
stale_after: 2027-01-17
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T23:09:19Z
sources:
- id: code
  resource: ansible/roles/xpra_setup
---

# xpra_setup role

The largest single addition to the image, behind `install_xpra`: a remote
desktop reachable through a browser.

## Public surface

- `xpra` and the HTML5 client on the image; started by `agentdev-runtime xpra`
  in the [agentdev_runtime package](../../py_packages/agentdev_runtime.md) at
  container start
- VirtualGL and Mesa/llvmpipe for GL inside the container

## How it works

Adds the Xpra signing key and the stable repository (`https://xpra.org`) for the
distribution codename and architecture, installs `xpra` from apt, upgrades a
preinstalled one to the repository's release, and fails unless the installed
version is at least 6; then clones `xpra-html5` at `v19` and runs its
`setup.py install`; downloads the VirtualGL `.deb` for the detected architecture
from GitHub releases and installs it; installs the Mesa, OpenGL, and Xvfb
packages, including the software renderer.

## Depends on

`basic_prereqs` for build prerequisites. The role derives the architecture from
`ansible_facts` itself. The port and display conventions are owned by the start
script, not this role.

## Invariants & gotchas

- `xpra` is installed unpinned, at whatever the stable repository serves
  (`architecture/ansible-apt-pins`). Ubuntu's archive ships an older `xpra`; the
  version assertion fails the build if apt resolves that one instead.
- VirtualGL is a `.deb` downloaded by URL and verified by a per-architecture
  checksum, not an apt install. Its version, checksums, and URL live in
  `defaults/main.yml` under a `# renovate:` comment; Renovate bumps the version
  and `scripts/refresh-pin-checksums.py` recomputes the checksums.
- The `xpra-html5` clone is removed after installation so they never reach a
  layer.

## Key references

Verified anchor points (line numbers as of 2026-10-19):

- `ansible/roles/xpra_setup/tasks/main.yml:14` — Xpra stable repository
- `ansible/roles/xpra_setup/tasks/main.yml:23` — the `xpra` apt install
- `ansible/roles/xpra_setup/tasks/main.yml:31` — upgrade of a preinstalled
  `xpra`
- `ansible/roles/xpra_setup/tasks/main.yml:46` — the Xpra 6 version assertion
- `ansible/roles/xpra_setup/tasks/main.yml:51` — xpra-html5 `v19` clone
- `ansible/roles/xpra_setup/tasks/main.yml:68` — VirtualGL from releases
- `ansible/roles/xpra_setup/defaults/main.yml:4-11` — VirtualGL version,
  checksums, and download URL
