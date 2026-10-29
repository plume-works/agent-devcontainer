---
type: architecture
description: The publisher/template boundary — which tracked paths a consuming project keeps, customizes, or deletes, and why the boundary is drawn there.
generated:
  by: claude-code/opus-5
  at: 2026-10-25T06:31:58Z
sources:
- resource: docs/repository-structure.md (folded and removed)
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .devcontainer/scripts/postAttachCommand.sh
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md
---

# Template boundary

## Classification

Every tracked path in this repository belongs to one of these classes:

| Class     | Meaning                                                                     |
| --------- | --------------------------------------------------------------------------- |
| Template  | Retain for a normal project consuming `agent-desktop`.                      |
| Customize | Retain as a starting point, then edit project identity or owned paths.      |
| Optional  | Retain only when building a customized image or keeping project memory.     |
| Publisher | Required to publish this repository's image/catalog/package, not to use it. |
| Generated | Host, container, test, or tool state; never template source.                |

"Template" and "customize" describe file-level reuse. This repository ships no
Copier template or generator — adoption is a copy or merge driven by the
`/agentdev:template-consume` skill, whose update mode later diffs the adopted
paths against this repository from a recorded commit SHA. The requirements it
must satisfy are in [Template consumption](../spec/template-consumption.md).

## Runtime flow

``` text
ansible/ + docker/ + catalog publisher source
                    |
                    v
        ghcr.io/plume-works/agent-desktop
                    |
                    | digest pin in devcontainer-compose-pins.yml
                    v
 .devcontainer/devcontainer.json + docker-compose.yml
                    |
        initializeCommand (host, before build)
                    |
   generate .devcontainer/.env, create the shared
   agentdev-agents-auth volume, wire host MCP/secrets
                    |
          postCreateCommand (once)
                    |
   ownership fixups, CBM binary install, persist
   Claude/Codex auth into shared volumes, uv sync,
   then install the image-staged agentdev catalog
   (codex + claude) at user scope
                    |
           postStartCommand (each start)
                    |
   CBM daemon, git safe.directory, pre-commit,
   keyring, firewall, Xpra, Codex and OpenCode auth symlink repair,
   Codex and OpenCode full-access policy
                    |
          postAttachCommand (each attach)
                    |
   git SSH signing, CBM index, uv sync, then reinstall
   the workspace agentdev catalog at local scope when
   this checkout ships one
```

The image contains the environment and a read-only catalog staged at
`/opt/agentdev`. It does not contain the repository scaffolding — a consuming
project needs the template files below even though it does not need the catalog
publisher source. See [Module layout](module-layout.md) for how these pieces
compose internally.

## Default template surface

### Adoption state

The root `.agent.metadata.json` is classified per top-level key, unlike
colocated metadata files that inherit their directory's class. Its `iwe-map`
rules are Template content and travel with the directory whose sources they
govern. Its `template-consume` section is consumer-created adoption state,
written during setup and never copied from the publisher.

`.agentdev-template-progress.md` is Customize / consumer-created state. It is
tracked in git, survives template updates, and never appears in `tracked_paths`.

### Devcontainer runtime

The default devcontainer surface is the complete tracked `.devcontainer/`
directory plus two root companions — one runtime unit; copying only
`devcontainer.json` and `docker-compose.yml` leaves direct references
unresolved:

