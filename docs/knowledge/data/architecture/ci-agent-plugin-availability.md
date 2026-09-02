---
type: architecture
description: Why a CI job that needs agentdev skills runs the devcontainer lifecycle hooks against its own checkout even though raw-image consumers get a build-time catalog install.
generated:
  by: codex/gpt-5
  at: 2026-09-02T06:07:09Z
sources:
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postAttachCommand.sh
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .devcontainer/scripts/reinstall-agentdev-claude.sh
- resource: .devcontainer/devcontainer.json
- resource: ansible/roles/agentic_tools/README.md
---

# CI agent plugin availability

## Decision

A GitHub Actions job that needs an `agentdev:*` skill **checks out the branch
and runs the devcontainer lifecycle hooks** — postCreate, postStart, and
postAttach — before invoking the agent. The job uses the image as published and
does not rely on the image's baked plugin state.

The skill the job gets is therefore the one **on the branch under review**, not
one baked into the image. A pull request that changes a skill is reviewed by the
skill as changed.

The image is **public**, so a `container:` block needs no `credentials:` and the
job needs no `packages: read` permission.

## Problem this solved

At the time this CI decision was made, the `agent-desktop` image staged the
plugin catalog at `/opt/agentdev` but did not install it: the marketplace was
not registered and the plugin cache under `~/.claude` was empty. Installation
into a devcontainer still belongs to the container's lifecycle scripts, because
`~/.claude` and `~/.codex` are commonly mounted as volumes that shadow anything
the build wrote.

**A GitHub Actions `container:` job runs no lifecycle hooks.** It starts the
image and runs steps. So a job that names a skill gets nothing, and the failure
is quiet: an agent asked to use a skill that does not resolve does not
necessarily fail — it improvises. For a PR-review responder gated by a required
check, that produces a green gate over an ungrounded review, which is worse than
a red one.

## Which hooks, and why all three

The naming does not match the responsibilities, so the split is worth stating.
The checkout-scoped catalog install and the CBM *index* both live in
**postAttach**; postStart only *starts* CBM, and postCreate is what *installs*
it in the first place.

| hook       | what a review job needs from it                                         |
| ---------- | ----------------------------------------------------------------------- |
| postCreate | **CBM install**, auth symlinks, `uv-sync`, image-scoped catalog install |
| postStart  | `codebase-memory-mcp-start.sh` — starts CBM, does not index             |
| postAttach | **CBM index**, `uv-sync`, **catalog from this checkout**                |

CBM is spread across all three hooks and no one of them is sufficient:
`codebase-memory-mcp-install.sh` wires the binary into agent config from
**postCreate** (`postCreateCommand.sh:52`), postStart starts it, postAttach
indexes. Dropping postCreate to slim a CI job would leave the responder with no
CBM wiring at all.

Running only postCreate and postStart would leave the responder with the image's
catalog and an unindexed CBM — the two things that make the review grounded are
both in postAttach (`postAttachCommand.sh:8` and `:14-15`).

## What a `container:` job must supply itself

The hooks depend on `devcontainer.json` — its `containerEnv` and its `mounts` —
not only on the image, and a `container:` job applies neither. The responder job
supplies the load-bearing hook environment explicitly:

| what                                  | why                                                                              |
| ------------------------------------- | -------------------------------------------------------------------------------- |
| `DEV_WORKSPACE_FOLDER`                | workspace root for every script                                                  |
| `CBM_CACHE_DIR`                       | `codebase-memory-mcp-install.sh:22` dereferences it under `set -u`               |
| `UV_PROJECT_ENVIRONMENT`              | see below — unset is silent, not fatal                                           |
| `mkdir -p /root/.claude /root/.codex` | `postCreateCommand.sh:63-69` writes `claude.json` where a volume normally mounts |

