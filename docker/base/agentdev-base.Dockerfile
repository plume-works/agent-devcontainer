# Tag-only by design. CI always overrides this with an explicit digest built in the same
# run (see .github/workflows/ci.yml); pinning a digest here would make Renovate bump a file
# under docker/**, which matches the CI image path filter and rebuilds the very image that
# produced the digest — an endless bump/rebuild loop.
ARG FROM_IMAGE=ghcr.io/plume-works/ubuntu-ansible:edge

FROM $FROM_IMAGE

# Default workspace folder. Consumers override it at runtime with
# DEV_WORKSPACE_FOLDER (set by .devcontainer/devcontainer.json), so this only
# provides the fallback baked into the image.
ARG WORKSPACE_FOLDER=/workspaces/project

# Supplied from the role default by the image workflow. Keeping the value in the
# role lets Renovate update installation and image metadata together.
ARG PLAYWRIGHT_VERSION

# Three provisioning steps, each bind-mounting only the inputs it reads at its context
# path under /provision, so a change elsewhere keeps its layer; see spec/agentdev-runtime-images.
# `cd`, not WORKDIR: /provision exists only during a step. ansible.cfg's log path is read-only.
# hadolint ignore=DL3003
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=bind,readonly,source=ansible.cfg,target=/provision/ansible.cfg \
    --mount=type=bind,readonly,source=ansible,target=/provision/ansible \
    apt-get update \
    && test -n "$PLAYWRIGHT_VERSION" \
    && cd /provision \
    && ANSIBLE_LOG_PATH='' ansible-playbook ansible/playbooks/setup-dev.yml \
      -vvv \
      --skip-tags validate_agent_files,agent_catalog \
      -e "workspace_folder=$WORKSPACE_FOLDER \
           install_xpra=true \
           install_docker=true \
           install_agentic_tools=true \
           install_playwright_browser=true \
           install_devcontainer_firewall=true \
           playwright_browser_version=$PLAYWRIGHT_VERSION \
         "

# A pin the build verifies, not one it fetches: provisioning fails unless the validator
# built from the context is exactly this version. Bump it together with
# py_packages/validate_agent_files/pyproject.toml.
ARG VALIDATE_AGENT_FILES_VERSION=1.0.1

# hadolint ignore=DL3003
RUN --mount=type=bind,readonly,source=ansible.cfg,target=/provision/ansible.cfg \
    --mount=type=bind,readonly,source=ansible,target=/provision/ansible \
    --mount=type=bind,readonly,source=py_packages/validate_agent_files,target=/provision/py_packages/validate_agent_files \
    cd /provision \
    && ANSIBLE_LOG_PATH='' ansible-playbook ansible/playbooks/setup-dev.yml \
      -vvv \
      --tags validate_agent_files \
      -e "workspace_folder=$WORKSPACE_FOLDER \
           install_validate_agent_files=true \
           validate_agent_files_source_dir=/provision/py_packages/validate_agent_files \
           validate_agent_files_version=$VALIDATE_AGENT_FILES_VERSION \
         "

# Version of the agentdev catalog staged into the image: a pin the build verifies, not
# a version it fetches. .claude-plugin/marketplace.json must declare exactly this
# version or provisioning fails. Bump both together when releasing the catalog.
ARG AGENTDEV_PLUGIN_VERSION=5.0.0

# Where the staged catalog lives. Outside $HOME on purpose: ~/.claude is commonly
# mounted as a volume, which would shadow anything placed under them.
ARG AGENTDEV_CATALOG_DIR=/opt/agentdev

# hadolint ignore=DL3003
RUN --mount=type=bind,readonly,source=ansible.cfg,target=/provision/ansible.cfg \
    --mount=type=bind,readonly,source=ansible,target=/provision/ansible \
    --mount=type=bind,readonly,source=.claude-plugin,target=/provision/.claude-plugin \
    --mount=type=bind,readonly,source=.agents/plugins,target=/provision/.agents/plugins \
    cd /provision \
    && ANSIBLE_LOG_PATH='' ansible-playbook ansible/playbooks/setup-dev.yml \
      -vvv \
      --tags agent_catalog \
      -e "workspace_folder=$WORKSPACE_FOLDER \
           install_agent_catalog=true \
           agent_catalog_source_dir=/provision \
           agent_catalog_plugin_version=$AGENTDEV_PLUGIN_VERSION \
           agent_catalog_root=$AGENTDEV_CATALOG_DIR \
         "

# Inherited by agentdev-deploy, agentdev-devcontainer, and any direct consumer. The
# catalog is staged here and installed into each agent's plugin state at build time, so
# a raw-image consumer resolves agentdev:* skills with no lifecycle hooks. This image
# carries no runtime lifecycle; agentdev-devcontainer reinstalls the catalog into the
# persistent ~/.claude volume it mounts over this install.
ENV AGENTDEV_CATALOG_DIR=$AGENTDEV_CATALOG_DIR
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
# Tools with their own root store read the system one, so an added CA reaches them all.
# Design: openspec/specs/agentdev-runtime-images.
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

LABEL org.opencontainers.image.title="agentdev-base"
LABEL org.opencontainers.image.description="Lifecycle-neutral agentdev tools, staged catalog, and default policy."
LABEL org.opencontainers.image.version.agentdev="$AGENTDEV_PLUGIN_VERSION"
LABEL org.opencontainers.image.version.playwright="$PLAYWRIGHT_VERSION"
LABEL org.opencontainers.image.version.validate-agent-files="$VALIDATE_AGENT_FILES_VERSION"

WORKDIR $WORKSPACE_FOLDER

# Default Xpra HTML5 container port.
EXPOSE 14500

ENV PATH="/root/.local/bin:$PATH"

COPY --chmod=755 docker/desktop/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
