---
type: adr
stage: accepted
---

# Extra CA trust goes through the system store

A host behind a TLS-intercepting proxy hands its CA bundle over as a file.
`agentdev_runtime.bootstrap@install_extra_ca`, in the root bootstrap, adds it to
the system store before any service starts. `agentdev-base` sets
`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, and `NODE_EXTRA_CA_CERTS` to the system
bundle, because uv, Python `requests`, Node, and Bun otherwise read their own
root stores.

## Considered Options

- Mount the bundle over `/etc/ssl/certs/ca-certificates.crt`. Rejected: this
  works only when the bundle also carries every public root, and it hides the
  image's own store.
- Point `SSL_CERT_FILE` at the mounted bundle. Rejected: it has the same
  dependence on a complete bundle, and the nested `dockerd` and every OpenSSL
  tool that reads the hashed store still do not trust the CA.
- Per-tool settings, such as `UV_SYSTEM_CERTS` and the pip and npm
  configuration. Rejected: one is needed for each tool, and each new tool is a
  new gap.
- Copy the CA into the image at build time. Rejected: the proxy belongs to the
  host, not the image, and its CA rotates.

## Consequences

- The nested `dockerd` reads the system store, so image pulls trust the CA
  without a daemon setting.
- The containers that the Dev Container engine starts do not get the CA:
  trusting it is the business of their own images.
