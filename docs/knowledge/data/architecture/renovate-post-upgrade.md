---
type: architecture
description: How the self-hosted Renovate's one post-upgrade task produces the checksums, lock file, and pre-commit output a bump implies, and the constraints that keep its output in Renovate's commit.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T04:31:25Z
sources:
- resource: .github/renovate.json
- resource: scripts/renovate-post-upgrade.py
- resource: scripts/refresh-pin-checksums.py
- resource: scripts/fetch-pinned-tool.py
- resource: .github/workflows/primary-checks.yml
- resource: https://github.com/renovatebot/renovate/blob/main/lib/workers/repository/update/branch/execute-post-upgrade-commands.ts
  title: Post-upgrade output is kept only where its path matches fileFilters
- resource: https://github.com/renovatebot/renovate/blob/main/lib/workers/repository/update/branch/commit.ts
  title: A branch commit is Renovate's package files followed by post-upgrade artifacts
---

# Renovate post-upgrade task

## Decision

`.github/renovate.json` declares one top-level `postUpgradeTasks` in `branch`
mode, running `scripts/renovate-post-upgrade.py`, and `renovate.yml` allows
exactly that command through the anchored `allowedCommands` pattern. The script
derives the bump from `git diff HEAD` in Renovate's clone and, in order:

1. recomputes the per-architecture SHA-256 of every pin in a changed pin file
   (`scripts/refresh-pin-checksums.py`), failing when an asset cannot be fetched
   or a pin whose version is unchanged hashes differently;
2. regenerates `.devcontainer/devcontainer-lock.json` with the devcontainer CLI
   when `devcontainer.json` changed;
3. when the `dev_tools` pins changed, fetches the pinned `iwe` with
   `scripts/fetch-pinned-tool.py`, which verifies the archive against its
   recorded checksum, puts it first on `PATH`, and runs `iwe normalize`. The
   image the task runs in still carries the previous `iwe`, so a release that
   migrates `.iwe/config.toml` or reformats the graph is applied by the version
   being pinned, and the pre-commit `iwe` hooks after it run at that version;
4. runs pre-commit on every changed file, accepting a first pass that only
   rewrites files and failing on a hook that still fails on the second. The runs
   skip `no-commit-to-branch`, because Renovate's clone is still on the base
   branch and that guard is for commits (see spec/git-new-branch).

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
`pre-commit`, which is unpinned. The hooks it runs take their tools from
`uv.lock` and the image's pinned binaries (see
architecture/formatter-ownership), so the pass formats with the versions the
bump pins: `uv run` syncs the environment to a bumped `uv.lock` before it starts
pre-commit.

## CI never commits to a Renovate branch

Renovate stops updating a branch that carries a commit it did not author, so the
formatting a bump implies must arrive in Renovate's own commit, through steps 3
and 4 above. The `pre-commit` job in Primary checks never pushes a fix to any
branch; on a Renovate pull request that touches a tool-version owner it runs
every hook on every file and fails, exposing whatever the post-upgrade
pre-commit pass missed.

## The App token carries only Renovate's permissions

The post-upgrade task runs code at versions Renovate has just bumped — new
pre-commit hook revs, a new devcontainer CLI — as the same user as Renovate, so
that code can reach Renovate's token. `renovate.yml` therefore names the token's
permissions explicitly rather than inheriting everything the App installation
holds: write on contents, pull requests, issues, workflows, checks and statuses,
and read on administration and vulnerability alerts. A permission later granted
to the App does not widen this token until the workflow asks for it.

## Rejected alternatives

**A `postUpgradeTasks` per pin kind.** `postUpgradeTasks` is an object that a
later matching `packageRule` replaces rather than extends, so a checksum rule
would silently drop the pre-commit step. One script behind one task has no
override ordering to get wrong.

**Skipping the lint gate on Renovate pull requests.** It keeps Renovate's
branches free of foreign commits just as well, but leaves those pull requests
with no lint gate, so a gap in the post-upgrade pass would merge unnoticed.
