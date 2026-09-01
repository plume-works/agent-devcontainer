# Validate Agent Files Role

Installs the `validate_agent_files` CLI into the image so a project using this image
as its devcontainer can validate its agents, skills, and prompts with no checkout of
the publisher repository and no `uv run` prefix.

Gated by `install_validate_agent_files` in the playbook.

## Where it comes from

The package is not published to PyPI, so the role builds it from the provisioning
sources — the same arrangement as the staged agent catalog, and with the same
consequence: the role only works while `py_packages/validate_agent_files/` is in the
tree the playbook reads. A consuming project that deletes the publisher source but
keeps this image bundle must build with `install_validate_agent_files=false`.

The build context is bind-mounted read-only and `setuptools` writes `*.egg-info`
into the source tree while preparing metadata, so the role copies the package out to
a temporary directory before building. Installing in place fails with
`Operation not permitted`.

## What it produces

```text
/usr/local/bin/validate_agent_files      # entry point, on PATH for every user
/opt/uv-tools/validate-agent-files/      # isolated tool environment, root-owned 0755
```

The role installs with `uv tool install` to keep the validator out of the system
interpreter and out of any `uv`-managed project environment, while putting exactly
one command on `PATH`. `/opt` keeps the tool environment outside agent and home
state that can be volume-mounted.

## Variables

| Variable                          | Default                                   | Purpose                                                                      |
| --------------------------------- | ----------------------------------------- | ---------------------------------------------------------------------------- |
| `validate_agent_files_source_dir` | `<repo>/py_packages/validate_agent_files` | Package source; the image build points it at `/provision/...`.               |
| `validate_agent_files_version`    | `""`                                      | Optional pin. When set, the installed version must match or the build fails. |
| `validate_agent_files_bin_dir`    | `/usr/local/bin`                          | Where the entry point lands.                                                 |
| `validate_agent_files_tool_dir`   | `/opt/uv-tools`                           | Root of the isolated tool environment.                                       |
| `validate_agent_files_dist_name`  | `validate-agent-files`                    | PEP 503-normalized name uv uses for the tool environment directory.          |
| `validate_agent_files_python`     | `/usr/bin/python3`                        | Interpreter for the tool environment; package requires >= 3.11.              |
| `validate_agent_files_uv`         | `/usr/local/bin/uv`                       | Installed by the `uv_setup` role, which must run first.                      |

## Ordering

Requires `uv_setup`. The playbook places this role directly after it.

## Verifying

```bash
docker run --rm <image> bash -lc 'command -v validate_agent_files && validate_agent_files --help'
docker inspect -f '{{ index .Config.Labels "org.opencontainers.image.version.validate-agent-files" }}' <image>
```
