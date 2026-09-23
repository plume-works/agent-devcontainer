---
type: codebase
description: Builds Xpra and its HTML5 client from pinned tags, installs VirtualGL from GitHub releases, and adds Mesa software rendering.
source: ansible/roles/xpra_setup
source_digest: sha256:d15d7b9dac09a38e26d2d77bb2f578c907279db999eb3bb7099cbbe45dd73b33
verified:
  by: claude-code/opus-5
  at: 2026-09-22T00:00:00Z
stale_after: 2026-12-21
generated:
  by: claude-code/opus-5
  at: 2026-09-22T00:00:00Z
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

Clones the Xpra repository at tag `v6.4.3` and runs its
`setup.py install-lts-repo`, then does the same for `xpra-html5` at `v19`;
installs the `xpra` package from apt at its pinned version; downloads the
VirtualGL `.deb` for the detected architecture from GitHub releases and installs
it; installs the Mesa, OpenGL, and Xvfb packages, including the software
renderer.

## Depends on

`basic_prereqs` for build prerequisites and `extra_facts` for the architecture.
The port and display conventions are owned by the start script, not this role.

## Invariants & gotchas

- The clones supply the upstream repository definitions, not the binaries: what
  lands on the image is the apt `xpra` at the version in
  `vars/apt_pins_<suite>_<arch>.yml`, resolved against the Ubuntu archive.
  Moving to the LTS stream means adding that repository to `ROLE_REPOS` in
  `scripts/apt-pins-refresh.py` and to the `registryUrls` rules in
  `.github/renovate.json`, not editing the clone tags alone.
- VirtualGL is the one package here that is not apt-pinned: it is a `.deb`
  downloaded by URL and verified by a per-architecture checksum.
- Source clones are removed after installation so they never reach a layer.

## Key references

Verified anchor points (line numbers as of 2026-09-22):

- `ansible/roles/xpra_setup/tasks/main.yml:4-6` — the pin file include
- `ansible/roles/xpra_setup/tasks/main.yml:8` — Xpra `v6.4.3` clone
- `ansible/roles/xpra_setup/tasks/main.yml:25` — the pinned `xpra` install
- `ansible/roles/xpra_setup/tasks/main.yml:31` — xpra-html5 `v19` clone
- `ansible/roles/xpra_setup/tasks/main.yml:58` — VirtualGL from releases
