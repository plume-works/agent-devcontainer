---
type: feature
stage: accepted
description: Run Renovate from a workflow inside the pinned agent-desktop image so post-upgrade tasks refresh checksum pins, lock files, and pre-commit output in the same commit as a bump.
generated:
  by: claude-code/opus-5
  at: 2026-09-25T00:00:00Z
sources:
- id: roles
  resource: ansible/roles
- id: renovate-config
  resource: .github/renovate.json
- id: renovate-options
  resource: https://docs.renovatebot.com/self-hosted-configuration/
- resource: .pre-commit-config.yaml
- resource: .devcontainer/devcontainer-lock.json
---

# Renovate maintains checksum-carrying pins

## Purpose

Three groups of pins carry a per-architecture SHA-256 beside their version:
`dev_tools_pinned_tools` (iwe, codebase-memory-mcp, bun, and zizmor), cc-filter,
and VirtualGL. Renovate can move the version but not the hash next to it, so an
automated bump would leave a stale checksum and fail the image build at download
time. They are maintained by hand, and go stale because nothing prompts a bump.

The same gap covers every file a bump implies but Renovate does not write
itself: `.devcontainer/devcontainer-lock.json` after a feature bump, and the
pre-commit output for the files a bump touched.

Renovate's `postUpgradeTasks` runs a command after the version bump and before
the commit, which is enough to produce all of these in the same pull request.
Which commands may run is gated by `allowedCommands`, a **global-only** option
that repository configuration cannot set. While Renovate runs as the hosted app
that gate belongs to the app operator, so the feature is unreachable from here.
Running Renovate from a workflow in this repository moves the gate into this
repository.

## Behaviour

**Renovate runs from a workflow in this repository, inside agent-desktop.** It
runs on push to `main`, daily, and on manual dispatch, in the
`ghcr.io/plume-works/agent-desktop` digest the devcontainer pins, so
post-upgrade commands have the contributor toolchain. `.github/renovate.json`
keeps its present meaning — repository policy — and the workflow supplies the
self-hosted global configuration alongside it, including `allowedCommands`.

**One Renovate version.** The workflow runs Renovate per run through `bunx`, at
the version the `renovate-config-validator` pre-commit hook pins in its
`bunx --package renovate@<version>` entry. Hook, validation workflow, and bot
therefore never disagree, Renovate is not provisioned into the image, and a bump
of that pin automerges once the validation check passes at the new version.

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
is allowed to contribute to the commit. zizmor is the exception: its version
belongs to the Super-Linter parity contract and moves only with it.

**Derived files move with the bump.** The same post-upgrade command regenerates
the devcontainer lock when a feature reference changes and runs pre-commit on
the changed files. `uv.lock` is relocked by Renovate's own `pep621` manager, and
lock file maintenance refreshes it periodically.

**A failed post-upgrade command fails the branch.** A pull request that carries
a new version beside an unverified or unchanged hash is worse than no pull
request, because the build failure it causes surfaces far from its cause.

**Checksum bumps automerge**, like the version-only pins they join.

**Every agent-desktop reference shares one pin.** Workflow jobs that run in the
image pin the same digest as the devcontainer, moved together by one group, and
a required check runs inside the new digest before a bump can merge.

**Digest masks extend to the new pins.** Automerged bumps would otherwise mark
every map doc sourcing `ansible` or `.github` stale while its prose stays
accurate — the defect recorded in
[Pin bumps invalidate map docs](../bugs/pin-bumps-invalidate-map-docs.md). The
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

Out of scope: `updatecli` and a repository-local refresh loop, both considered
and set aside because Renovate already owns dependency updates here; apt
packages, which stay unpinned; and the Ubuntu base release.

## References

- Repository policy: `.github/renovate.json`
- Pins concerned: `ansible/roles/dev_tools/defaults/main.yml`,
  `ansible/roles/agentic_tools/defaults/main.yml`,
  `ansible/roles/xpra_setup/tasks/main.yml`
