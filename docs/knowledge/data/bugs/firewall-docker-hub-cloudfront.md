---
type: bug
stage: pending
severity: medium
description: With the egress firewall enabled, Docker Hub pulls fail because blob downloads now come from production.cloudfront.docker.com, which the shipped allowlist does not include.
sources:
- resource: .devcontainer/firewall-allowlist.txt
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: scripts/tests/test_agent_runtime_firewall.py
---

# Bug: firewalled Docker Hub pulls fail at the CloudFront CDN

## Symptom

With `ENABLE_FIREWALL=true`, `docker pull` or `docker run` of a Docker Hub image
gets the manifest but fails fetching the first layer:
`failed to do request: Get "https://production.cloudfront.docker.com/registry-v2/...": dial tcp 52.85.151.38:443: connect: no route to host`.

## Reproduction

1. Start `agentdev-devcontainer` with `ENABLE_FIREWALL=true`, so the bootstrap
   applies `agentdev-runtime firewall apply` before the nested engine starts,
   with an allowlist holding the shipped Docker entries: `registry-1.docker.io`,
   `auth.docker.io`, and `production.cloudflare.docker.com`.
2. Run `docker run --rm hello-world`; the blob fetch fails as above.
3. Add `production.cloudfront.docker.com` to the allowlist and repeat; the pull
   succeeds.

## Root cause

Docker Hub's registry redirects blob downloads to
`production.cloudfront.docker.com`. The allowlist names only the Cloudflare CDN
host, so the address is not in the `allowed-domains` ipset. The final `OUTPUT`
rule rejects it with `icmp-admin-prohibited`, which the client reports as "no
route to host".

## Potential solution

Add `production.cloudfront.docker.com` beside `production.cloudflare.docker.com`
in `.devcontainer/firewall-allowlist.txt`. The image copies that file to
`/etc/agentdev/firewall-allowlist.txt` as its default allowlist, so the fix also
covers a checkout that ships none.

## Key references

- `.devcontainer/firewall-allowlist.txt › "production.cloudflare.docker.com"` —
  `production.cloudflare.docker.com`, the only Docker CDN entry
- `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply_policy` —
  the final `OUTPUT` REJECT rule
- `scripts/tests/test_agent_runtime_firewall.py::RUNTIME_SCRIPT` — the test
  allowlist that adds the CloudFront host
