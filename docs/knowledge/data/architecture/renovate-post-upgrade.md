---
type: architecture
description: How the self-hosted Renovate's one post-upgrade task produces the checksums, lock file, and pre-commit output a bump implies, and the constraints that keep its output in Renovate's commit.
generated:
  by: claude-code/opus-5
  at: 2026-09-26T12:00:00Z
sources:
- resource: .github/renovate.json
- resource: scripts/renovate-post-upgrade.sh
- resource: scripts/refresh-pin-checksums.py
- resource: https://github.com/renovatebot/renovate/blob/main/lib/workers/repository/update/branch/execute-post-upgrade-commands.ts
  title: Post-upgrade output is kept only where its path matches fileFilters
- resource: https://github.com/renovatebot/renovate/blob/main/lib/workers/repository/update/branch/commit.ts
  title: A branch commit is Renovate's package files followed by post-upgrade artifacts
- resource: https://github.com/pre-commit/pre-commit/blob/main/pre_commit/languages/docker.py
  title: pre-commit remaps docker hook paths from the container ID in /proc/1/mountinfo
---

# Renovate post-upgrade task

## Decision

`.github/renovate.json` declares one top-level `postUpgradeTasks` in `branch`
mode, running `scripts/renovate-post-upgrade.sh`, and `renovate.yml` allows
exactly that command through the anchored `allowedCommands` pattern. The script
derives the bump from `git diff HEAD` in Renovate's clone and, in order:

1. recomputes the per-architecture SHA-256 of every pin in a changed pin file
   (`scripts/refresh-pin-checksums.py`), failing when an asset cannot be fetched
   or a pin whose version is unchanged hashes differently;
2. regenerates `.devcontainer/devcontainer-lock.json` with the devcontainer CLI
   when `devcontainer.json` changed;
3. runs pre-commit on every changed file, accepting a first pass that only
   rewrites files and failing on a hook that still fails on the second.

Any failure fails the branch, so no pull request carries a version beside a
stale checksum or lock.

`refresh-pin-checksums.py` renders each download URL from the consuming role's
own templates — the `dev_tools` install task's expressions, or a
`*_download_url` default — so it fetches exactly what the image build fetches. A
new checksum-carrying pin needs its file registered in `PIN_FILES`.

## `fileFilters` enumerates every path Renovate edits

Renovate commits its own edits first and the post-upgrade output after them, and
keeps post-upgrade output only where the path matches `fileFilters` — a file
Renovate itself edited included. A pre-commit rewrite of a bumped file outside
the filters is silently dropped. The filters therefore list every path a
Renovate manager in this repository edits, plus the derived files; adding a
manager, or a file one manages, extends the list.

## pre-commit runs through uv

The script calls `uv run --frozen pre-commit`, never the image's apt
`pre-commit`. Inside a CI container job, a `docker_image` hook such as
`hadolint-docker` bind-mounts paths the host daemon must resolve; pre-commit 4
maps them back to host paths by finding its own container through
`/proc/1/mountinfo`, while the 3.x the image's apt ships looks in
`/proc/1/cgroup`, which carries no container ID on cgroup v2 hosts. The
project's `pre-commit>=4.2.0` dependency is what makes the hook work there.

## Rejected alternatives

**A `postUpgradeTasks` per pin kind.** `postUpgradeTasks` is an object that a
later matching `packageRule` replaces rather than extends, so a checksum rule
would silently drop the pre-commit step. One script behind one task has no
override ordering to get wrong.
