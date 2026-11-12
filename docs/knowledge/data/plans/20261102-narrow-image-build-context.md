---
type: plan
created: 2026-11-02
release:
- bugs/image-build-context-whole-repo
description: Give every image build step only the inputs it reads — an allow-list build context, per-input mounts, tag-selected provisioning steps, a digest-pinned Ubuntu base refreshed weekly, and a gh wrapper owned by its role — so unrelated changes reuse the cached provisioning layers.
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
stage: done
completed: 2026-11-05
released: 2.1.0
---

# Narrow the image build context

## Context

[Bug: Image provisioning layer is keyed on the whole
repository](../bugs/image-build-context-whole-repo.md): the `agentdev-base`
provisioning `RUN` bind-mounts the entire repository, so any change anywhere
invalidates the cached Ansible layer.

Two existing behaviors depend on the current shape and change with it:

- `main`, release tags, merge queues, and requested clean builds start from a
  bare `ubuntu:24.04` tag, and other refs warm-start from `agentdev-base:edge`
  when it exists ([Image pinning](../spec/image-pinning.md) governs the
  published images; the Ubuntu base is excluded from Renovate entirely).
- The `github_cli` role puts the opened checkout's `docker/bin` ahead of the
  image-baked `gh` wrapper on `PATH` ([gh authentication
  shim](../archive/1.0.0/architecture/gh-authentication-shim.md)), which is also
  why the base build reads `docker/bin/gh` from the repository root.

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

- **Stable intermediate digest.** `agentdev-base` starts from `ubuntu-ansible`
  by digest, so a per-run change to that digest misses every provisioning step's
  cache. CI builds `ubuntu-ansible` without the
  `org.opencontainers.image.created`, `.revision`, and `.version` labels, so
  unchanged inputs keep its manifest digest, and `agentdev-base` starts from
  that per-architecture manifest rather than the pushed index, whose per-run
  provenance attestation changes every run.

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

- [x] The composite build action takes a `no-cache` input that drops
  `cache-from` while still writing `cache-to`.
  - **Evidence:** commit aa9f25c adds the input and empties `cache-from` when it
    is `'true'`, leaving `cache-to` unchanged; `actionlint` and `zizmor` pass on
    the action.
- [x] A `clean_build` dispatch or a `[ci:clean_build]` marker in the commit
  message or pull request body sets it for every image build in the run, and the
  input descriptions say so.
  - **Evidence:** commit aa9f25c passes `no-cache` to all four image builds in
    `ci.yml` from `inputs.clean_build` or the marker check, and rewrites both
    `clean_build` descriptions; `actionlint` and `zizmor` pass.

### Task 4: Move the gh wrapper into the `github_cli` role

**Files:** Create: `ansible/roles/github_cli/files/gh` (moved from
`docker/bin/gh`); Modify: `ansible/roles/github_cli/tasks/main.yml`

- [x] The wrapper is installed to `/usr/local/bin/gh` from the role's
  `files/gh`, and `docker/bin/` no longer exists.
  - **Evidence:** commit c0a95df moves the file and copies `src: gh`; running
    the role from the devcontainer installs a `/usr/local/bin/gh` identical to
    `files/gh`.
- [x] The bash and fish `github_cli_wrapper` blocks are `state: absent` with the
  same markers, so a re-provisioned host loses them, and nothing else puts a
  checkout path ahead of `/usr/local/bin/gh`.
  - **Evidence:** commit c0a95df; running the role against a scratch home whose
    `.bashrc` and `config.fish` carry the block removes it from both and leaves
    the surrounding lines; no other role or runtime file prepends a checkout
    path. Commit b9fc039 removes the blocks only from configs that exist;
    running its tasks against scratch homes with no config, `.bashrc` only, and
    both removes each existing block and creates no file.
- [x] The wrapper's comments describe one baked copy, keeping the PATH walk and
  the `GH_WRAPPER_ACTIVE` guard as defensive behavior.
  - **Evidence:** commit c0a95df rewrites the two comments and leaves the PATH
    walk and guard code unchanged; `shellcheck` passes.

### Task 5: Split catalog staging into an `agent_catalog` role

**Files:** Create: `ansible/roles/agent_catalog/` (`defaults/main.yml`,
`tasks/main.yml`, `tasks/stage_catalog.yml`, `tasks/install_catalog.yml`,
`README.md`); Modify: `ansible/roles/agentic_tools/tasks/main.yml`,
`ansible/roles/agentic_tools/defaults/main.yml`,
`ansible/roles/agentic_tools/README.md`,
`ansible/roles/validate_agent_files/defaults/main.yml`,
`ansible/playbooks/setup-dev.yml`, `ansible/playbooks/group_vars/all.yml` (an
`install_agent_catalog: false` gate, like its sibling roles', so an untagged
host run still stages no catalog)

