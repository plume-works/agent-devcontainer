---
type: feature
stage: proposed
description: Run Renovate from a workflow in this repository so post-upgrade tasks can refresh the per-architecture checksums that sit beside pinned versions.
generated:
  by: claude-code/opus-5
  at: 2026-09-20T00:00:00Z
sources:
- id: roles
  resource: ansible/roles
- id: renovate-config
  resource: .github/renovate.json
- id: renovate-options
  resource: https://docs.renovatebot.com/self-hosted-configuration/
---

# Renovate maintains checksum-carrying pins

## Purpose

Three groups of pins carry a per-architecture SHA-256 beside their version:
`dev_tools_pinned_tools` (zizmor, iwe, codebase-memory-mcp, bun), cc-filter, and
VirtualGL. Renovate can move the version but not the hash next to it, so an
automated bump would leave a stale checksum and fail the image build at download
time. They are maintained by hand, and go stale because nothing prompts a bump.

Renovate's `postUpgradeTasks` runs a command after the version bump and before
the commit, which is enough to recompute the hash and fold it into the same pull
request. Which commands may run is gated by `allowedCommands`, a **global-only**
option that repository configuration cannot set. While Renovate runs as the
hosted app that gate belongs to the app operator, so the feature is unreachable
from here. Running Renovate from a workflow in this repository moves the gate
into this repository and brings the checksum-carrying pins under the same
automated path as every other dependency.

## Behaviour

**Renovate runs from a workflow in this repository.** It is invoked on a
schedule and on manual dispatch. `.github/renovate.json` keeps its present
meaning — repository policy — and the workflow supplies the self-hosted global
configuration alongside it, including `allowedCommands`.

**The hosted app is disconnected in the same change.** Two Renovates against one
repository each treat the other's branches as foreign and contend over them.

**Renovate authenticates as a GitHub App rather than `GITHUB_TOKEN`.** A pull
request opened with a workflow's own token does not start further workflow runs,
so CI would never report on a Renovate pull request and automerge-on-green could
never fire.

**Checksum-carrying pins become managed pins.** Each gains a `# renovate:`
comment naming its datasource, the way the version-only pins already do. On a
bump, a post-upgrade command recomputes every architecture's SHA-256 from the
release asset and rewrites it in place; `fileFilters` narrows what that command
is allowed to contribute to the commit.

**A failed checksum refresh fails the branch.** A pull request that carries a
new version beside an unverified or unchanged hash is worse than no pull
request, because the build failure it causes surfaces far from its cause.

**Digest masks extend to the checksum pins.** Automerged bumps would otherwise
mark every map doc sourcing `ansible` stale while its prose stays accurate — the
defect recorded in
[Pin bumps invalidate map docs](../bugs/pin-bumps-invalidate-map-docs.md).
`ansible/roles/.agent.metadata.json` already masks the version-only pins under
`*/defaults/main.yml`; the checksum values need the same treatment, and
VirtualGL's pin needs a glob that reaches it in `xpra_setup/tasks/main.yml`. The
format and its resolution are
[Agent metadata files](../architecture/agent-metadata-files.md).

## Scope

A recomputed hash is trust-on-first-use. Re-downloading from the same URL and
hashing the bytes removes the toil, not the trust assumption: for a new version
there is no prior value to disagree with, and fetching a publisher's own
checksum file from the same origin proves the same amount. Verifying a
publisher's signed attestation — codebase-memory-mcp ships a sigstore bundle —
would be an improvement in verification rather than in effort, and is not part
of this.

Out of scope: the version-only pins, which already update unattended and are
unchanged in shape; `updatecli` and a repository-local refresh script, both
considered and set aside because Renovate already owns dependency updates here;
and apt packages, which stay unpinned.

## Open questions

- Whether the checksum-carrying group automerges once version and hash move
  together, or opens for review. Automerge is what the rest of the pins do; the
  trust-on-first-use property above is the argument for a human on these.
- The schedule Renovate runs on, which the hosted app previously decided.

## References

- Repository policy: `.github/renovate.json`
- Pins concerned: `ansible/roles/dev_tools/defaults/main.yml`,
  `ansible/roles/agentic_tools/defaults/main.yml`,
  `ansible/roles/xpra_setup/tasks/main.yml`
