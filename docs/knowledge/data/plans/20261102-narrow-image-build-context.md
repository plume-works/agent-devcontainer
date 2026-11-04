---
type: plan
created: 2026-11-02
release:
- bugs/image-build-context-whole-repo
description: Give every image build step only the inputs it reads — an allow-list build context, per-input mounts, tag-selected provisioning steps, a digest-pinned Ubuntu base refreshed weekly, and a gh wrapper owned by its role — so unrelated changes reuse the cached provisioning layers.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-02T12:30:00Z
sources:
- resource: docker/base/agentdev-base.Dockerfile
- resource: docker/ansible/Dockerfile
- resource: .dockerignore
- resource: .github/workflows/ci.yml
- resource: .github/actions/docker/build-push-action/action.yml
- resource: .github/renovate.json
- resource: ansible/playbooks/setup-dev.yml
- resource: ansible/roles/agentic_tools/tasks/main.yml
- resource: ansible/roles/github_cli/tasks/main.yml
- resource: docker/bin/gh
- resource: https://github.com/plume-works/agent-devcontainer/actions/runs/41371706407
rank: 50
---

# Narrow the image build context

## Context

[Bug: Image provisioning layer is keyed on the whole
repository](../bugs/image-build-context-whole-repo.md): the `agentdev-base`
provisioning `RUN` bind-mounts the entire repository, so any change anywhere
invalidates the cached Ansible layer.

Two existing behaviors depend on the current shape and change with it:

- `main` builds from a bare `ubuntu:24.04` tag for freshness, and other refs
  warm-start from `agentdev-base:edge` ([Image
  pinning](../spec/image-pinning.md) governs the published images; the Ubuntu
  base is excluded from Renovate entirely).
- The `github_cli` role puts the opened checkout's `docker/bin` ahead of the
  image-baked `gh` wrapper on `PATH` ([gh authentication
  shim](../architecture/gh-authentication-shim.md)), which is also why the base
  build reads `docker/bin/gh` from the repository root.

## Approach

Every build step reads only what it uses, so its cache key changes only when
those inputs do.

- **Context.** `.dockerignore` becomes an allow-list: `ansible.cfg`, `ansible/`,
  `docker/`, `.claude-plugin/`, `.agents/plugins/` without plugin `tests/`,
  `py_packages/validate_agent_files/`, `py_packages/agentdev_runtime/`, and
  `.devcontainer/firewall-allowlist.txt`.

- **Provisioning steps.** The single provisioning `RUN` becomes three, each
  bind-mounting only its inputs under the same `/provision` layout and selecting
  its roles by tag:

  ```
  RUN 1  --skip-tags validate_agent_files,agent_catalog   mounts: ansible.cfg, ansible/
  RUN 2  --tags validate_agent_files                      mounts: ansible.cfg, ansible/, py_packages/validate_agent_files
  RUN 3  --tags agent_catalog                             mounts: ansible.cfg, ansible/, .claude-plugin/, .agents/plugins/
  ```

  Catalog staging and installation leave `agentic_tools` for a new
  `agent_catalog` role, so each role is atomic within its step; the
  `agentic_tools_stage_catalog` and `agentic_tools_install_catalog` switches go
  away, because a build opts in or out of the catalog by running RUN 3 or not.
  An untagged `setup-dev.yml` run still runs every role in playbook order.

- **Base freshness.** `docker/ansible/Dockerfile` pins `ubuntu:24.04` by digest
  in its `BASE_IMAGE` default, CI stops overriding it, and Renovate moves only
  that digest, weekly, with automerge. The digest bump is the scheduled clean
  rebuild; between bumps `main` and pull requests share the layer cache, so the
  warm start from `agentdev-base:edge` is removed. `clean_build` and
  `[ci:clean_build]` build without the layer cache.

- **gh wrapper.** `docker/bin/gh` becomes the `github_cli` role's `files/gh`,
  and the role stops putting the checkout's `docker/bin` on `PATH`: a checkout's
  own `gh` must never run ahead of the image's wrapper with the injected token.

- **Catalog contents.** The image stages `.claude-plugin/` and
  `.agents/plugins/` only; the `.agents/` root files are publisher-only
  contributor instructions, and plugin `tests/` are never run from the image.

- `entrypoint.sh` and the runtime `supervisord.conf` files stay narrow `COPY`s
  from `docker/`; they already have their own cache keys.

- `ansible.cfg` sets `log_path=ansible/ansible.log`, which resolves inside the
  read-only `/provision` mount; each provisioning step sets `ANSIBLE_LOG_PATH=`
  so Ansible writes no log there.

Rejected: keeping one provisioning `RUN` behind an allow-list alone. It shrinks
the context, but the most frequent image change — a catalog edit — would still
reprovision every role. Also rejected: moving `entrypoint.sh` into a role, which
would make host provisioning carry a container entrypoint it never uses.

