# Optional image-source contributor instructions

These instructions apply when retaining the optional Ansible image-customization source.

## Validation

Run every Ansible command from the **repository root**, not from this directory:
`ansible.cfg` lives at the root and Ansible only auto-loads it from the current
working directory. Running from here silently loses the inventory and roles path.

- Run `uv run ansible-lint ansible` from the repository root.
- Run `uv run ansible-playbook --syntax-check ansible/playbooks/setup-dev.yml` from the
  repository root.
- The real validation gate is a local image build documented in the repository README.

## Role conventions

- Give each role one responsibility.
- Prefix role variables with the role name (`dev_tools_*`, `agentic_tools_*`). The shared
  facts `workspace_folder`, `user_home`, and `dev_user` are the documented exceptions.
- Roles must be independently runnable. Do not rely on a `register:` from another role
  without tolerating it being undefined.
- Pin every external download. A binary or archive fetched directly needs a version
  and a per-architecture checksum, as `dev_tools` does for `zizmor`. A tool installed
  through an upstream installer or package registry is pinned by version alone, in the
  role's `defaults/`, under a `# renovate:` comment naming its datasource — Renovate
  cannot update a checksum, so a checksum on those pins would leave every automerged
  bump with a stale one. Track a commit instead of a version only where the upstream's
  tags are unusable, as `fish_setup` does for `bass`.
- Apt packages are pinned per Ubuntu release and architecture in the generated
  `roles/<role>/vars/apt_pins_<suite>_<arch>.yml`. The role loads the file matching
  `system_dist` and `system_arch` and hands apt the `name=version` list it holds. Add or
  remove a package name by editing the file, then run `scripts/apt-pins-refresh.py` to
  resolve the versions. A role that enables an apt repository of its own resolves against
  a wider set than the Ubuntu archive: record it in that script's `ROLE_REPOS` and in the
  matching `registryUrls` rule in `.github/renovate.json`, which must agree or the two
  will revert each other.
- Read paths that vary per consuming project from `DEV_WORKSPACE_FOLDER` at runtime, with
  `workspace_folder` as the fallback. Never hardcode a workspace path.
