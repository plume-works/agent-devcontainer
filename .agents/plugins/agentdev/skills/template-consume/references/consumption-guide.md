# Template Consumption Guide

The manual guide for adopting the development environment and repository
conventions supplied by `agent-devcontainer` (published from
`plume-works/agent-devcontainer`) into another project. It covers both starting
from a complete copy (Workflow A) and adding the template surface to an
existing repository (Workflow B).

Every tracked path in the template repository belongs to one of five classes:
**Template** (retain for a normal consuming project), **Customize** (retain as
a starting point, then edit project identity or owned paths), **Optional**
(retain only when building a customized image or keeping IWE project memory),
**Publisher** (required to publish the template repository's own
image/catalog/package, not to use it — always deleted by a consumer), and
**Generated** (host, container, test, or tool state; never template source).
The steps below walk that classification path by path.

## Requirement: the finished project retains every current runtime capability

The default setup SHALL retain all runtime capabilities provided by the
template's devcontainer: the digest-pinned `agent-desktop` image;
Docker-in-Docker and Codespaces SSH; worktree-safe workspace mounts;
Xpra/VirtualGL desktop access; the Docker Desktop MCP gateway and secrets
socket integration; persistent state volumes (one shared volume holding both
agents' credentials, the rest of each agent's state scoped per devcontainer
instance); the `agentdev` catalog staged in the image and installed after
volume mounts; Codex devcontainer policy configuration; keyring and GitHub
authentication support; uv environment caching and pre-commit setup; and an
opt-in egress firewall with a project-owned allowlist.

The setup targets any project, but only supplies the tools and conventions the
template repository already carries. It does not infer a language, create
application code, choose dependencies, or invent CI for the consuming
project's product.

## Workflow A: start from a full repository copy

Use this workflow with GitHub's "Use this template" operation, a normal clone
copied into a new repository, or any equivalent complete checkout.

### 1. Establish the new repository identity

Before pruning files, record: the new repository name and owner; its default
branch; whether it will publish a custom development image; and whether agent
authentication/configuration should remain shared with other local projects.

The supplied configuration uses the literal Docker volume
`agentdev-agents-auth`, mounted at `/root/.agents-auth` with one subdirectory
per agent. Keeping it shares Claude Code's and Codex's credentials only —
nothing else — across this project, its worktrees, and other projects using the
same volume name. That is the default behavior supplied here. The rest of each
agent's state — plugins, marketplaces, sessions, `~/.claude.json`, `~/.codex`'s
logs and sqlite state — lives in the `agentdev-claude` and `agentdev-codex`
mounts, which Compose scopes per devcontainer instance because that state
records absolute workspace paths that differ between worktrees.

Replace the publisher-oriented `README.md` sections with the consuming
project's purpose, setup, tests, and ownership. Remove image/catalog
publishing instructions the project does not retain. Update the project
identity in `pyproject.toml` as well. Keep the existing `LICENSE` notice unless
the project deliberately chooses another compatible licensing arrangement.

### 2. Delete publisher-only source

Delete these paths from the copied repository:

```text
.agents/
.claude-plugin/
py_packages/
scripts/validate-super-linter-tool-versions.sh
templates/iwe/
docs/knowledge/tests/test_iwe_seed.py
```