- [x] `agent_catalog` stages and installs the catalog with `agent_catalog_*`
  variables, is tagged `agent_catalog` in `setup-dev.yml` after `agentic_tools`,
  and relies on no fact another role sets except the `always`-tagged
  `extra_facts`.
  - **Evidence:** commit 27c33da; a local `agentdev-base` build at commit
    ecc66aa runs the `--tags agent_catalog` step with only `perm_probe` and
    `extra_facts` beside it, `failed=0`, and the image lists
    `agentdev@agent-devcontainer` 5.0.0 enabled from `/opt/agentdev`.
- [x] `agentic_tools` installs only the tools and `cc-filter`; its catalog
  switches and variables are gone.
  - **Evidence:** commit 27c33da; no `agentic_tools_*catalog*` or
    `agentic_tools_plugin_*` name remains under `ansible/`, and `ansible-lint`
    passes.
- [x] The staged trees are `.claude-plugin` and `.agents/plugins`, and no plugin
  `tests/` directory reaches the staged catalog.
  - **Evidence:** commit 27c33da; running `stage_catalog.yml` alone from the
    devcontainer against this checkout stages only `.claude-plugin` and
    `.agents/plugins`, `find -name tests -type d` on the staged root prints
    nothing, and a mismatched version pin still fails.

### Task 6: Split the base image provisioning into per-input steps

**Files:** Modify: `docker/base/agentdev-base.Dockerfile`

- [x] The provisioning runs as the three `RUN` steps in `## Approach`, each with
  one read-only bind mount per input it reads under `/provision`, tag selection
  as listed, and `ANSIBLE_LOG_PATH=` set.
  - **Evidence:** commit 325b78e; a local `agentdev-base` build at commit
    ecc66aa, layered on the published `agentdev-base:edge`, runs all three steps
    with `failed=0`, and rebuilding after a `docs/` edit reports all three
    `CACHED`. A from-scratch build is Task 10's CI run.
- [x] `ansible-playbook ansible/playbooks/setup-dev.yml --list-tasks`, run from
  the repository root once with each step's tag selection, lists every role of
  the playbook in exactly one step, apart from the `always`-tagged `perm_probe`
  and `extra_facts`; `test_playwright_browser_provisioning.py` still passes.
  - **Evidence:** commits 325b78e and 27c33da; at commit cb3616d, the three
    `--list-tasks` selections from the devcontainer list 16, 1, and 1 roles with
    no role in two, an untagged listing names all 18 in playbook order, and
    `pytest scripts/tests/test_playwright_browser_provisioning.py` passes 3
    tests.

### Task 7: Turn `.dockerignore` into an allow-list

**Files:** Modify: `.dockerignore`

- [x] `.dockerignore` excludes everything and re-includes exactly the context
  listed in `## Approach`, keeping the cache and `*.egg-info` exclusions inside
  the re-included trees.
  - **Evidence:** commit d21bda7; a `COPY . /ctx` probe build lists only the
    listed paths, no plugin `tests/`, no scratch or `*.egg-info`, and no
    `ansible/ansible.log`, which the allow-list also excludes.

### Task 8: Update the consumer and role documentation

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`docs/knowledge/data/archive/1.0.0/architecture/template-boundary.md`

- [x] The consumption guide's image-build section describes opting out of the
  catalog and validator by removing their provisioning steps instead of the
  removed switches, and names the `.dockerignore` allow-list as the place a
  customized image adds inputs.
  - **Evidence:** commit 43f5127;
    `validate_agent_files --recommend . --require-marketplace claude` reports 0
    errors and prettier passes.
- [x] `architecture/template-boundary` lists `.dockerignore` as an allow-list a
  custom image extends, and no longer implies `docker/bin` is needed.
  - **Evidence:** commit 43f5127 adds the allow-list paragraph and replaces the
    switch-based opt-out; the document names no `docker/bin` path, and
    `iwe schema validate` passes.

### Task 9: Record the image-only gh wrapper decision

**Files:** Create:
`docs/knowledge/data/archive/2.1.0/architecture/gh-wrapper-image-only.md`;
Modify: `docs/knowledge/data/architecture.md`

- [x] A new architecture document records that the image's wrapper is the only
  `gh` shim and that no checkout path precedes it, with the reason and the
  rejected live-workspace override, linking [gh authentication
  shim](../archive/1.0.0/architecture/gh-authentication-shim.md) as the decision
  it supersedes; it is linked from `data/architecture.md`.
  - **Evidence:** commit 52c9ed2 adds `architecture/gh-wrapper-image-only` and
    its hub link; `iwe schema validate` passes.

