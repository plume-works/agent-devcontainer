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

- The file is at `AGENTDEV_EXTRA_CA_CERTS`. The bootstrap writes one file for
  each certificate in it as `agentdev-extra-*.crt`, and first removes the files
  of an earlier start. As a result, the store holds only the extra CAs of the
  current bundle.
- An empty or missing bundle adds nothing. A bundle that is not empty but has no
  PEM certificate stops the bootstrap.
- The bootstrap reads the bundle one time at each container start. A new CA of
  the proxy needs a container restart.
- With no extra CA, the variables name the stock bundle and change nothing.
- The nested `dockerd` reads the system store, so image pulls trust the CA.
- `.devcontainer/devcontainer-init.sh` writes `.devcontainer/.extra-ca.crt`, and
  Compose mounts it read-only at `/etc/agentdev/extra-ca.crt`. The script copies
  the host `AGENTDEV_EXTRA_CA_CERTS`, If it cannot, it copies the host
  `NODE_EXTRA_CA_CERTS`. If neither is set, it writes an empty file.
  `NODE_EXTRA_CA_CERTS` names the CAs that a host adds to the defaults, so it
  holds the same bundle.
- A host `AGENTDEV_EXTRA_CA_CERTS` that the script cannot read stops the script.
  A changed host bundle needs the script to run again.
- The containers that the Dev Container engine starts do not get the CA.
