---
type: codebase
description: Installs Xpra from the Xpra stable apt repository and its HTML5 client from a pinned tag, installs VirtualGL from GitHub releases, and adds Mesa software rendering.
source: ansible/roles/xpra_setup
source_digest: sha256:65e18f6d1916581fce3e644976a5385785dcd20d7edd13320ed098edc32c58bb
verified:
  by: claude-code/opus-5.5
  at: 2026-10-19T18:45:02Z
stale_after: 2027-01-17
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T18:45:02Z
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

Adds the Xpra signing key and the stable repository (`https://xpra.org`) for the
distribution codename and architecture, installs `xpra` from apt, and fails
unless the installed version is at least 6; then clones `xpra-html5` at `v19`
and runs its `setup.py install`; downloads the VirtualGL `.deb` for the detected
architecture from GitHub releases and installs it; installs the Mesa, OpenGL,
and Xvfb packages, including the software renderer.

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
- `ansible/roles/xpra_setup/tasks/main.yml:37` — the Xpra 6 version assertion
- `ansible/roles/xpra_setup/tasks/main.yml:42` — xpra-html5 `v19` clone
- `ansible/roles/xpra_setup/tasks/main.yml:59` — VirtualGL from releases
- `ansible/roles/xpra_setup/defaults/main.yml:4-11` — VirtualGL version,
  checksums, and download URL
