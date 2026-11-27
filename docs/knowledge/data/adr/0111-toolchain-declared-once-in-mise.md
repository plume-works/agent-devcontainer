---
type: adr
stage: accepted
---

# The toolchain is declared once, in mise files, and installed by one script

The devcontainer image, a Claude Code cloud session's host, and a native macOS
host each provisioned the same release tools their own way, with versions and
checksums repeated in each. The maintainer decided that `mise.toml` declares the
tools the catalog runs, `mise.dev.toml` adds the binaries this repository's
hooks run, and `mise.image.toml` adds VirtualGL for the image. Their lockfiles
record each download's URL and SHA-256 for every platform the tool serves.
`scripts/install-toolchain` installs the lists that `MISE_ENV` selects with
`mise install --locked` and links each tool's binaries into a directory on
`PATH`: `/usr/local/bin` in the image and on a cloud host, `~/.local/bin` on
macOS. Renovate's mise manager bumps a version and runs `mise lock` in the same
commit, so no checksum is refreshed by hand.

## Considered Options

- One list for every host. Rejected: a macOS host that only runs the catalog
  does not need the hooks' linters.
- Activate mise, or put its shims on `PATH`, instead of linking the binaries.
  Rejected: pre-commit hooks, `uv run`, and non-interactive shells would then
  find a tool only where mise is activated.

## Consequences

- A linked tool replaces the base image's copy at the same path, so the version
  in `mise.toml` wins over the base image's uv, Bun, gh, and jq.
- A Linux host without mise gets the release that `scripts/install-toolchain`
  pins, checked against the musl asset's SHA-256 that the script commits per
  architecture. When Renovate bumps `MISE_VERSION`,
  `scripts/renovate-post-upgrade.py` refreshes those digests from the release's
  checksum list, so the Renovate pull request diff shows them for review. macOS
  gets mise from Homebrew, unpinned.
- `bin/macos-bootstrap.zsh` downloads `scripts/install-toolchain`, `mise.toml`,
  and `mise.lock` from the repository, because an installed plugin has no
  checkout around it.
- VirtualGL is a package file, not a binary: the image installs it with apt from
  where mise downloaded it, and links nothing from it.
