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
- Pin every external download with a version and a per-architecture checksum, as
  `dev_tools` does for `zizmor`.
- Read paths that vary per consuming project from `DEV_WORKSPACE_FOLDER` at runtime, with
  `workspace_folder` as the fallback. Never hardcode a workspace path.