| Path                                                 | Responsibility                                                                                                                             |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `.devcontainer/devcontainer.json`                    | Dev Container entry point, features, mounts, ports, editor configuration, and lifecycle commands.                                          |
| `.devcontainer/docker-compose.yml`                   | Devcontainer service, MCP gateway, worktree mounts, and persistent Claude/Codex volumes.                                                   |
| `.devcontainer/devcontainer-init.sh`                 | Generates host-specific Compose state and creates shared agent volumes before startup.                                                     |
| `.devcontainer/devcontainer-lock.json`               | Locks the Docker-in-Docker and SSH feature digests.                                                                                        |
| `.devcontainer/firewall-allowlist.txt`               | Project-owned allowlist read when the opt-in firewall starts.                                                                              |
| `.devcontainer/scripts/postCreateCommand.sh`         | Sets up persistent Claude and Codex auth state, syncs the uv environment, and installs the image-staged catalog.                           |
| `.devcontainer/scripts/postStartCommand.sh`          | Starts the CBM daemon, sets git safe.directory, starts pre-commit hooks, keyring, firewall, and Xpra, and configures Codex and OpenCode.   |
| `.devcontainer/scripts/postAttachCommand.sh`         | Configures git SSH signing, indexes CBM, syncs uv, and reinstalls the workspace catalog on each editor attach.                             |
| `.devcontainer/scripts/uv-sync.sh`                   | Runs `uv sync` into the out-of-tree environment on the `/uv` volume ([why](uv-environment-location.md)).                                   |
| `.devcontainer/scripts/setup-pre-commit.sh`          | Trusts the checkout and installs pre-commit and pre-push hooks.                                                                            |
| `.devcontainer/scripts/setup-keyring.sh`             | Starts and persists the headless keyring used by authenticated tooling.                                                                    |
| `.devcontainer/scripts/firewall.sh`                  | Activates the image-provided egress firewall when enabled.                                                                                 |
| `.devcontainer/scripts/link-codex-auth.sh`           | Persists Codex's `auth.json` in the shared `agentdev-agents-auth` volume and symlinks it into place.                                       |
| `.devcontainer/scripts/configure-codex.py`           | Sets Codex's full-access sandbox and never-approve policy in `config.toml` on every start ([why](codex-full-access-in-devcontainer.md)).   |
| `.devcontainer/scripts/configure-opencode.py`        | Sets OpenCode's full-access action and filesystem policy in JSON or JSONC on every start ([why](opencode-full-access-in-devcontainer.md)). |
| `.devcontainer/scripts/reinstall-agentdev-claude.sh` | Installs the staged Claude plugin and overrides it with a workspace marketplace when present.                                              |
| `.devcontainer/scripts/reinstall-agentdev-codex.sh`  | Performs the equivalent Codex marketplace/plugin installation.                                                                             |
| `devcontainer-compose-pins.yml`                      | Supplies the Renovate-managed tag-plus-digest image override referenced by `devcontainer.json`.                                            |
| `.mcp.json`                                          | Points repository agents at the MCP gateway sidecar.                                                                                       |

The default runtime intentionally retains all capabilities currently supplied
here: Docker-in-Docker; Xpra and VirtualGL desktop access; the Docker Desktop
MCP gateway and secret socket integration; shared Claude and Codex
authentication/configuration volumes; image-staged `agentdev` installation; the
opt-in egress firewall; and Codespaces SSH and worktree-safe mounts.

### Agent-facing repository configuration

| Path        | Disposition | Notes                                                                                    |
| ----------- | ----------- | ---------------------------------------------------------------------------------------- |
| `AGENTS.md` | Template    | Reusable safety, workflow, language, testing, and spike guidance.                        |
| `CLAUDE.md` | Template    | Includes the root `AGENTS.md` for Claude Code.                                           |
| `.claude/`  | Customize   | Shared Claude permissions, official plugins, local ignore rules, and explanatory README. |
| `.codex/`   | Customize   | Codex Cloud bootstrap and explanation of where the shared catalog lives.                 |

Publisher-only instructions are scoped below `.agents/`, `.claude-plugin/`,
`ansible/`, and `py_packages/validate_agent_files/`. Deleting those sources also
deletes their local maintenance contract; the reusable root instructions remain.

### Project tooling

These files are template starting points. They express this repository's
development conventions, but several contain publisher-owned package names or
paths and must be reviewed in a copied project:

| Path                                 | Purpose and required review                                                                                                                                |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pyproject.toml`                     | uv-managed developer environment. Remove the local validator source and publisher test paths; rename the project and add the consumer's dependencies.      |
| `uv.lock`                            | Recreate after editing `pyproject.toml`.                                                                                                                   |
| `.pre-commit-config.yaml`            | Shared formatter/linter hooks. Remove optional-source hooks that do not match the consumer and invoke the image-provided validator directly when retained. |
| `.ruff.toml`                         | Python lint/format policy. Remove publisher-only first-party module names.                                                                                 |
| `.clang-format`                      | C/C++ formatting policy.                                                                                                                                   |
| `.ansible-lint.yml`                  | Ansible lint policy; useful with the optional image bundle and requiring comment/path review without it.                                                   |
| `.hadolint.yaml`                     | Dockerfile lint policy.                                                                                                                                    |
| `.shellcheckrc`                      | Shell lint policy.                                                                                                                                         |
| `.markdownlint.yml`                  | Markdown lint policy.                                                                                                                                      |
| `.prettierrc.yml`, `.prettierignore` | Markdown, JSON, YAML, and related formatting policy.                                                                                                       |
| `zizmor.yaml`                        | GitHub Actions security lint policy.                                                                                                                       |
| `.editorconfig`                      | Cross-editor whitespace and newline conventions.                                                                                                           |
| `.gitignore`                         | Ignores devcontainer, agent, environment, test, and tool state.                                                                                            |

`scripts/validate-super-linter-tool-versions.sh` is deliberately not in this
group. It checks this publisher repository's CI/tool pin synchronization and
stays behind.

### GitHub surface

The `.github/` tree is template-related, but it is mixed rather than copy-ready:

| Path                                             | Class     | Current coupling                                                                                                                                                                                                                                                                      |
| ------------------------------------------------ | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.github/pull_request_template.md`               | Template  | A stub pointing at the `agentdev` catalog, which owns PR structure. Copy-ready precisely because it carries none: a consumer gets a pointer to the same authority, not a format that could drift from it.                                                                             |
| `.github/pr-description-guidance.md`             | Customize | Consumer-created, absent from this publisher repository. Holds `pr-gen-description` instructions that take precedence over its default section generation; written when `template-consume` §4 captures a consumer's PR-template extras and the template is reduced to the stub above. |
| `.github/renovate.json`                          | Customize | Contains image-publisher and catalog-release assumptions in addition to the consumer image pin.                                                                                                                                                                                       |
| `.github/workflows/primary-checks.yml`           | Customize | Calls both reformatting and the optional image-building CI workflow.                                                                                                                                                                                                                  |
| `.github/workflows/reformat.yml`                 | Customize | Calls `super-linter-env.sh` from the catalog and this repository's excluded tool-version check; both must be replaced inline.                                                                                                                                                         |
| `.github/workflows/validate-agent-files.yml`     | Customize | Tests publisher sources and uses local validator packaging; consumers run validator-dependent CI through `agent-desktop` instead.                                                                                                                                                     |
| `.github/workflows/validate-knowledge-base.yml`  | Customize | Installs `iwe`, runs `iwe schema validate`/`normalize` and `docs/knowledge/tests`; retained only when the consumer keeps an IWE knowledge base, and it shares this repository's `paths-filter`.                                                                                       |
| `.github/workflows/renovate.yml`                 | Customize | Runs Renovate in `container.image`, which names this image, and needs a GitHub App whose client ID and private key are the `RENOVATE_APP_CLIENT_ID` and `RENOVATE_APP_PRIVATE_KEY` secrets. `allowedCommands` names this repository's post-upgrade script.                            |
| `.github/workflows/validate-renovate-config.yml` | Customize | Runs the validator in `container.image`, which names this image, and shares this repository's `paths-filter`.                                                                                                                                                                         |
| `.github/workflows/ai-responder.yml`             | Customize | Owner gate names `plume-works` and `container.image` names this image; needs the Claude GitHub App, the `CLAUDE_CODE_OAUTH_TOKEN` secret, and the `claude-review` environment. Also carries the `ai-review-present` merge gate, satisfiable only while the responder job is retained. |
| `.github/actions/ai-review-status/`              | Template  | Reusable acceptance test for the AI review gate; the reviewer logins it accepts are the policy in `spec/ai-review-gate`.                                                                                                                                                              |
| `.github/actions/log-debug-stats/`               | Template  | Reusable GitHub API diagnostic action.                                                                                                                                                                                                                                                |
| `.github/actions/setup-python-venv/`             | Customize | Reusable for uv projects after the consumer lockfile/project metadata is established.                                                                                                                                                                                                 |
| `.github/actions/paths-filter/`                  | Customize | Its current filters name image and catalog publisher paths.                                                                                                                                                                                                                           |
| `.github/workflows/ci.yml`                       | Optional  | Builds, publishes, merges, and smoke-tests the two container images.                                                                                                                                                                                                                  |
| `.github/workflows/delete-old-containers.yml`    | Optional  | Deletes old GHCR versions for repositories that publish custom images.                                                                                                                                                                                                                |
| `.github/actions/docker/`                        | Optional  | Composite actions used by the image publishing workflow.                                                                                                                                                                                                                              |