## Implementation Steps

### Task 1: Pin the Ubuntu base by digest and drop the warm start

**Files:** Modify: `docker/ansible/Dockerfile`, `.github/workflows/ci.yml`

- [x] `docker/ansible/Dockerfile`'s `ARG BASE_IMAGE` default is
  `ubuntu:24.04@sha256:<current digest>`, and its setup-script mount names the
  context root instead of `source=..`.
  - **Evidence:** commit 5b2b4c2 pins the 24.04 index digest and mounts
    `source=.`; `pre-commit run` `hadolint-docker` passes on the file.
- [x] `ci.yml` passes no `BASE_IMAGE` build argument and no longer selects
  `agentdev-base:edge` as a base; the `Set base image refs` step and its skopeo
  lookup are gone.
  - **Evidence:** commit 5b2b4c2 removes the step and the build argument;
    `pre-commit run` `actionlint` and `zizmor` pass on `ci.yml`.

### Task 2: Let Renovate move only the Ubuntu digest, weekly

**Files:** Modify: `.github/renovate.json`

- [x] The `ubuntu` rule for `docker/ansible/Dockerfile` allows only `digest`
  updates, on a weekly schedule, with `automerge`, `automergeType: pr`, and
  `platformAutomerge`; major, minor, and patch updates stay disabled, and its
  description still says the release never moves off 24.04.
  - **Evidence:** commit dc03270 splits the rule into a disabled
    major/minor/patch rule that keeps the 24.04 description and a weekly
    automerged `digest` rule.
- [x] `renovate-config-validator` passes on the changed configuration.
  - **Evidence:** `pre-commit run renovate-config-validator` (`--strict`) passes
    on `.github/renovate.json` at commit dc03270.

### Task 3: Make `clean_build` bypass the layer cache

**Files:** Modify: `.github/actions/docker/build-push-action/action.yml`,
`.github/workflows/ci.yml`, `.github/workflows/primary-checks.yml`

- [ ] The composite build action takes a `no-cache` input that drops
  `cache-from` while still writing `cache-to`.
- [ ] A `clean_build` dispatch or a `[ci:clean_build]` marker in the commit
  message or pull request body sets it for every image build in the run, and the
  input descriptions say so.

### Task 4: Move the gh wrapper into the `github_cli` role

**Files:** Create: `ansible/roles/github_cli/files/gh` (moved from
`docker/bin/gh`); Modify: `ansible/roles/github_cli/tasks/main.yml`

- [ ] The wrapper is installed to `/usr/local/bin/gh` from the role's
  `files/gh`, and `docker/bin/` no longer exists.
- [ ] The bash and fish `github_cli_wrapper` blocks are `state: absent` with the
  same markers, so a re-provisioned host loses them, and nothing else puts a
  checkout path ahead of `/usr/local/bin/gh`.
- [ ] The wrapper's comments describe one baked copy, keeping the PATH walk and
  the `GH_WRAPPER_ACTIVE` guard as defensive behavior.

### Task 5: Split catalog staging into an `agent_catalog` role

**Files:** Create: `ansible/roles/agent_catalog/` (`defaults/main.yml`,
`tasks/main.yml`, `tasks/stage_catalog.yml`, `tasks/install_catalog.yml`,
`README.md`); Modify: `ansible/roles/agentic_tools/tasks/main.yml`,
`ansible/roles/agentic_tools/defaults/main.yml`,
`ansible/roles/agentic_tools/README.md`,
`ansible/roles/validate_agent_files/defaults/main.yml`,
`ansible/playbooks/setup-dev.yml`

- [ ] `agent_catalog` stages and installs the catalog with `agent_catalog_*`
  variables, is tagged `agent_catalog` in `setup-dev.yml` after `agentic_tools`,
  and relies on no fact another role sets except the `always`-tagged
  `extra_facts`.
- [ ] `agentic_tools` installs only the tools and `cc-filter`; its catalog
  switches and variables are gone.
- [ ] The staged trees are `.claude-plugin` and `.agents/plugins`, and no plugin
  `tests/` directory reaches the staged catalog.

### Task 6: Split the base image provisioning into per-input steps

**Files:** Modify: `docker/base/agentdev-base.Dockerfile`; Create:
`scripts/tests/test_agentdev_base_dockerfile.py`

- [ ] The provisioning runs as the three `RUN` steps in `## Approach`, each with
  one read-only bind mount per input it reads under `/provision`, tag selection
  as listed, and `ANSIBLE_LOG_PATH=` set.
- [ ] A test fails when any bind mount in `agentdev-base.Dockerfile` omits
  `source`, and when the three steps' tag selections stop covering every role in
  `setup-dev.yml` exactly once; `test_playwright_browser_provisioning.py` still
  passes.

