---
type: architecture
description: The runtime images trust a TLS-intercepting proxy's CA by having the root bootstrap install an extra PEM bundle into the system store, and the base image points the per-tool CA variables at that store; the Dev Container host hands its bundle over through devcontainer-init.sh.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/trust.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/settings.py
- resource: docker/base/agentdev-base.Dockerfile
- resource: .devcontainer/devcontainer-init.sh
- resource: .devcontainer/docker-compose.yml
- resource: scripts/tests/test_agent_runtime_trust.py
- resource: scripts/tests/test_agent_runtime_acceptance.py
---

# Extra CA trust

## Decision

A host whose egress goes through a TLS-intercepting proxy hands the proxy's CA
bundle to the runtime as a file at `AGENTDEV_EXTRA_CA_CERTS`
(`/etc/agentdev/extra-ca.crt` by default). The root bootstrap, in both profiles
and before supervisord starts any service, splits the bundle into one file per
certificate under `/usr/local/share/ca-certificates/agentdev-extra-*.crt` and
runs `update-ca-certificates`. The store then holds exactly the current bundle:
entries from an earlier start are withdrawn first, and an absent or empty bundle
adds nothing. A non-empty bundle with no PEM certificate fails the bootstrap.

`agentdev-base` sets `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, and
`NODE_EXTRA_CA_CERTS` to `/etc/ssl/certs/ca-certificates.crt`. uv, Python
`requests`, Node, and Bun otherwise read their own root stores and would ignore
the system one. With no extra CA the variables name the stock system bundle, so
they change nothing.

The nested `dockerd` reads the system store directly, so image pulls inside the
runtime are covered without a daemon setting.

## Dev Container wiring

`devcontainer-init.sh` runs on the host and always writes
`.devcontainer/.extra-ca.crt` (git-ignored): a copy of `AGENTDEV_EXTRA_CA_CERTS`
when the host sets it, else of `NODE_EXTRA_CA_CERTS` when that names a readable
file, else empty. The Compose service bind-mounts it read-only at
`/etc/agentdev/extra-ca.crt`. An explicit `AGENTDEV_EXTRA_CA_CERTS` that is not
readable fails the init script.

`NODE_EXTRA_CA_CERTS` is the fallback because it means "CAs added to the
defaults", which is exactly this bundle; hosts behind such proxies, Claude Code
cloud sessions among them, already export it.

## Constraints

- The bundle is read once per container start. A rotated proxy CA needs a
  container restart, and a changed host bundle needs `devcontainer-init.sh` to
  run again.
- Containers that the nested `dockerd` starts get no extra CA; trusting it is
  their image's business.

## Rejected alternatives

- **Mounting the bundle over `/etc/ssl/certs/ca-certificates.crt`.** It works
  only when the bundle also carries every public root, and it hides the image's
  own store.
- **Pointing `SSL_CERT_FILE` at the mounted bundle.** Same dependence on a
  complete bundle, and it leaves the nested `dockerd` and every OpenSSL tool
  reading the hashed store untrusting.
- **Per-tool settings (`UV_SYSTEM_CERTS`, pip and npm config).** One per tool,
  and each new tool is a new gap; the system store plus three variables covers
  the image's tools.
- **Copying the CA into the image at build time.** The proxy belongs to the
  host, not the image, and its CA rotates.
