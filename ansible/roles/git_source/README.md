# git_source Role

Builds upstream git from its source release on kernel.org and installs it under
`git_source_prefix` (`/usr/local`), ahead of Ubuntu's git on `PATH`. Ubuntu's
`git` package stays installed because `gh`, `docker-ce` and `git-lfs` depend on
it. The role fails when `git` on `PATH` is not the pinned build.

`git_source_version` carries a `# renovate:` comment that tracks the `git/git`
release tags; the post-upgrade script recomputes `git_source_checksums` in the
same commit. The build is skipped when the installed git already reports the
pinned version.