### Task 7: Turn `.dockerignore` into an allow-list

**Files:** Modify: `.dockerignore`

- [ ] `.dockerignore` excludes everything and re-includes exactly the context
  listed in `## Approach`, keeping the cache and `*.egg-info` exclusions inside
  the re-included trees.

### Task 8: Update the consumer and role documentation

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`docs/knowledge/data/architecture/template-boundary.md`

- [ ] The consumption guide's image-build section describes opting out of the
  catalog and validator by removing their provisioning steps instead of the
  removed switches, and names the `.dockerignore` allow-list as the place a
  customized image adds inputs.
- [ ] `architecture/template-boundary` lists `.dockerignore` as an allow-list a
  custom image extends, and no longer implies `docker/bin` is needed.

### Task 9: Record the image-only gh wrapper decision

**Files:** Create: `docs/knowledge/data/architecture/gh-wrapper-image-only.md`;
Modify: `docs/knowledge/data/architecture.md`

- [ ] A new architecture document records that the image's wrapper is the only
  `gh` shim and that no checkout path precedes it, with the reason and the
  rejected live-workspace override, linking [gh authentication
  shim](../architecture/gh-authentication-shim.md) as the decision it
  supersedes; it is linked from `data/architecture.md`.

### Task 10: Observe the images build and pass acceptance from the narrowed context

**Files:** none; the pull request's CI run

- [ ] **Closed by: CI on the pull request.** Primary checks builds both
  architectures from the narrowed context, and Dev Container and deploy runtime
  acceptance and the candidate pre-commit run pass.

### Task 11: Observe a catalog-only change reuse the provisioning layers

**Files:** none; a second CI run on the pull request

- [ ] **Closed by: CI on the pull request.** After a commit that changes only a
  file under `.agents/plugins/`, the base image build log shows RUN 1 and RUN 2
  `CACHED` and RUN 3 executed, on both architectures.

## Spec changes

[Image pinning](../spec/image-pinning.md) — contract change (base image
compatibility):

``` markdown
## ADDED Requirements

### Requirement: the Ubuntu base is pinned by digest and refreshed weekly

The `ubuntu-ansible` build SHALL start from `ubuntu:24.04` pinned by digest in
`docker/ansible/Dockerfile`'s `BASE_IMAGE` default, and CI SHALL NOT override
it. Renovate SHALL update only that digest, on a weekly schedule, and SHALL
automerge the update once required checks pass; the release SHALL NOT move off
24.04.

#### Scenario: a new 24.04 digest is published

- **WHEN** Renovate's weekly run finds a newer `ubuntu:24.04` digest
- **THEN** it opens one pull request that changes only the digest, the run
  rebuilds and accepts the images from the new base, and the pull request
  automerges when its checks pass

#### Scenario: a newer Ubuntu release exists

- **WHEN** a release newer than 24.04 is published
- **THEN** Renovate proposes no update to the base

#### Scenario: a pull request builds the images

- **WHEN** a pull request's run builds `ubuntu-ansible`
- **THEN** it starts from the pinned digest, never from a published
  `agentdev-base` image
```

[agentdev runtime images](../spec/agentdev-runtime-images.md) — contract change
(build inputs and a security boundary):

``` markdown
## ADDED Requirements

### Requirement: image builds read only their declared inputs

The image build context SHALL contain only `ansible.cfg`, `ansible/`,
`docker/`, `.claude-plugin/`, `.agents/plugins/` without plugin `tests/`,
`py_packages/validate_agent_files/`, `py_packages/agentdev_runtime/`, and
`.devcontainer/firewall-allowlist.txt`. `agentdev-base` SHALL provision in
three steps — Ansible roles, the validator, the catalog — each bind-mounting
only the inputs it reads, so a change outside a step's inputs SHALL leave that
step's cached layer valid. A `clean_build` dispatch or a `[ci:clean_build]`
marker SHALL build without the layer cache.

#### Scenario: a change outside the image inputs

- **WHEN** an image build runs with the layer cache after a change only to
  files outside the build context
- **THEN** every provisioning step is reused from the cache

#### Scenario: a catalog-only change

- **WHEN** only files under `.agents/plugins/` change
- **THEN** only the catalog step runs again; the roles and validator steps are
  reused from the cache

#### Scenario: a clean build is requested

- **WHEN** a run is dispatched with `clean_build` or its commit or pull request
  body carries `[ci:clean_build]`
- **THEN** no provisioning step is reused from the layer cache

### Requirement: gh resolves to the image's wrapper

The images SHALL install the `gh` authentication wrapper at `/usr/local/bin/gh`
from the `github_cli` role, and no shell configuration the images or
`setup-dev.yml` provide SHALL put a path from the workspace checkout ahead of it
on `PATH`.

#### Scenario: a checkout carries its own gh

- **WHEN** a Dev Container opens a checkout that contains `docker/bin/gh`
- **THEN** `command -v gh` in an interactive bash or fish shell resolves to
  `/usr/local/bin/gh`

#### Scenario: a host provisioned before this change

- **WHEN** `setup-dev.yml` runs again on a host whose `~/.bashrc` or
  `config.fish` carries the `github_cli_wrapper` block
- **THEN** the block is removed
```

