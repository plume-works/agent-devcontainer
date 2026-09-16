---
type: architecture
description: Why a pull request from a fork builds both images but publishes nothing, why the desktop image then builds on the published base, and why chaining the two builds through a local registry was rejected.
generated:
  by: claude-code/opus-5
  at: 2026-09-16T07:19:49Z
sources:
- resource: .github/workflows/ci.yml
- resource: .github/actions/docker/build-push-action/action.yml
---

# Fork pull request builds

## Decision

A pull request from a fork **builds both images and publishes neither**. One
verdict, `publish`, is computed once in `ci.yml`'s `paths-filter` job and gates
every registry write: the per-architecture pushes, the digest artifacts, the
manifest merge, and the digest-pin patch in the devcontainer smoke test. The run
says so in a warning and its job summary rather than failing.

Because a fork run pushes nothing, the desktop image cannot be built `FROM` the
base the same run produced. It is built on the published `ubuntu-ansible:edge`
instead. The devcontainer smoke test keeps the committed pin for the same
reason.

## Problem this solved

A fork's `GITHUB_TOKEN` is read-only whatever the workflow's `permissions` block
declares, and `ghcr.io` rejects the push rather than the login. An unconditional
push therefore turns every fork pull request red only after a full
multi-architecture image build — the most expensive way to discover that the
token was never going to work.

## What a fork run does and does not verify

Both Dockerfiles build, so a fork pull request proves the image sources are
buildable on both architectures. It does **not** verify the two images composed:
the desktop build consumes the last published base, not the one the run just
built, so a change under `docker/ansible/` is built but never exercised by the
desktop build or the smoke test. A same-repository run covers that composition,
which is what makes this acceptable.

## Alternatives considered

**Chain the two builds through a registry the fork can write.** A `registry:2`
service container on the runner, or buildx's local image store, would let the
desktop image build on the base the same run produced and restore full
verification. Rejected as disproportionate: it adds a second, fork-only build
topology to maintain beside the one that publishes, and the composition it would
verify is verified on every same-repository run and again in the merge queue.

**Skip the image jobs entirely for a fork.** Cheapest, and it was rejected
because it makes the check meaningless exactly where review is least privileged:
a fork contributor would get a green run that compiled nothing.

**Grant the push another way** — a PAT, or `pull_request_target`. Rejected: a
write credential reachable from unreviewed pull request code is the one thing
the read-only fork token is protecting.

## Consequences

- Every new registry write in `ci.yml` has to hang off `publish`; adding one
  that does not reintroduces the red fork check.
- `docker/build-push-action`'s `push` and `export-digest` inputs travel together
  — a build that pushes nothing produces no digest for the merge to assemble,
  which is why the merge job is skipped rather than fed an empty set.
- Jobs downstream of a skipped merge need an explicit `always()` condition, and
  the `finished` aggregate treats a skipped job as a pass.
- A fork run depends on `ubuntu-ansible:edge` being published and public.
