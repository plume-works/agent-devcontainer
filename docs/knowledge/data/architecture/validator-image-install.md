---
type: architecture
description: Why validate_agent_files is built from the repository build context and installed as an isolated uv tool in the agent-desktop image, rather than published to PyPI or installed another way.
generated:
  by: claude-sonnet-5
  at: 2026-08-12T00:00:00Z
sources:
- resource: docs/agents/specs/template-reuse-validation/ (folded and removed)
---

# Validator image install

## Decision

`validate_agent_files` is installed into the `agent-desktop` image as an
isolated `uv` tool, built from the repository build context — not published to
PyPI, not installed some other way.

## Problem this solved

The template consumption guide instructed a consuming project to delete
`py_packages/validate_agent_files/` and rely on the "image-provided
`validate_agent_files`". Nothing under `ansible/` or `docker/` referenced the
package, and the command was not on `PATH` in a running container — it resolved
only through `uv run`, from the editable path dependency that the documented
deletion removes. A consumer that followed the guide and wanted agent-file
validation had no validator, in the devcontainer or in CI.

## Alternatives considered

**Install source: wheel from the build context, vs. publish to PyPI.**
`https://pypi.org/pypi/validate-agent-files/json` returned 404 — publishing
would have meant new work (name reservation, a release workflow, trusted
publishing) before this could land at all. Building from the build context
instead keeps release coupling inside this repository and matches how the
catalog is already staged (`docker/desktop/agent-desktop.Dockerfile` already
reads `.claude-plugin/` and `.agents/` from the same context under
`agentic_tools_stage_catalog=true`). The tradeoff, inherited deliberately: the
image build only works while `py_packages/validate_agent_files/` is present in
the build context — see [Template boundary](template-boundary.md).

**Installer placement: a new Ansible role, vs. a task file inside
`agentic_tools`.** A new role (`ansible/roles/validate_agent_files/`) keeps one
responsibility, its own `install_validate_agent_files` toggle, and its own
variables, matching how every other tool in the image is provisioned. It runs
directly after `uv_setup`, which it depends on.

**Isolation: `uv tool install`, not the system interpreter or a project
environment.** Puts the single entry point at
`/usr/local/bin/validate_agent_files` and the environment at
`/opt/uv-tools/validate-agent-files/`, touching neither the system interpreter
nor any project environment.

## Versioning

The package moved from `0.0.0` to `1.0.0`, pinned by
`VALIDATE_AGENT_FILES_VERSION` in `docker/desktop/agent-desktop.Dockerfile` and
surfaced as the `org.opencontainers.image.version.validate-agent-files` label.
The role reads the version back from the installed distribution and fails the
build on a mismatch, so the pin describes what the image actually carries rather
than what the source claimed.

## Implementation note

The build context is bind-mounted read-only, and `setuptools.build_meta` writes
`*.egg-info` into the source tree while preparing metadata — building in place
fails with `Operation not permitted`. The role copies the source to a temporary
directory first.

## Verified behavior (implemented, status: shipped)

1. `command -v validate_agent_files` resolves inside a container started from
   the published image, for the non-root user the devcontainer runs as.
2. `validate_agent_files --help` exits 0 there without a `uv run` prefix and
   without the repository checked out.
3. The version installed into the image is pinned and updated deliberately, the
   same way the catalog version is pinned by `AGENTDEV_PLUGIN_VERSION`.
4. A CI job running in the digest-pinned image can validate a consuming
   repository's agent files — see
   [Template consumption](../spec/template-consumption.md#agent-file-validation).
5. The image build does not depend on the consuming repository's checkout — the
   package is installed at build time, not staged for a lifecycle hook to
   install.

## Adjacent findings folded elsewhere while validating this change

End-to-end testing of both consumption workflows (full copy and existing
repository) surfaced issues unrelated to the validator install itself, all
resolved by folding them into
[Template consumption](../spec/template-consumption.md):

- `.ruff.toml` silently disabling a project's `[tool.ruff]` block — now a named
  requirement there.
- Formatter adoption rewriting verbatim third-party captures — now a named
  requirement there.
- `reformat.yml`'s dependency on
  `.agents/plugins/agentdev/bin/super-linter-env.sh` being under-specified in
  the old guide — now stated concretely as an inline-heredoc instruction.
- Smaller documentation gaps (empty `py_packages/`/`scripts/` after deletion,
  missing `pyproject.toml` dependencies, an orphaned `clean_build` workflow
  input, the `zizmor` pre-commit hook needing a host-portable alternative,
  `.gitignore` entries for generated devcontainer env files, and
  `--require-marketplace claude codex` asserting manifests a consumer does not
  have) — all folded into the guide.

One item was out of scope and stayed with its owning repository: a pre-existing
test failure in a consumer's own suite
(`test_self_test_fails_when_state_root_is_unwritable`, fails only when the suite
runs as root) — not caused by and not addressed by template adoption.

Two stale CI filter references were also found and are unrelated to the template
boundary: `.github/workflows/reformat.yml` filters on
`.github/workflows/validate-super-linter-tool-versions.yml` and
`.github/super-linter-*.env`, neither of which exist. Not yet fixed; worth a
backlog item if noticed again.
