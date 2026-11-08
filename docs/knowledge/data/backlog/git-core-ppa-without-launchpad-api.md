---
type: task
created: 2026-11-02
stage: cancelled
priority: high
description: Add the Git Core PPA in the dev_tools role as an explicit repository entry with a pinned signing key instead of the ppa:git-core/ppa shorthand, so building the image no longer depends on the Launchpad API.
sources:
- resource: ansible/roles/dev_tools/tasks/main.yml
- resource: ansible/roles/github_cli/tasks/main.yml
- resource: ansible/roles/install_docker/tasks/main.yml
---

# Add the Git Core PPA without the Launchpad API

The `dev_tools` role adds Git's PPA with
`ansible.builtin.apt_repository: repo: ppa:git-core/ppa`. With the `ppa:`
shorthand, the module asks the Launchpad API for the PPA's signing key before it
writes the source. When that API is slow or down, the step fails, and the
Development image cannot be built on any architecture. The package archive
itself, `ppa.launchpadcontent.net`, is a separate host and does not depend on
that API.

## Work

- Commit the PPA's public signing key to the role, pinned by its fingerprint,
  and install it under `/etc/apt/keyrings/`.
- Replace the shorthand with an explicit
  `deb [arch=… signed-by=…] https://ppa.launchpadcontent.net/git-core/ppa/ubuntu <dist> main`
  entry. Use the form the `github_cli`, `install_docker`, and `cmake_kitware`
  roles already use.
- Keep the source's `filename` (`git-core-ppa`), so an image that already has
  the PPA ends up with the same single source file.

## Done when

- Building the image makes no request to `launchpad.net` or `api.launchpad.net`.
- `git` still installs from the PPA.
- A rotated PPA key fails the build with a signature error, rather than being
  trusted silently.
