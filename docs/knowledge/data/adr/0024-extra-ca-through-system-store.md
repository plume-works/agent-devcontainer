---
type: adr
stage: accepted
description: The root bootstrap adds an extra CA bundle from the host to the system store, and the images point each tool with its own root store at the system store.
---

# Extra CA trust goes through the system store

A host behind a TLS proxy that intercepts traffic gives its CA bundle as a file.
`agentdev_runtime.bootstrap::install_extra_ca` adds it to the system store
before a service starts. `agentdev-base` sets `SSL_CERT_FILE`,
`REQUESTS_CA_BUNDLE`, and `NODE_EXTRA_CA_CERTS` to the system bundle, because
uv, Python `requests`, Node, and Bun otherwise read their own root stores.

## Considered Options

- Mount the bundle over `/etc/ssl/certs/ca-certificates.crt`. Rejected: this
  works only when the bundle also holds all public roots, and it hides the store
  of the image.
- Set `SSL_CERT_FILE` to the mounted bundle. Rejected: it also needs a complete
  bundle, and the nested `dockerd` and the OpenSSL tools that read the hashed
  store do not trust the CA.
- A setting for each tool, such as `UV_SYSTEM_CERTS`. Rejected: each new tool is
  a new gap.
- Copy the CA into the image at build time. Rejected: the proxy belongs to the
  host, and its CA changes.

## Consequences

- With no extra CA, the variables name the stock bundle and change nothing.
- The nested `dockerd` reads the system store, so image pulls trust the CA.
- `.devcontainer/devcontainer-init.sh` uses the host `NODE_EXTRA_CA_CERTS` when
  the operator does not set `AGENTDEV_EXTRA_CA_CERTS`.
- The containers that the Dev Container engine starts do not get the CA.
