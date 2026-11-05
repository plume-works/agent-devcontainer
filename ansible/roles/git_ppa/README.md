# git_ppa Role

Installs the Git Core PPA's `git` and `git-man` packages for Ubuntu 24.04 from
their unchanged copies in the
[plume-works/git-releases](https://github.com/plume-works/git-releases)
releases. apt installs both in one transaction, replacing Ubuntu's `git`, and
resolves their other dependencies from the Ubuntu archive. The role fails when
the installed `git` package is not the pinned build.

`git_ppa_version` is a release tag of that repository; its `# renovate:` comment
tracks new releases, and the post-upgrade script recomputes `git_ppa_checksums`
and `git_ppa_man_checksums` in the same commit.