The existing workflows are evidence of the supplied CI design; they are not
claimed to run unchanged after publisher source is removed.

### Repository presentation

`README.md` and `LICENSE` are template content. The root README and the READMEs
under `.claude/` and `.codex/` must be rewritten to remove publisher-only
descriptions and links. The MIT license and its existing notice remain unless
the project deliberately adopts a compatible alternative.

## Optional custom-image bundle

Keep these paths together only when a project needs to build a customized
development image: `ansible/`, `ansible.cfg`, `docker/`, `.dockerignore`,
`.github/workflows/ci.yml`, `.github/workflows/delete-old-containers.yml`,
`.github/actions/docker/`, and the matching image paths and job invocation in
the shared GitHub files.

This is the source used to publish `agent-desktop`, not a generic
derivative-image template. The current desktop Dockerfile reads publisher-only
source from the build context twice: it sets `agentic_tools_stage_catalog=true`
for `.claude-plugin/` plus `.agents/`, and `install_validate_agent_files=true`
for `py_packages/validate_agent_files/`. A full template copy deletes both, so
the optional image bundle cannot build unchanged afterward. A project retaining
the bundle must explicitly choose one of these manual directions:

1. retain the publisher source too and keep building this repository's full
   image;
2. stop staging a local catalog and stop building the validator — set
   `agentic_tools_stage_catalog=false` and `install_validate_agent_files=false`,
   and adapt the image build accordingly; or
3. create a derivative build based on the published `agent-desktop` image.

The repository currently implements the first direction. The other two are
customization work, not hidden template behavior.

## Optional knowledge-base bundle

Keep these paths together only when a project adopts IWE project memory:
`.iwe/`, the supporting documents under `docs/knowledge/` (`AGENTS.md`,
`CLAUDE.md`, `README.md`, `SCHEMA.md`, `STRUCTURE.md`, `CHANGELOG.md`),
`docs/knowledge/tests/test_plan_checkboxes.py`,
`.github/workflows/validate-knowledge-base.yml`, the `iwe-schema-validate` and
`iwe-normalize` pre-commit hooks, and the `docs/knowledge/tests` entry in
`pyproject.toml`'s `testpaths`. Those are the paths a consumer tracks; they are
what update mode may legitimately diff.

`docs/knowledge/data/` is **not** among them. That directory is this
repository's own project memory in the publisher and the consumer's own project
memory in a consumer — the same path holding different owners' content. Update
mode must never compare it, because there is no version of that diff that is
meaningful: every difference is either the publisher's history or the
consumer's, and applying either direction destroys memory.

The consumer's starting workspace comes from the installed agentdev catalog, not
from the template checkout: template consumption invokes
`/agentdev:iwe-bootstrap`, which copies its own scaffold into the consumer root
and refuses whenever `.iwe/` or `docs/knowledge/` already exists.

| Scaffold source (`skills/iwe-bootstrap/assets/`) | Destination                 | Owner after initialization                       |
| ------------------------------------------------ | --------------------------- | ------------------------------------------------ |
| `.iwe/`                                          | `.iwe/`                     | Consumer; tracked against the template's `.iwe/` |
| `docs/knowledge/` support documents              | `docs/knowledge/`           | Consumer; tracked against the template's copies  |
| `docs/knowledge/data/`                           | `docs/knowledge/data/`      | Consumer                                         |
| `docs/knowledge/LICENSE.md`                      | `docs/knowledge/LICENSE.md` | Consumer                                         |

The scaffold is initialization-only. It is catalog content, never a template
path, so it never appears in `tracked_paths`, and a catalog update that changes
it never reaches an initialized consumer. Bootstrap installs no tests, CI
workflows, or hooks; the remaining knowledge-base paths above come from the
template checkout as usual.

## Optional Expo profile

