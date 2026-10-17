---
type: bug
description: With the egress firewall enabled, Docker Hub pulls fail because blob downloads now come from production.cloudfront.docker.com, which the shipped allowlist does not include.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T23:55:00Z
sources:
- resource: .devcontainer/firewall-allowlist.txt
- resource: ansible/roles/devcontainer_firewall/files/init-firewall.sh
- resource: scripts/tests/test_agent_runtime_firewall.py
---

# Bug: firewalled Docker Hub pulls fail at the CloudFront CDN

## Symptom

With `ENABLE_FIREWALL=true`, `docker pull` or `docker run` of a Docker Hub image
gets the manifest but fails fetching the first layer:
`failed to do request: Get "https://production.cloudfront.docker.com/registry-v2/...": dial tcp 52.85.151.38:443: connect: no route to host`.

## Reproduction

1. Start a privileged container from `agent-desktop` with a nested `dockerd`,
   after running `init-firewall.sh` with an allowlist holding the shipped Docker
   entries: `registry-1.docker.io`, `auth.docker.io`, and
   `production.cloudflare.docker.com`.
2. Run `docker run --rm hello-world`; the blob fetch fails as above.
3. Add `production.cloudfront.docker.com` to the allowlist and repeat; the pull
   succeeds. `test_proxy_ingress_egress_and_nested_docker_together` runs exactly
   this, with the extra entry.

## Root cause

Docker Hub's registry redirects blob downloads to
`production.cloudfront.docker.com`. The allowlist names only the Cloudflare CDN
host, so the address is not in the `allowed-domains` ipset. The final `OUTPUT`
rule rejects it with `icmp-admin-prohibited`, which the client reports as "no
route to host".

## Fix

Not fixed. Add `production.cloudfront.docker.com` beside
`production.cloudflare.docker.com` in `.devcontainer/firewall-allowlist.txt`.
The standalone image bakes that file as its default allowlist, so the fix covers
both runtimes.

## Key references

Verified anchor points (line numbers as of 2026-10-17):

- `.devcontainer/firewall-allowlist.txt:52` —
  `production.cloudflare.docker.com`, the only Docker CDN entry
- `ansible/roles/devcontainer_firewall/files/init-firewall.sh:136` — the final
  `OUTPUT` REJECT rule
- `scripts/tests/test_agent_runtime_firewall.py:150` — the test allowlist that
  adds the CloudFront host