### Task 10: Observe the images build and pass acceptance from the narrowed context

**Files:** none; the pull request's CI run

- [x] **Closed by: CI on the pull request.** Primary checks builds both
  architectures from the narrowed context, and Dev Container and deploy runtime
  acceptance and the candidate pre-commit run pass.
  - **Evidence:** Primary checks run 41776248447 at commit 5fe2ea4 builds
    `ubuntu-ansible` from the pinned `ubuntu:24.04` digest and runs all three
    `agentdev-base` provisioning steps on amd64 and arm64; both Dev Container
    and deploy runtime acceptance jobs and the candidate pre-commit job pass.

### Task 11: Observe a catalog-only change reuse the provisioning layers

**Files:** none; a second CI run on the pull request

- [x] **Closed by: CI on the pull request.** After a commit that changes only a
  file under `.agents/plugins/`, the base image build log shows RUN 1 and RUN 2
  `CACHED` and RUN 3 executed, on both architectures. It closes on a run after
  Task 12 lands, on a pull request whose body carries no `[ci:clean_build]`.
  - **Evidence:** Primary checks run 41875687016 at commit a6b5abf, which
    changes only `.agents/plugins/agentdev/README.md`: on amd64 and arm64 the
    `agentdev-base` roles and validator steps report `CACHED` and run no Ansible
    task, and the catalog step runs its 33 tasks.

### Task 12: Keep the `ubuntu-ansible` digest stable across runs

**Files:** Create: `.github/actions/docker/build-push-action/select-labels.sh`,
`.github/actions/docker/build-push-action/platform-digest.sh`,
`scripts/tests/test_build_push_select_labels.py`,
`scripts/tests/test_build_push_platform_digest.py`; Modify:
`.github/actions/docker/build-push-action/action.yml`,
`.github/workflows/ci.yml`

- [x] The composite build action takes a `stable-labels` input that drops the
  `org.opencontainers.image.created`, `.revision`, and `.version` labels from
  the metadata it applies, and `ci.yml`'s `Build ubuntu ansible image` step sets
  it; the other image builds keep every label.
  - **Evidence:** commit 7168f5e adds the input and `select-labels.sh`, and sets
    it on `Build ubuntu ansible image` only;
    `pytest scripts/tests/test_build_push_select_labels.py` passes 4 tests, and
    `actionlint` and `zizmor --offline` pass.
- [x] Two runs of the action on unchanged `docker/ansible/` inputs push the same
  `ubuntu-ansible` per-architecture manifest digest.
  - **Evidence:** Primary checks run 41852171165 at commit e0a4a23, attempts 1
    and 2, both build `ubuntu-ansible` from cache and export the same manifest,
    `sha256:d39ddb34…` on amd64 and `sha256:4c0ea1e8…` on arm64.
- [x] The composite build action outputs a `platform-digest`, the built
  architecture's manifest inside the pushed index, and `ci.yml`'s
  `Build agentdev base image` step passes it as `FROM_IMAGE` in place of the
  index digest.
  - **Evidence:** commit b59450b adds `platform-digest.sh` and the output, and
    sets `FROM_IMAGE` from it;
    `pytest scripts/tests/test_build_push_platform_digest.py` passes 4 tests,
    and `actionlint` and `zizmor --offline` pass.

### Task 13: Check the staged catalog contents in Dev Container acceptance

**Files:** Modify: `scripts/tests/test_agentdev_devcontainer_image.py`

- [x] The direct-consumer acceptance test asserts that `$AGENTDEV_CATALOG_DIR`
  holds no `tests` directory and that its `.agents/` holds only `plugins`.
  - **Evidence:** commit cd8efbd adds both assertions; run by hand inside the
    CI-built `agentdev-devcontainer:pr-692` image, each passes, and `.agents/`
    lists only `plugins`.
- [x] Dev Container runtime acceptance passes with the new assertions on both
  architectures.
  - **Evidence:** Primary checks run 41908309456 at commit e28f58e; Dev
    Container runtime acceptance passes 10 tests on amd64 and arm64.

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
step's cached layer valid. `ubuntu-ansible` SHALL carry no per-run labels, so
unchanged inputs keep its digest. A `clean_build` dispatch or a
`[ci:clean_build]` marker SHALL build without the layer cache.

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

