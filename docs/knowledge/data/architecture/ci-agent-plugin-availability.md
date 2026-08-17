---
type: architecture
description: Why a CI job that needs agentdev skills runs the devcontainer lifecycle hooks against its own checkout rather than relying on the image, and why installing the catalog at image build time was considered and rejected.
generated:
  by: claude-code/opus-5
  at: 2026-08-16T00:00:00Z
sources:
- .devcontainer/scripts/postCreateCommand.sh
- .devcontainer/scripts/postAttachCommand.sh
- .devcontainer/scripts/postStartCommand.sh
- .devcontainer/scripts/reinstall-agentdev-claude.sh
- .devcontainer/devcontainer.json
- ansible/roles/agentic_tools/README.md
---

# CI agent plugin availability

## Decision

A GitHub Actions job that needs an `agentdev:*` skill **checks out the branch
and runs the devcontainer lifecycle hooks** — postCreate, postStart, and
postAttach — before invoking the agent. The image is used as published; nothing
about it changes.

The skill the job gets is therefore the one **on the branch under review**, not
one baked into the image. A pull request that changes a skill is reviewed by the
skill as changed.

The image is **public**, so a `container:` block needs no `credentials:` and the
job needs no `packages: read` permission.

## Problem this solved

The `agent-desktop` image stages the plugin catalog at `/opt/agentdev` but does
not install it: the marketplace is not registered and the plugin cache under
`~/.claude` is empty. Installation belongs to the container's lifecycle scripts,
because `~/.claude` and `~/.codex` are commonly mounted as volumes that would
shadow anything the build wrote.

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

**Install the catalog into the image at build time.** Decided, then reversed
before implementation. It would have made skills resolve for any raw-image
consumer with no extra step, and the devcontainer path would have been
unaffected because its volumes shadow `/root/.claude` and `/root/.codex`.

Rejected once the checkout was recognized as always present: a review job clones
the repository anyway, so the catalog is already there, and using it is strictly
better because it reflects the branch under review rather than the image's
pinned `AGENTDEV_PLUGIN_VERSION`. The image change would also have made the
image ship a `~/.claude.json` it does not ship today, changing which branch of
`postCreateCommand.sh:52-59` fires on a fresh volume — a real behavior change to
the devcontainer path in exchange for a capability the checkout already
provides.

Rejected *for CI*, not discarded: it still closes a real gap for consumers that
never run the lifecycle hooks — a plain `docker run`, a Codespace. That is
planned separately in
[Install the agentdev catalog into the image](../plans/20260817-catalog-install-in-image.md),
which owns the `~/.claude.json` risk.

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

- The lifecycle scripts become a CI contract, not only a devcontainer one. A
  change that assumes an interactive editor session will break the responder.
  This is not hypothetical: the first responder run died in
  `postCreateCommand.sh` on a `chown` of `$workspace/.cache` and `/uv`, two
  paths that exist only because `devcontainer.json` mounts them. The scripts may
  no longer assume a devcontainer's *mounts* either, not just its editor.
- Skill availability is a property of the *job*, not the image — reading the
  Dockerfile will suggest otherwise, since it stages a catalog it never
  installs.
- `data/spec/catalog-lifecycle` is unaffected: nothing about staging, the
  postCreate install, or the attach-time override changes.

## Status

Decided during exploration of the AI responder workflow import, and revised once
when the checkout made the image change unnecessary. Not yet implemented.
Planned in
[AI responder workflows](../plans/20260816-ai-responder-workflows.md).