An Expo consumer applies the template-consume guide's Optional Expo setup. The
profile adds no paths and no `tracked_paths`: it edits Template and Customize
files the consumer already has — `.devcontainer/firewall-allowlist.txt`,
`.devcontainer/devcontainer.json`, `.gitignore`, `.claude/settings.json`, the
root `AGENTS.md` — and the consumer-owned `eas.json`. The marker records it as
`"expo"` in `optional_bundles`, which is how update mode knows to re-check the
`eas.json` bun pin when the image changes and to reconcile the profile's edits
against the guide on every update, since no `tracked_paths` diff surfaces them.

In `.devcontainer/devcontainer.json` the profile lists the [VS Code Expo
bridge](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/architecture/vscode-expo-bridge.md)
extension pack `plume-works.vscode-expo-bridge` in
`customizations.vscode.extensions`, adds `8081` to `forwardPorts` for Metro, and
gives that port a `portsAttributes` entry with `"onAutoForward": "silent"`, so
VS Code's auto-forward notification does not cover the bridge's own
notifications. The listed pack installs the workspace extension in the
container; the host extension is installed on the Mac by one click on its
**Install Locally**, once per Mac. Its `AGENTS.md` rule tells agents to build
iOS through `eas-host` when `eas-host status` succeeds and on EAS cloud
otherwise. Setup grants the bridge no trust: it writes no trust or security
setting into any consumer file, and a workspace is trusted only on the Mac.
`EXPO_TOKEN` needs no profile edit: the template devcontainer passes it from the
host for every consumer, empty when the host does not set it.

The profile merges the Expo template's `AGENTS.md` into the root `AGENTS.md`,
which therefore stops matching upstream: the consumer's progress document
records it as customized, and update mode merges it by hand.

## Publisher-only source

These paths stay in this repository but are deleted from a normal full template
copy:

| Path                                             | Responsibility                                                                                                                                 |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `.agents/`                                       | Canonical `agentdev` plugin source: agents, skills (the `iwe-bootstrap` scaffold among them), hooks, helper commands, and plugin-script tests. |
| `.claude-plugin/`                                | Claude marketplace manifest for the catalog.                                                                                                   |
| `py_packages/validate_agent_files/`              | Standalone validator package source and package tests.                                                                                         |
| `scripts/validate-super-linter-tool-versions.sh` | Publisher CI consistency check.                                                                                                                |
| `docs/knowledge/tests/test_iwe_seed.py`          | Validates the `iwe-bootstrap` scaffold in the catalog source, which no consumer keeps.                                                         |

After deleting `py_packages/validate_agent_files/`, remove the now-empty
`py_packages/` wrapper and its standalone `LICENSE` as well. `scripts/` holds
nothing but the tool-version check, so it disappears with it.

`validate_agent_files` itself remains available from the `agent-desktop` image,
which installs it at `/usr/local/bin/validate_agent_files` as an isolated `uv`
tool (`ansible/roles/validate_agent_files/`). It can still be used locally or by
CI that executes through the image, with no `uv run` prefix and no copy of the
package source. See [Validator image install](validator-image-install.md) for
how that install works and the decisions behind it.

## Generated and local-only state

The following observed paths are not repository structure and must never be
treated as template input: `.devcontainer/.env` (generated by
`devcontainer-init.sh`); `.devcontainer/local.env` (ignored host-specific
overrides); `.claude/settings.local.json` (ignored machine-specific Claude
permissions); `.tmp/` (required scratch root for agents and audits); `.venv`,
`.cache/`, `.pytest_cache/`, `.coverage`, and tool caches; `.ansible/`,
`ansible/.ansible/`, and `ansible/ansible.log`; and `log/` and Super-Linter
output.

## Why the boundary is drawn here

The repository history explains the boundary's evolution:

- `c1dce21` extracted a project-agnostic image publisher and described
  `.devcontainer/` as ready to copy.
- `efc55c1` added digest pinning and Renovate.
- `a07718f` moved the Claude catalog into the `agentdev` plugin.
- `d2270b6` packaged the same tree for Codex.
- `6cb9487` moved lifecycle helpers from root `scripts/` into
  `.devcontainer/scripts/`.
- `07e125b` replaced build-time plugin seeding with a staged catalog plus
  lifecycle installation for both agents.

An earlier estimate of the publisher/template boundary (a four-file catalog
split) predates this final lifecycle layout — the live dependency chain now
makes the complete `.devcontainer/` tree, `devcontainer-compose-pins.yml`, and
related configuration part of the manual template inventory.