[Catalog lifecycle](../spec/catalog-lifecycle.md) — the staged catalog at
`$AGENTDEV_CATALOG_DIR` SHALL contain `.claude-plugin/` and `.agents/plugins/`
and SHALL NOT contain any plugin `tests/` directory or the `.agents/` root
instruction files.

## Verification

- `uv run pytest scripts/tests/test_agentdev_base_dockerfile.py scripts/tests/test_playwright_browser_provisioning.py`
  passes.
- `uv run pre-commit run --all-files` passes, including `ansible-lint`,
  `hadolint`, `actionlint`, `zizmor`, and `renovate-config-validator`.
- Locally, `docker buildx build -f docker/base/agentdev-base.Dockerfile .` twice
  with a `docs/` edit between the builds reports every provisioning step
  `CACHED` on the second build.
- `docker buildx build` of the base image, then
  `docker run --rm <image> find /opt/agentdev -name tests -type d` prints
  nothing, and `command -v gh` in `bash -ic` and `fish -c` prints
  `/usr/local/bin/gh` with a checkout carrying `docker/bin/gh` mounted at the
  workspace folder.
- An untagged `ansible-playbook ansible/playbooks/setup-dev.yml --check` lists
  every role in its original order.
- Tasks 10 and 11 close on the pull request's CI runs.

## Depends on

None. [Dev Container home volume](20261030-devcontainer-home-volume.md) depends
on this plan: its shell-setup task no longer puts the checkout's `docker/bin` on
`PATH`.

## Out of scope

- Building images once on the pull request and promoting them on `main`; the
  narrowed context is its prerequisite, and that idea stays unplanned.
- Pinning apt package versions beyond what the roles already pin; a weekly
  digest bump can expose a superseded apt pin, and that is fixed when it
  happens.
- Shortening runtime acceptance, which remains the longest part of an
  image-touching run.
- Changing what the published deploy and Dev Container images contain beyond the
  staged catalog's `tests/` and root instruction files.

## Key references

Verified anchor points (line numbers as of 2026-11-02):

- `docker/base/agentdev-base.Dockerfile:45-66` — provisioning `RUN`,
  whole-context mount at line 47, catalog and validator `-e` switches at 60-65
- `docker/base/agentdev-base.Dockerfile:91` — `COPY` of
  `docker/desktop/entrypoint.sh`
- `docker/ansible/Dockerfile:1` — `ARG BASE_IMAGE=ubuntu:24.04`
- `docker/ansible/Dockerfile:7` — `source=..` setup-script mount
- `.dockerignore:1-3` — header naming the consumed inputs
- `.github/workflows/ci.yml:11-15` — `clean_build` input
- `.github/workflows/ci.yml:87-96` — `[ci:clean_build]` marker check
- `.github/workflows/ci.yml:103-131` — `Set base image refs`, edge warm start
- `.github/workflows/ci.yml:142-154` — `Build ubuntu ansible image`,
  `BASE_IMAGE` build argument
- `.github/workflows/primary-checks.yml:15` — dispatch `clean_build` input
- `.github/actions/docker/build-push-action/action.yml:61-68` — `cache-from` and
  `cache-to`
- `.github/renovate.json:65-71` — `ubuntu` rule, `enabled: false`
- `ansible/playbooks/setup-dev.yml:33-39` — `bun_setup` tag list,
  `validate_agent_files` and `agentic_tools` roles
- `ansible/roles/agentic_tools/tasks/main.yml:41-49` — catalog stage and install
  imports
- `ansible/roles/agentic_tools/defaults/main.yml:45-84` — catalog switches,
  source dir, trees, prune names
- `ansible/roles/validate_agent_files/defaults/main.yml:9` — comment naming
  `agentic_tools_plugin_version`
- `ansible/roles/github_cli/tasks/main.yml:43-89` — wrapper copy from
  `docker/bin/gh` and the bash and fish PATH blocks
- `ansible.cfg:6` — `log_path=ansible/ansible.log`
- `scripts/tests/test_playwright_browser_provisioning.py:16` — reads
  `agentdev-base.Dockerfile`
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:1059-1072`
  — image-build opt-out through `agentic_tools_stage_catalog`
- `docs/knowledge/data/architecture/template-boundary.md:178-182` — custom image
  path set