- `uv run pytest scripts/tests/test_playwright_browser_provisioning.py` passes.
- `ansible-playbook ansible/playbooks/setup-dev.yml --list-tasks` from the
  repository root, with `--skip-tags validate_agent_files,agent_catalog`, with
  `--tags validate_agent_files`, and with `--tags agent_catalog`, lists every
  role other than `perm_probe` and `extra_facts` under exactly one of the three.
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
- An untagged `ansible-playbook ansible/playbooks/setup-dev.yml --list-tasks`
  lists every role in its original order.
- Tasks 10 and 11 close on the pull request's CI runs.

## Depends on

None. [Dev Container home volume](20261030-devcontainer-home-volume.md) depends
on this plan: its shell-setup task (Task 3) puts no checkout path on `PATH`.

## Out of scope

- Building images once on the pull request and promoting them on `main`; the
  narrowed context is its prerequisite, and that idea stays unplanned.
- Pinning apt package versions beyond what the roles already pin; a weekly
  digest bump can expose a superseded apt pin, and that is fixed when it
  happens.
- Shortening runtime acceptance.
- A test that parses `agentdev-base.Dockerfile` for its mounts or tag
  selections: a test may not read a repository file to check its text. The local
  builds and tag listings in `## Verification`, and Tasks 10 and 11, cover that
  behavior.
- Changing what the published deploy and Dev Container images contain beyond the
  staged catalog's `tests/` and root instruction files.

## Key references

- `docker/base/agentdev-base.Dockerfile › "RUN --mount=type=cache,target=/var/cache/apt,sharing=locked"`
  — the three provisioning `RUN` steps, their mounts, and their tag selections
  (Task 6)
- `docker/base/agentdev-base.Dockerfile › "NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt"`
  — `COPY` of `docker/desktop/entrypoint.sh`
- `docker/ansible/Dockerfile › "ARG BASE_IMAGE=ubuntu:24.04"` —
  `ARG BASE_IMAGE=ubuntu:24.04`
- `docker/ansible/Dockerfile › "--mount=type=bind,readonly,source=..,target=/scripts"`
  — `source=..` setup-script mount
- `.dockerignore › "The image build context is the repository root; keep it"` —
  header naming the consumed inputs
- `.github/workflows/ci.yml#on.workflow_call.inputs.clean_build` — `clean_build`
  input
- `.github/workflows/ci.yml#jobs.build-dev-image.steps.name` —
  `[ci:clean_build]` marker check
- `.github/workflows/ci.yml#jobs.build-dev-image.steps.name` —
  `Set base image refs`, edge warm start
- `.github/workflows/ci.yml#jobs.build-dev-image.steps.name` —
  `Build ubuntu ansible image`, `BASE_IMAGE` build argument
- `.github/workflows/primary-checks.yml#on.workflow_dispatch.inputs.clean_build`
  — dispatch `clean_build` input
- `.github/actions/docker/build-push-action/action.yml#runs.steps.Build and push Docker image.env.REGISTRY_CACHE`
  — `cache-from` and `cache-to`
- `.github/actions/docker/build-push-action/action.yml#outputs.platform-digest.value`
  — `meta` step labels applied to the build (Task 12)
- `.github/workflows/ci.yml#jobs.build-dev-image.steps.name` —
  `Build ubuntu ansible image` (Task 12)
- `.github/renovate.json › "The 24.04 base's digest moves weekly, which is the images"`
  — `ubuntu` rule, `enabled: false`
- `ansible/playbooks/setup-dev.yml#Setup development environment.roles` — the
  role list and tags (Task 6), from the `always`-tagged `perm_probe` and
  `extra_facts` to the final `perm_probe`
- `ansible/roles/agentic_tools/tasks/main.yml#name` — catalog stage and install
  imports
- `ansible/roles/agentic_tools/defaults/main.yml#agentic_tools_stage_catalog` —
  catalog switches, source dir, trees, prune names
- `ansible/roles/validate_agent_files/defaults/main.yml › "agentic_tools_plugin_version."`
  — comment naming `agentic_tools_plugin_version`
- `ansible/roles/github_cli/tasks/main.yml#name` — wrapper copy from
  `docker/bin/gh` and the bash and fish PATH blocks
- `ansible.cfg › "log_path=ansible/ansible.log"` —
  `log_path=ansible/ansible.log`
- `scripts/tests/test_playwright_browser_provisioning.py::DOCKERFILE` — reads
  `agentdev-base.Dockerfile`
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#optional-custom-image-setup › "Also retain the image job in"`
  — image-build opt-out through `agentic_tools_stage_catalog`
- `docs/knowledge/data/archive/1.0.0/architecture/template-boundary.md#optional-custom-image-bundle › "Keep these paths together only when a project needs to build"`
  — custom image path set