`templates/iwe/` is the IWE seed's source. Delete it only _after_ [Optional
knowledge-base setup](#optional-knowledge-base-setup) has copied the seed to
`docs/knowledge/data/`, or when IWE is being declined; `docs/knowledge/` is
handled there too, not here. `templates/` holds nothing else, so it goes with
it.

`scripts/` holds nothing else, so it disappears with its one file; delete the
empty directory rather than leaving it behind. The same applies to the
`py_packages/` wrapper and its standalone `LICENSE` once `validate_agent_files`
is gone.

The catalog is not lost: the published image stages it at `/opt/agentdev`, and
the retained post-create scripts install it through the Claude and Codex plugin
CLIs. The validator source is also unnecessary — the image installs
`validate_agent_files` at `/usr/local/bin/validate_agent_files`, so the command
works in the devcontainer with no `uv run` prefix. Confirm it with
`command -v validate_agent_files`.

Do not delete `.claude/` or `.codex/`; those are project-facing configuration.
Do not delete the root `AGENTS.md` or `CLAUDE.md`; publisher-only instructions
were split into the source trees removed above.

### 3. Choose whether to retain custom-image publishing

For the normal consumer path, delete the optional bundle:

```text
ansible/
ansible.cfg
docker/
.dockerignore
.github/actions/docker/
.github/workflows/ci.yml
.github/workflows/delete-old-containers.yml
```

Then remove the `ci` job that calls `.github/workflows/ci.yml` from
`.github/workflows/primary-checks.yml`, and remove image/catalog publisher
paths from `.github/actions/paths-filter/action.yml`.

If the project needs image customization, retain those paths for reference and
complete the additional steps in [Optional custom-image
setup](#optional-custom-image-setup). Do not assume the retained publisher
build works after the catalog source was deleted.

### 4. Adapt the uv project

The post-create lifecycle runs `.devcontainer/scripts/uv-sync.sh`
unconditionally, so keep a valid root `pyproject.toml` even when the
application itself is not Python. It can remain a development-tool project.

In `pyproject.toml`:

1. replace the publisher project name, version, and description;
2. remove `validate_agent_files` from the development dependency list;
3. remove the editable `validate_agent_files` entry from `[tool.uv.sources]`,
   and delete the now-empty `[tool.uv.sources]` table;
4. remove `pydantic` and `python-frontmatter` — they exist for the validator
   package, not for the development environment;
5. remove `.agents/plugins/agentdev/tests` and `py_packages` from pytest
   `testpaths`, and remove `docs/knowledge/tests` too unless the project keeps
   IWE-based project memory under `docs/knowledge/` (see [Knowledge-base
   validation](#knowledge-base-validation)). If that empties the list, delete
   the whole `[tool.pytest.ini_options]` table rather than leaving
   `testpaths = []`, which makes a bare `pytest` collect nothing;
6. remove `ansible` and `ansible-lint` when the optional image bundle is not
   retained; and
7. add only the dependencies and test paths the consuming project actually
   owns.

Regenerate `uv.lock` after those edits, then run
`uv sync --all-groups --all-extras`.

Do not add the deleted local package back merely to make it importable from
the consuming repository.

### 5. Adapt pre-commit and lint configuration

Review `.pre-commit-config.yaml` hook by hook:

1. keep the general whitespace, Prettier, clang-format, ruff, ShellCheck,
   Gitleaks, Actionlint, and Zizmor hooks that match the project;
2. remove the Ansible hook when the optional image bundle is absent, and the
   clang-format and Hadolint hooks when the project has no C/C++ and no
   Dockerfile;
3. remove publisher-only catalog path patterns;
4. when agent-file validation is retained, invoke the image-provided
   `validate_agent_files` command rather than the deleted local package —
   change the hook's `entry: uv run validate_agent_files` to
   `entry: validate_agent_files`, keeping `language: system`. The hook then
   requires the development image, like the `zizmor` hook below;
5. the `zizmor` hook is `language: system` and expects `zizmor` on `PATH`,
   which the development image provides — the same arrangement as the
   `validate_agent_files` hook above;
6. remove the `plan-checkboxes`, `iwe-schema-validate`, and `iwe-normalize`
   local hooks unless the project keeps IWE-based project memory under
   `docs/knowledge/` (see [Knowledge-base
   validation](#knowledge-base-validation)); they require the `iwe` binary on
   `PATH`, which the development image also provides; and
7. update file selectors for the consuming project's source layout.

In `.ruff.toml`, remove `validate_agent_files` and `mock_catalog` from
`known-first-party`, then add the consuming project's own first-party
packages. Leaving the publisher names in place is not cosmetic — the project's
own modules get sorted as third-party imports, and the isort pass silently
enforces the wrong grouping.

Set `target-version` to the project's real floor. The supplied value is
`py312`, which is the template repository's floor rather than a default.

Review the Ansible patterns in `.prettierignore` if the optional bundle was
deleted, and add any directory holding verbatim third-party captures — a
formatter must not rewrite content whose whole point is that it matches an
upstream byte for byte.

The remaining lint configuration is still template content even when a
particular language is not yet present; unused file selectors simply match
nothing.

### 6. Review the devcontainer configuration

Keep the complete `.devcontainer/` tree, `devcontainer-compose-pins.yml`, and
`.mcp.json`. Then review these project-owned values:

1. Change `name` in `.devcontainer/devcontainer.json`.
2. Keep `workspaceFolder`, `DEV_WORKSPACE_FOLDER`, and the Compose workspace
   mount aligned. They currently derive the folder name automatically and
   normally need no edit.
3. Replace `python.testing.pytestArgs`, which currently names `py_packages`,
   with the consuming project's test roots or remove it when the project has
   no Python tests.
4. Remove Ansible-specific editor settings and extensions only when the
   project does not want the supplied optional tooling visible. Keeping them
   does not enable image building.
5. Review the extension list and chat terminal auto-approval settings for the
   project's trust model.
6. Review `.devcontainer/firewall-allowlist.txt`. Leave `ENABLE_FIREWALL=false`
   until the allowlist contains every destination the project needs, then opt
   in deliberately.
7. Keep port `14500` in `forwardPorts` when retaining Xpra.
8. Keep `devcontainer-compose-pins.yml` in the `dockerComposeFile` list; it is
   the actual digest pin.
9. Rewrite publisher-specific comments in `devcontainer-compose-pins.yml` when
   the consumer no longer builds `agent-desktop` itself; keep the pinned image
   reference and Renovate discovery behavior intact.

The lifecycle scripts are not optional fragments: post-create depends on
`uv-sync.sh` and both plugin installers; post-start depends on pre-commit,
keyring, firewall, Xpra, and Codex configuration; and `devcontainer-init.sh`
supplies the environment consumed by Compose.

### 7. Review agent configuration

Retain `.claude/` and `.codex/`, then review them as project policy:

- `.claude/settings.json` is strict JSON. Review allowed paths, Bash commands,
  web domains, MCP tools, and enabled official plugins. Remove the
  workspace-source permission for `.agents/plugins/agentdev/skills/*/scripts/*`
  after deleting `.agents/`; keep the installed-plugin cache permission when
  those scripts should remain callable.
- `.claude/settings.local.json` remains ignored for machine-specific
  permissions.
- Rewrite `.claude/README.md` so it no longer links to the deleted catalog
  publisher tree.
- `.codex/setup-codex-cloud.sh` is useful only for Codex Cloud hosts that need
  GitHub CLI; retaining it is harmless elsewhere.
- Rewrite `.codex/README.md` to describe the consumer project without links to
  deleted publisher manifests.
- Root `CLAUDE.md` continues to include root `AGENTS.md`.

The project does not need to declare `agentdev` in `.claude/settings.json`
merely to use the devcontainer. The image-staged installation is handled by
`postCreateCommand`. The retained post-start installers look for a workspace
marketplace and exit successfully when the consumer has none.

The IWE workflow skills are delivered by the installed `agentdev` catalog as
`/agentdev:iwe-*` skills, not by the copied `.claude/` directory.

### 8. Adapt GitHub Actions and Renovate

The `.github/` tree is a starting point, not a copy-and-run contract.

#### Primary checks and reformatting

In `.github/workflows/primary-checks.yml`, keep the reformat call and remove
the `ci` job unless the optional image bundle is retained. That job is the
only consumer of the `clean_build` `workflow_dispatch` input, so remove the
input with it.

In `.github/actions/paths-filter/action.yml`, the built-in filter is named
`image` and lists the publisher's build inputs. Delete the `ansible/**`,
`docker/**`, `scripts/**`, `.agents/plugins/**`, `.claude-plugin/**`, and
`py_packages/validate_agent_files/**` entries; keep `.devcontainer/**` and
`.github/actions/**` so the retained workflows still trigger.

In `.github/workflows/reformat.yml`:

1. remove catalog, validator-source, Ansible, and excluded tool-version paths
   that no longer exist;
2. remove the `scripts/validate-super-linter-tool-versions.sh` step;
3. replace the two `./.agents/plugins/agentdev/bin/super-linter-env.sh` calls;
   and
4. update formatter path filters for the consuming project.

Step 3 is the only one with real work in it. Both steps write the Super-Linter
environment into `$GITHUB_ENV`, and the helper is nothing but a sequence of
`NAME=value` lines — one set for the autofix pass, one for the check pass,
differing in the `FIX_*` values and in four `VALIDATE_*` flags for linters that
cannot autofix. Inline those two blocks into the workflow as heredocs and drop
`VALIDATE_ANSIBLE` and `ANSIBLE_DIRECTORY` if the optional bundle is gone.
Nothing else in the workflow depends on the catalog.

The template's workflow references publisher files under `.agents/` and
`scripts/`; it will fail if copied and pruned without these edits.

#### Agent-file validation

Retain agent-file validation only for agent files the consuming repository
owns. The template's `.github/workflows/validate-agent-files.yml` builds a
`uv` environment on a plain `ubuntu-latest` runner and runs the _editable,
working-tree_ validator — the same publisher-only package step 2 deletes.
Copying that workflow as-is fails once `py_packages/` is gone. Remove: the
`py_packages/validate_agent_files/tests` step; the
`.agents/plugins/agentdev/tests` step; the `--require-marketplace claude
codex` argument, which asserts publisher manifests a consumer does not have;
and path filters for deleted catalog/package source in the `paths-filter`
job's `extra-filter`.

Rebuild the remaining job to run through the digest-pinned `agent-desktop`
image instead of `uv run`, since the working-tree package that made `uv run`
necessary is gone. Give the job a `container.image` carrying the same
tag-plus-digest as `devcontainer-compose-pins.yml`, never the moving `edge`
tag — the image already carries the installed validator, so the job needs no
Python setup at all:

```yaml
jobs:
  validate-agent-files:
    runs-on: ubuntu-latest
    container:
      # Same tag-plus-digest as devcontainer-compose-pins.yml. Never the moving `edge` tag.
      image: ghcr.io/plume-works/agent-desktop:edge@sha256:<digest>
      credentials:
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    steps:
      - uses: actions/checkout@v7.0.1
        with:
          persist-credentials: false
      - run: validate_agent_files --ci .
```

`--ci` prints nothing when everything passes and the full report when
anything fails, so a green run stays quiet in the log. Add `--verbose` if the
report is wanted either way. This trades the publisher's from-source
validation (needed there because the working-tree package under
`py_packages/` is what is being edited) for validating against whatever
validator version the pinned image carries — the correct trade once that
source is deleted.

Keep the digest in step with `devcontainer-compose-pins.yml` so CI and the
devcontainer validate with the same version — Renovate already bumps that
file.

A project that ships no skills or agents of its own should delete the
workflow and the `validate-agent-files` pre-commit hook outright.

#### Knowledge-base validation

`.github/workflows/validate-knowledge-base.yml` checks an IWE knowledge graph
under `docs/knowledge/` (schema validation, normalization drift, and plan
checkbox evidence). It is part of the template repository's own
project-memory practice, not part of the devcontainer runtime. Retain it only
when the consuming project also adopts IWE-based project memory under
`docs/knowledge/` — see [Optional knowledge-base
setup](#optional-knowledge-base-setup) for the full adoption path; otherwise
delete the workflow along with the `iwe-schema-validate` and `iwe-normalize`
pre-commit hooks and the `docs/knowledge/tests` pytest path.

The workflow's seed-test step is publisher-only: it validates `templates/iwe/`,
which no consumer keeps. Drop that step along with
`docs/knowledge/tests/test_iwe_seed.py`.

#### AI responder and the review gate

One workflow file, `ai-responder.yml`, both answers `@claude` mentions and
reviews pull requests through its `claude-respond` job and contributes the
`ai-review-present` merge gate through a job of the same workflow that `needs`
the review job. Because the gate is a job of the review workflow, it is
satisfiable only while that workflow is retained: dropping the review job
leaves the required check with nothing able to satisfy it.

Two prerequisites live outside the repository and are **required**; a third
changes only how the review is attributed:

1. **Create the `CLAUDE_CODE_OAUTH_TOKEN` repository secret**, which
   `anthropics/claude-code-action` authenticates with.
2. **Create the `claude-review` environment** named by the `claude-respond`
   job's `environment:` key. A job naming an environment that does not exist
   does not run.
3. Optionally install the Claude GitHub App
   (`https://github.com/apps/claude`). The workflow passes `github_token: ${{
secrets.GITHUB_TOKEN }}` explicitly, so the responder authenticates and
   posts without it; installing the app makes comments appear as Claude
   rather than as `github-actions[bot]`. The gate's `claudeLogins` set accepts
   both, so either attribution satisfies `ai-review-present`.

The gate checks that the pull request has been reviewed, not that its current
head commit has. A push after a review does not re-open it; the author
refreshes the review when they judge it stale, by commenting `@claude
review`. This is deliberate — a review per commit would be prohibitively
expensive — so treat a copy that compares the review's `commit_id` against
the head SHA as a change in policy, not a bug fix.

Then adapt the workflows themselves:

- Change the owner gate. The preflight `if:` opens with
  `github.repository_owner == 'plume-works'`; a copy that keeps that literal
  never runs anywhere else. This gate is deliberate — it stops the workflow
  running in forks of the template.
- Keep the fork gate and the write-access gate exactly as written. They are
  the security spine: together they ensure no fork's code is checked out and
  no actor without write access can drive the responder.
- Keep the two bot gates as they are: the responder does not auto-review any
  bot author, while `ai-review-present` waives its requirement only for the
  bots named in `TRUSTED_BOT_ACTORS`. The asymmetry is deliberate. Bot-authored
  pull requests get no automatic review — that is a decision about what the
  responder is for, not a limitation. Waiving the _requirement_ is a separate
  statement of trust, so it is spelled out as a list rather than inferred from
  the author being a bot: routine dependency bumps from Renovate and
  Dependabot merge unreviewed, while a pull request from any other bot stays
  blocked until a maintainer asks for a review with an `@claude review`
  comment, which arrives under their own account.
- Review `TRUSTED_BOT_ACTORS` when adopting this workflow. It is a
  comma-separated list of bot logins, matched exactly and only for authors
  whose `user.type` is `Bot`. A consuming project running its own Renovate
  app, or another bot whose pull requests should merge without review, adds
  that login here. Widening it to every bot restores the old blanket
  exemption and hands a green required check to any app that can open a pull
  request.
- Repoint `container.image` at whichever image the consuming project uses.
- Review the `Run devcontainer lifecycle scripts` step against that image's
  own lifecycle scripts. It exists because a `container:` job runs no
  devcontainer hooks, so without it nothing installs the `agentdev` catalog
  and the responder improvises a review instead of running an
  `agentdev:pr-review`-style skill — a green required check over an
  ungrounded review.
- Do not set `track_progress` on the Claude responder review step. Although
  that input restores the action's progress comment when `prompt` is set, it
  also changes review delivery from a formal GitHub PR review into a regular
  PR comment. Preserve the review artifact, and keep job-link or status
  reporting in a separate workflow step, such as a `github-script` step that
  appends the current Actions run link to comment-triggered `@claude review`
  requests.

Two trigger behaviors are part of the workflow contract:

- The `pull_request` triggers include `synchronize`, but a push re-reviews only
  a pull request that has no accepted review yet; a push to an already-reviewed
  pull request runs the gate alone, which passes on the existing review. Adding
  a blanket review-every-push would be prohibitively expensive; re-request a
  review of a reviewed pull request by commenting `@claude review` instead.
- **Comment triggers only work once the workflow is on the default branch.**
  `issue_comment` is a repository-level event, and GitHub dispatches it using
  the workflow file on the default branch — so while the workflow exists only
  on a feature branch, `@claude review` starts nothing. The Claude app may still
  react with 👀, which makes this look like an app or authentication problem
  when it is purely a trigger-resolution one. Plan for the first end-to-end
  comment test to happen after the workflow merges. A comment mention on the
  default branch is bridged into a `workflow_dispatch` of this workflow on the
  pull request's head branch, so the review runs the branch's own file and its
  checks attach to the head commit; the `workflow_dispatch` trigger and its
  inputs are therefore part of the contract and must be retained.

A project that wants neither the responder nor the gate should delete the
workflow, and must not add `ai-review-present` to its branch protection.

#### Renovate

Retain `.github/renovate.json`, but review every rule:

1. keep Docker dependency management for `devcontainer-compose-pins.yml` so
   the development image does not become stale;
2. remove the image-publisher self-build/automerge explanation when the
   project consumes rather than publishes the image;
3. remove the publisher-only Super-Linter synchronization rule if its
   excluded script and release process are not retained; and
4. update organization, repository, and branch assumptions.

The catalog needs no Renovate rule of its own: the devcontainer reinstalls
the bundled catalog on start, so its version follows the image pin rather
than a separate one.

### 9. Set up or remove project memory

The copied repository carries the publisher's own `docs/knowledge/data/`, which
is never the consumer's memory. Follow [Optional knowledge-base
setup](#optional-knowledge-base-setup) to replace it with the seed and onboard
the consumer, or to remove IWE entirely.

### 10. Verify the copied project

Run these checks from the new repository:

1. Parse the effective Compose configuration:

   ```bash
   docker compose \
     -f .devcontainer/docker-compose.yml \
     -f devcontainer-compose-pins.yml \
     config
   ```

2. Sync the retained development-tool project:

   ```bash
   uv sync --all-groups --all-extras
   ```

3. Run the retained pre-commit hooks against the tree:

   ```bash
   uv run pre-commit run --all-files
   ```

4. Generate the host-specific Compose environment and check the derived
   workspace name:

   ```bash
   ./.devcontainer/devcontainer-init.sh && cat .devcontainer/.env
   ```

5. Create or rebuild the devcontainer and confirm the post-create and
   post-start commands finish successfully.

6. Confirm Claude and Codex list `agentdev@agent-devcontainer` after starting
   new sessions.

7. When agent files are present, run the image-provided validator against
   their actual locations.

8. Enable the firewall only after checking the project allowlist, then
   rebuild/restart and verify required network destinations still work.

9. Open the forwarded Xpra port and confirm the desktop starts.

10. Run the adapted GitHub workflows on a branch before making them required
    checks.

## Workflow B: add the template to an existing repository

This workflow avoids copying publisher source in the first place.

### 1. Copy the runtime unit

Copy all of these paths, preserving executable bits:

```text
.devcontainer/
devcontainer-compose-pins.yml
.mcp.json
```

Do not copy only the two visible devcontainer configuration files. The
lifecycle hooks, feature lock, allowlist, Compose environment setup, and
plugin installers are direct dependencies.

Then adapt the project-owned values from [step 6 of Workflow
A](#6-review-the-devcontainer-configuration), and add these to the existing
`.gitignore` before the first container start:

```text
.devcontainer/.env
.devcontainer/local.env
```

`devcontainer-init.sh` generates the first file on every start. Without the
ignore rules it lands in the next commit, carrying the host's absolute paths
with it.

### 2. Merge agent-facing configuration

Copy or merge:

```text
AGENTS.md
CLAUDE.md
.claude/
.codex/
```

When the existing repository already has agent instructions or settings,
merge the rules semantically rather than overwriting them. Keep `CLAUDE.md`
as an include of the resulting root `AGENTS.md` unless the project
deliberately maintains separate Claude instructions.

### 3. Merge the tooling baseline

Selectively copy and merge:

```text
pyproject.toml
uv.lock
.pre-commit-config.yaml
.ruff.toml
.clang-format
.ansible-lint.yml
.hadolint.yaml
.shellcheckrc
.markdownlint.yml
.prettierrc.yml
.prettierignore
zizmor.yaml
.editorconfig
.gitignore
```

Do not overwrite an existing project manifest, lockfile, ignore file, or lint
configuration. Transfer the supplied dependencies, hooks, and rules the
project wants, then regenerate the lockfile. Preserve a valid root uv project
because the supplied post-create hook runs `uv sync`.

#### Requirement: `.ruff.toml` and `pyproject.toml` never both configure ruff

Ruff resolves the first configuration file it finds and stops. Dropping
`.ruff.toml` into a repository that configures ruff under `[tool.ruff]`
disables that block entirely — line length, `target-version`, selected rules,
and all — with no warning.

**Scenario: an existing project's `[tool.ruff]` block goes silently dead**

- **WHEN** a repository with a `pyproject.toml` `[tool.ruff]` block adopts the
  template's root `.ruff.toml`
- **THEN** ruff resolves `.ruff.toml` and ignores `[tool.ruff]` entirely, with
  no warning printed.

Merge the two into `.ruff.toml` and delete the `[tool.ruff]` tables, or keep
the project's `pyproject.toml` configuration and do not copy this file.
Confirm which one won with `ruff check --show-settings <path> | head -3`,
which prints the resolved settings path.

#### Requirement: a linter hook is never added without its matching config, or vice versa

Copy only the linter configuration that has a matching hook, and vice versa.
A `.clang-format` with no C++ is inert, but a clang-format hook with no
`.clang-format` is a failing hook. The same holds for Ansible and Hadolint.

#### Requirement: formatter adoption never rewrites verbatim third-party captures

Adopting the formatters rewrites everything they can reach, including
snapshots whose value is that they are unmodified.

**Scenario: a snapshot directory with an exactness contract gets reformatted**

- **WHEN** a repository adds the template's Prettier and ruff hooks without
  first excluding directories holding verbatim third-party captures (a
  prompt snapshot with a stated exactness contract; a capture whose README
  records SHA-256 digests of its files)
- **THEN** the first hook run rewrites those files, breaking the contract.

Where the project vendors verbatim third-party files, exclude them in
`.prettierignore` and in ruff's `extend-exclude` before running the hooks for
the first time.

### 4. Merge GitHub configuration

Copy or merge the Renovate configuration, reusable actions, and the workflow
starting points under `.github/` in the template repository. Apply the same
manual CI edits from Workflow A; selecting fewer files does not remove their
internal publisher assumptions.

#### The pull request template

The template's `.github/pull_request_template.md` is a
`<!-- pr-gen-description: no-template -->` stub: `pr-gen-description` owns the PR
description structure, and the stub defers to it silently. A Workflow B
consumer, though, may already have a real `.github/pull_request_template.md`
full of its own sections. Do not copy the stub over it blindly, and do not keep
the real template as unexamined structure — evaluate it first:

1. **Map, then confirm.** Propose a section-by-section mapping of the consumer's
   existing template headings onto the sections `pr-gen-description` generates
   (its Step 7 list: Summary, What Changed, Why, Verification, Reviewer Handoff,
   Breaking Changes, Migration, Related). Present two buckets — **covered** (a
   consumer heading with a Step 7 equivalent) and **extras** (a heading with no
   equivalent) — and let the user correct the split before anything is written.
   Nothing is captured or deleted until the user confirms the buckets.

2. **Decide the extras as one batch.** Offer the extras' disposition as a single
   decision, defaulting to **capture**, with three outcomes:
   - **Capture as guidance** (recommended): write the extras into a
     consumer-owned `.github/pr-description-guidance.md` and reduce the template
     to the `<!-- pr-gen-description: no-template -->` stub.
   - **Drop all:** discard the extras and reduce the template to the stub.
   - **Keep template as-is:** leave the consumer's real template in place.
     `pr-gen-description` then reports it as not consulted on every run (its
     three-way template-reporting path), because the skill never reads structure
     out of the template itself.

3. **Capture translates headings into instructions.** When capturing, translate
   each extra _heading_ into an _instruction_ that tells `pr-gen-description` to
   emit that content — never paste the heading verbatim. A consumer
   `## Rollback plan` becomes an instruction like "always include a Rollback
   plan section describing how to revert this change." A guidance file full of
   pasted headings is a structure file by another name, which is exactly what
   Step 7 supersedes.

4. **Respect the precedence floor.** Guidance instructions take precedence over
   `pr-gen-description`'s default section generation, but they may not collapse
   or rename the Verification / Reviewer Handoff split — that tense split is what
   makes each item's state readable. Never capture an instruction that would
   merge or rename those two sections.

Leave `.github/pr-description-guidance.md` out of the marker's `tracked_paths`;
it is consumer-created state, not a template-owned upstream diff input. See
[Update Mode](../SKILL.md) for how a later PR-template change re-runs this
evaluation while preserving an existing guidance file unless the user explicitly
replaces or removes it.

If the AI responder workflows are among the files taken, their three
out-of-repository prerequisites apply here too — the Claude GitHub App
installation, the `CLAUDE_CODE_OAUTH_TOKEN` secret, and the `claude-review`
environment. Copying the files alone is not enough, and none of the three is
visible in a diff.

### 5. Set up project memory

If the project is adopting IWE-based project memory, follow [Optional
knowledge-base setup](#optional-knowledge-base-setup). An existing
`docs/knowledge/` in this repository is the consumer's own and is never
replaced — that section's step 2 covers it. Skip this step otherwise.

### 6. Verify

Run the same verification sequence from Workflow A. Pay particular attention
to merged mounts, lifecycle command keys, GitHub workflow permissions, and
duplicate pre-commit hooks.

## Optional knowledge-base setup

Follow this section whenever the consumer keeps IWE-based project memory —
`optional_bundles` includes `"knowledge-base"`. Both workflows use it; the one
step that differs is which starting state counts as "no knowledge yet", and that
is called out below.

The consumer's knowledge lives at `docs/knowledge/data/`, validated by schemas
at the consumer's repository **root** `.iwe/`. `.iwe/config.toml` sets
`[library].path = "docs/knowledge"`, and `iwe` neither searches upward for
`.iwe/` nor takes a `--root` flag — so the config stays at the root and every
`iwe` command runs with the consumer root as the working directory.

### Reusable scaffold

These paths are template-owned and copy across as-is:

```text
.iwe/
docs/knowledge/AGENTS.md
docs/knowledge/CLAUDE.md
docs/knowledge/README.md
docs/knowledge/SCHEMA.md
docs/knowledge/STRUCTURE.md
docs/knowledge/CHANGELOG.md
docs/knowledge/LICENSE.md
docs/knowledge/tests/test_plan_checkboxes.py
```

Alongside them, retain the validation the scaffold depends on:

- `.github/workflows/validate-knowledge-base.yml` (see [Knowledge-base
  validation](#knowledge-base-validation));
- the `iwe-schema-validate` and `iwe-normalize` pre-commit hooks, which need
  the `iwe` binary on PATH — the devcontainer image provides it;
- `docs/knowledge/tests` in `pyproject.toml`'s `testpaths`.

`docs/knowledge/tests/test_iwe_seed.py` is **not** in that list. It validates
the publisher's seed source under `templates/iwe/`, which a consumer does not
keep; copying it leaves a test that fails on a missing directory. Delete it if
the copy brought it along.

### Seed the consumer's data

`docs/knowledge/data/` is the one part a consumer must not receive from the
publisher — that directory is the publisher's own project memory. The starting
content comes from the seed at `templates/iwe/data/` in the agent-devcontainer
checkout at the ref being adopted, the same checkout every other template file
is read from. There is no copy of the seed inside the installed plugin, and
nothing is fetched from anywhere else.

1. **Decide whether the consumer has knowledge already.**
   - **Workflow A**: the copy carries the publisher's `docs/knowledge/data/`.
     Compare it against that same ref's `docs/knowledge/data/`. Identical means
     it is the untouched publisher copy — replace it wholesale with the seed.
     Any difference means the user has already written into it: it is consumer
     memory from here on, and step 2 applies instead.
   - **Workflow B**: an absent or empty `docs/knowledge/data/` is the only state
     that gets seeded. Anything present is consumer memory.
2. **When knowledge already exists, do not seed.** Never delete, overwrite, or
   reset a consumer's data directory. Present what is there and what the seed
   would add, and ask how to reconcile it — the same question applies to an
   existing root `.iwe/` whose schemas or `[library].path` differ from the
   template's. Proceed only on the user's answer; leaving both in place
   unmerged is a valid answer.
3. **Copy the seed** into `docs/knowledge/data/`, and copy
   `templates/iwe/LICENSE.md` to `docs/knowledge/LICENSE.md` so the notice the
   seed carries survives into the consumer.
4. **Do not retain `templates/iwe/` itself.** It is publisher source; the seed's
   destination is `docs/knowledge/data/`, and the source directory is deleted
   with the rest of the publisher-only trees.

When this skill runs from inside the template repository against a different
target directory, every path above is read from the publisher checkout and
written only under the target. The publisher's own `docs/knowledge/` and
`templates/iwe/` are never modified.

### Onboard the consumer's project memory

A freshly seeded workspace holds placeholders, not project memory. Fill it by
invoking the two onboarding skills, in order, from the **consumer** repository
root:

1. `/agentdev:iwe-setup` — reads the consumer's codebase, interviews the
   developer for what the code cannot answer, fills `data/product.md`, writes
   the first architecture doc, closes the `fill-product-doc` and
   `capture-current-architecture` backlog tasks, and deletes the `*.example.md`
   documents.
2. `/agentdev:iwe-map` — writes the per-module `data/codebase/` map that setup
   deliberately defers.
3. At the end of the consumption episode, write the adoption summary described
   below into the consumer graph. Record the adopted SHA, workflow, and settled
   choices, and point to `.agentdev-template-progress.md` as the live record.
   Do not copy the checklist into the graph.

The summary key is `data/template-adoption` and its frontmatter `type` is
`tracker`. Adoption state is a living record refreshed in place, which matches
the tracker schema; it is not a design decision or a one-time release record.
The seeded `.iwe/config.toml` binds that exact key to `[schemas.tracker]`. Setup
writes it and update mode refreshes it at the end of every episode. A consumer
without IWE skips the summary entirely.

Both skills own their own interviews and confirmation gates. This guide invokes
them; it does not answer for the user, skip a confirmation, or pre-fill an
interview.

Two states need naming explicitly:

- **A greenfield consumer** — no code to map. Run setup, which works from the
  interview alone, and report mapping as deferred until code exists. Do not run
  map against an empty tree and do not record it as done.
- **Onboarding interrupted** — a question unanswered, a confirmation not given,
  the session ended partway. Report onboarding as pending, naming what is
  outstanding; never report it complete. Resuming picks up from the consumer's
  current `docs/knowledge/data/`, which is now consumer memory: re-copying the
  seed would discard the answers already given.

Verify the result from the consumer root: `iwe schema validate` and
`iwe normalize` both clean, `data/product.md` free of `✏️` placeholders, and
no `*.example.md` documents left under `data/`. For a mapped brownfield
consumer, the installed iwe-map skill's `stale-map-docs.py` must report
`RESULT=SUCCESS`.

### When IWE is declined

Skip seeding and onboarding entirely, and remove the IWE-only artifacts a copy
may have brought in:

```text
.iwe/
docs/knowledge/
templates/iwe/
.github/workflows/validate-knowledge-base.yml
```

Also drop the `iwe-schema-validate` and `iwe-normalize` pre-commit hooks and the
`docs/knowledge/tests` entry in `testpaths` — deleting the list's last entry
means deleting the empty list. Leave `"knowledge-base"` out of
`optional_bundles`, and keep `.iwe/` and the knowledge paths out of
`tracked_paths`.

Declining IWE never authorizes deleting knowledge the consumer already had. In
Workflow B a pre-existing `docs/knowledge/` belongs to the consumer: leave it,
and remove only what this adoption would have added.

## Optional custom-image setup

Only follow this section when the published `agent-desktop` image does not
meet the project's needs.

Retain or copy:

```text
ansible/
ansible.cfg
docker/
.dockerignore
.github/actions/docker/
.github/workflows/ci.yml
.github/workflows/delete-old-containers.yml
```

Also retain the image job in `primary-checks.yml` and the corresponding image
paths in the shared filter action.

Before running the build, inspect `docker/desktop/agent-desktop.Dockerfile`.
Its Ansible invocation reads publisher source from the repository build
context twice: it enables `agentic_tools_stage_catalog` for `.agents/` and
`.claude-plugin/`, and `install_validate_agent_files` for
`py_packages/validate_agent_files/`. After the normal publisher-source
deletion, none of those trees exist and the build fails with an explicit
message from each role. Choose explicitly whether to:

- retain those publisher trees and continue building the complete image;
- alter the retained build so it stages no local catalog and builds no
  validator — set `agentic_tools_stage_catalog=false` and
  `install_validate_agent_files=false`, and drop the `AGENTDEV_PLUGIN_VERSION`
  and `VALIDATE_AGENT_FILES_VERSION` pins and labels with them; or
- construct a derivative from the published `agent-desktop` image, which
  already carries both.

Only the first option is implemented by the template repository today. Treat
the other options as project-owned image work and update the CI path
filters, image names, GHCR permissions, digest update flow, and cleanup
workflow to match it.

Do not publish under `plume-works` names from a consuming repository. Update
image names and metadata to the new repository owner, then pin the resulting
consumer image in `devcontainer-compose-pins.yml`.

## Ongoing maintenance

A manual copy or merge creates no upstream relationship by itself — that is
what this skill's update mode is for. After bootstrap: Renovate advances
external image and tool pins configured in the consumer; catalog updates
arrive through a rebuilt/pinned `agent-desktop` image; and project-specific
changes remain owned by the consuming repository. Use update mode to compare
template files against a later improvement instead of tracking scaffolding
churn by hand.

Project memory is outside that loop. `docs/knowledge/data/` is the consumer's
own from the moment it is seeded, so update mode neither compares it nor reseeds
it, and it never re-runs `/agentdev:iwe-setup` or `/agentdev:iwe-map`. Only the
reusable scaffold listed above is tracked. A marker written before that
distinction existed tracks `docs/knowledge/` wholesale; update mode narrows it
to the scaffold before diffing anything, without advancing `consumed_ref`.

The one tracked knowledge path that can affect existing documents is `.iwe/`. A
schema or config change applied from upstream can invalidate documents the
consumer already wrote, so validate the consumer's graph against the proposed
schemas — `iwe schema validate` from the consumer root — and decide with the
user before applying.