The remaining devcontainer `containerEnv` variables are not required here:
`ENABLE_FIREWALL` is already inert by default; `UV_CACHE_DIR` and
`UV_PYTHON_INSTALL_DIR` fall back to uv defaults; and `DISPLAY`, `DOCKER_HOST`,
`DEVCONTAINER_ID`, and `CLAUDE_SECURESTORAGE_CONFIG_DIR` are not exercised by
the hooks. No volumes are required; plain directories suffice.

`UV_PROJECT_ENVIRONMENT` deserves the emphasis. Unset, `uv sync` does not fail —
it creates `.venv` **inside the checkout** and the job stays green. A review job
would report success while having written into the very tree it is reviewing.
That failure mode is invisible to CI, so the local reproducer checks for this
side effect explicitly.

Mounts have the same shape: `postCreateCommand.sh` chowns `$workspace/.cache`
and `/uv`, which exist only because `devcontainer.json` mounts them, so that
chown skips targets that are absent rather than aborting the script.

## What a review job should skip

Two postStart steps are pure cost in CI and are guarded by `AGENTDEV_*`
variables that default to today's behavior:

- `setup-pre-commit.sh` runs `pre-commit install --install-hooks`, which eagerly
  builds a virtualenv for every hook in the repository. That is minutes of work
  for hooks a review job never fires.
- `/start-xpra.sh --background` starts a remote desktop nothing will connect to.

`setup-keyring.sh` needs no guard: it already exits cleanly when the keyring
stack is absent (`setup-keyring.sh:99-107`).

`git config --global --add safe.directory` is *not* skippable — a CI checkout is
owned by a different uid — which is why it moves out of `setup-pre-commit.sh`
into its own script rather than living behind the pre-commit guard.

## Alternatives considered

**Rely on the image's build-time catalog install for CI.** Rejected for review
jobs. A review job clones the repository anyway, so the catalog is already
there, and using it is strictly better because it reflects the branch under
review rather than the image's pinned `AGENTDEV_PLUGIN_VERSION`.

The image now installs the catalog at build time for raw-image consumers that
never run the lifecycle hooks — a plain `docker run`, a Codespace, or a
containerized job that only needs the published catalog. That path is specified
in [Catalog lifecycle](../spec/catalog-lifecycle.md) and recorded by
[Build-time agentdev catalog install](../features/build-time-agentdev-catalog-install.md).

**Install from an explicit workflow step rather than the lifecycle hooks.**
Rejected: it duplicates logic the hooks already own and drifts from them. The
hooks are the tested path.

**Skip the container and run the responder on a bare runner.** Viable, and
simpler, but it gives up the project toolchain (`uv`, `bun`, the linters) and
CBM that make a review grounded.

**Vendor a repository-local `.claude/skills/pr-review/`.** Removes the plugin
dependency entirely, but forks from the catalog's copy and drifts.

## Cost of running the hooks

Measured rather than assumed, because the intuition here is wrong in both
directions:

- **A cold CBM index is ~3.5s** in this repository. It runs from postAttach on
  every review job and is not worth optimizing or caching.
- **`pre-commit install --install-hooks` is minutes.** It eagerly builds a
  virtualenv for every hook in the repository — the single expensive step in the
  whole lifecycle, and the one a review job least needs, since it never commits.

The expensive step is the one that looks incidental, which is why the guard
exists and why upstream's 30-minute job timeout carries over unchanged.

## Consequences

- The lifecycle scripts become a CI contract, not only a devcontainer one. They
  must tolerate missing devcontainer mounts in `container:` jobs, not just the
  absence of an interactive editor session.
- Branch-local skill availability is a property of the *job*, not only the
  image. The image's build-time install supplies the published catalog, while
  the lifecycle hook install supplies the checkout's catalog.
- [Catalog lifecycle](../spec/catalog-lifecycle.md) describes both install
  paths: the image-build install for raw-image consumers and the lifecycle
  install for mounted devcontainer volumes.

## Status

Implemented for CI by
[AI responder workflows](../plans/20260816-ai-responder-workflows.md). The
separate raw-image catalog install is implemented by
[Install the agentdev catalog into the image](../plans/20260817-catalog-install-in-image.md).
