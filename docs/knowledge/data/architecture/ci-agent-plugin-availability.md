---
type: architecture
description: Why the agent-desktop image installs the agentdev catalog at build time so raw-image consumers such as CI resolve its skills, why the devcontainer path is nearly unaffected because its volumes shadow the image's plugin state — with ~/.claude.json the one shared surface — and why the image being public means container jobs need no registry credentials.
generated:
  by: claude-code/opus-5
  at: 2026-08-16T00:00:00Z
sources:
- ansible/roles/agentic_tools/README.md
- ansible/roles/agentic_tools/defaults/main.yml
- .devcontainer/scripts/reinstall-agentdev-claude.sh
- docker/desktop/agent-desktop.Dockerfile
---

# CI agent plugin availability

## Decision

The `agent-desktop` image **installs** the `agentdev` catalog at build time, at
user scope, in addition to staging it at `/opt/agentdev`. Any direct consumer of
the image — a GitHub Actions `container:` job, a plain `docker run` — therefore
resolves `agentdev:*` skills with no extra step.

Devcontainers are essentially unaffected: their `agentdev-claude` /
`agentdev-codex` volumes mount over `/root/.claude` and `/root/.codex`, so the
build-time install is not part of that path, and `postCreate` installs into the
volumes exactly as it does today. The single shared surface is `~/.claude.json`,
which cannot be volume-backed — see *The one place the paths meet*.

The image is **public**, so a `container:` block needs no `credentials:` and the
job needs no `packages: read` permission.

## Problem this solved

The `agent-desktop` image stages the plugin catalog at `/opt/agentdev`
(`agentic_tools_catalog_root`), which reads naturally as "the plugin is in the
image". It is — on disk. But it is not *installed*: the marketplace is not
registered and the plugin cache under `~/.claude` is empty.

`agentic_tools` originally staged without installing, and
[the role's README](../../../../ansible/roles/agentic_tools/README.md) justified
that by volume semantics: Docker copies image content into a named volume only
when that volume is empty, so a build-time `claude plugin install` would be
correct on a clean machine and silently inert for every container whose
`~/.claude` volume already exists. Installation was therefore deferred to
`.devcontainer/scripts/reinstall-agentdev-claude.sh`, run from `postCreate`.

**A GitHub Actions `container:` job runs no lifecycle hooks.** It starts the
image and runs steps. So the deferral left CI with a staged-but-uninstalled
catalog, and any skill reference resolved to nothing.

The failure mode is quiet, which is what makes it worth recording: an agent
asked to use a skill that does not resolve does not necessarily fail — it
improvises. For a PR-review responder gated by a required check, that produces a
green gate over an ungrounded review, which is worse than a red one.

## Why the original rationale did not hold

The README's reason was sound about *what* happens and wrong about *what
follows*. It treated one consumer — the devcontainer — as the only one. There
are two, and their plugin *directories* do not overlap:

|                    | reads plugin state from      | build-time install |
| ------------------ | ---------------------------- | ------------------ |
| raw image consumer | `/root/.claude` in the image | is what it uses    |
| devcontainer       | the `agentdev-claude` volume | never visible      |

A devcontainer mounts its volumes over `/root/.claude` and `/root/.codex` before
anything reads them, so a build-time install is not shadowed *and then repaired*
— it is simply absent from that path. `postCreate` installs into the volumes,
which is what it does today and what it would do whether or not the image
carried an install.

So the build-time install serves only the consumer that has no lifecycle hook to
install for it, which is precisely the gap this document opens with.

### The one place the paths meet

`~/.claude.json` is the exception. Docker volumes are always directory-backed,
so that file cannot be volume-mounted; `postCreateCommand.sh:52-59` persists it
*inside* the `agentdev-claude` volume and symlinks `/root/.claude.json` to it:

``` bash
if [[ -f /root/.claude.json && ! -L /root/.claude.json ]]; then
    mv /root/.claude.json "$claude_json_target"
elif [[ ! -e "$claude_json_target" ]]; then
    echo '{}' >"$claude_json_target"
fi
```

Today the image ships no `~/.claude.json`, so a fresh volume takes the `elif`
and starts from `{}`. Once the image installs plugins at build time it *will*
ship that file, so the `mv` branch fires instead and the volume is seeded from
the image. On an existing volume `/root/.claude.json` is already a symlink, both
branches skip, and the image's copy is correctly ignored.

Two consequences worth holding: the fresh-volume case changes behavior even
though nothing about the devcontainer scripts changed, and
`codebase-memory-mcp-install.sh` runs *before* the symlink is established
(`postCreateCommand.sh:40`, deliberately) against a `~/.claude.json` that is now
a real file rather than absent. Neither is known to be broken; both are why the
plan verifies the fresh and existing-volume cases separately instead of
asserting the paths never interact.

## Alternatives considered

**Keep staging-only and install from an explicit workflow step.** The first
version of this decision. Rejected once the rationale above was checked: it
pushes the same three lines into every CI job and every other direct consumer,
and leaves the image carrying a catalog that looks installed but is not — the
quiet failure mode this document exists to prevent.

**Skip the container and run the responder on a bare runner.** Viable, and
simpler, but it gives up the project toolchain (`uv`, `bun`, the linters) that
makes a review grounded.

**Vendor a repository-local `.claude/skills/pr-review/`.** Removes the
dependency on the plugin entirely, since a repo-local skill is present after
checkout. Rejected as duplication: it would fork from the catalog's copy and
drift.

## Resolved by inspection

- **Install user and runtime user agree.** `user_home` resolves from
  `ansible_facts['env'].HOME` (`ansible/roles/extra_facts/tasks/main.yml:16`),
  which is `/root`; the Dockerfile declares no `USER`, and the devcontainer
  mounts its `agentdev-claude` volume at `/root/.claude`. The install runs as
  the same user every consumer runs as, matching the rest of the Ansible
  provisioning.
- **No auth or network is needed.** The marketplace is added from a local path —
  the staged catalog already in the image — so the build stays offline, as the
  staging design intends.
- **No install-over-install case exists for the directories.** Because the
  volumes shadow `/root/.claude` and `/root/.codex` entirely, the build-time
  install and `postCreate`'s install never write to the same directory state.
  The exception is `~/.claude.json`, which is not volume-backed — see *The one
  place the paths meet* above. That file is the only shared surface, and it is
  the reason the fresh-volume and existing-volume cases are verified separately.

## Consequences

- `agentic_tools` no longer only stages. Its README's rationale is superseded by
  this document and must be rewritten alongside the change.
- Skill availability becomes a property of the image, which is what reading the
  Dockerfile already suggests.
- Because the catalog is staged read-only from the build context, the plugin
  version a consumer gets is the one pinned by `AGENTDEV_PLUGIN_VERSION` in the
  image it runs — updating it means rebuilding the image.
- The responder workflow cannot work until this image change ships and `:edge`
  is rebuilt, which orders the work.

## Status

Decided during exploration of the AI responder workflow import. Not yet
implemented — neither the image install nor the workflows exist. Planned in
[AI responder workflows](../plans/20260816-ai-responder-workflows.md), which
also carries the Codex-side decision: the build-time install covers both agents,
not Claude alone.
