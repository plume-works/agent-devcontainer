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

# Version of the agentdev catalog staged into the image. The catalog is staged from
# the build context, so this is a pin the build verifies rather than a version it
# fetches: .claude-plugin/marketplace.json must declare exactly this version or the
# provisioning fails. Bump both together when releasing the catalog.
ARG AGENTDEV_PLUGIN_VERSION=3.0.0

# Where the staged catalog lives. Outside $HOME on purpose: ~/.claude and ~/.codex
# are commonly mounted as volumes, which would shadow anything placed under them.
ARG AGENTDEV_CATALOG_DIR=/opt/agentdev

# Version of the validate_agent_files CLI installed into the image. Like the catalog
# version this is a pin the build verifies rather than one it fetches: the package is
# built from the build context, and provisioning fails unless the version it installs
# is exactly this. Bump it together with
# py_packages/validate_agent_files/pyproject.toml.
ARG VALIDATE_AGENT_FILES_VERSION=1.0.0

# Provision the image with Ansible.
#
# The build context is the repository root, bind-mounted read-only rather than
# COPY'd so none of the provisioning sources end up in the final layer. Omitting
# `source` on the bind mount takes the whole context.
# `cd` (not WORKDIR) into /provision: that path only exists for the duration of
# this RUN's bind mount, so WORKDIR would break later build steps. The context
# root is also where ansible.cfg lives, which is how the playbook resolves its
# inventory and roles.
# hadolint ignore=DL3003
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=bind,readonly,target=/provision \
    apt-get update \
    && cd /provision \
    && ansible-playbook ansible/playbooks/setup-dev.yml \
      -vvv \
      -e "workspace_folder=$WORKSPACE_FOLDER \
           install_xpra=true \
           install_docker=true \
           install_agentic_tools=true \
           install_devcontainer_firewall=true \
           install_validate_agent_files=true \
           agentic_tools_stage_catalog=true \
           agentic_tools_catalog_source_dir=/provision \
           agentic_tools_plugin_version=$AGENTDEV_PLUGIN_VERSION \
           agentic_tools_catalog_root=$AGENTDEV_CATALOG_DIR \
           validate_agent_files_source_dir=/provision/py_packages/validate_agent_files \
           validate_agent_files_version=$VALIDATE_AGENT_FILES_VERSION \
         "

# Inherited by any consumer of this image, including one that writes its own
# devcontainer.json. The catalog is only staged here, never installed: a container
# installs from this path through each agent's plugin CLI once the persistent
# ~/.claude and ~/.codex volumes are mounted, which is what the devcontainer
# template's postCreate hook does.
ENV AGENTDEV_CATALOG_DIR=$AGENTDEV_CATALOG_DIR

LABEL org.opencontainers.image.version.agentdev="$AGENTDEV_PLUGIN_VERSION"
LABEL org.opencontainers.image.version.validate-agent-files="$VALIDATE_AGENT_FILES_VERSION"

WORKDIR $WORKSPACE_FOLDER

# Xpra HTML5 client startup script
COPY --chmod=755 docker/desktop/start-xpra.sh /start-xpra.sh

# Xpra HTML5 base port. start-xpra.sh derives a per-devcontainer port in
# 14500-14599 from DEVCONTAINER_ID so parallel worktrees do not collide.
EXPOSE 14500

ENV PATH="/root/.local/bin:$PATH"

COPY --chmod=755 docker/desktop/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
