#!/usr/bin/env bash
set -euo pipefail

# Provision Codex Cloud with the same playbook and capabilities as the published
# agent-desktop image. Keep these pins and extra vars aligned with
# docker/desktop/agent-desktop.Dockerfile.

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT"

ANSIBLE_VERSION=13.4.0
AGENTDEV_PLUGIN_VERSION=3.0.0
AGENTDEV_CATALOG_DIR=/opt/agentdev
VALIDATE_AGENT_FILES_VERSION=1.0.0
WORKSPACE_FOLDER=$REPO_ROOT

log() {
    printf '\n==> %s\n' "$*"
}

have() {
    command -v "$1" >/dev/null 2>&1
}

run_sudo() {
    if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
        "$@"
    elif have sudo; then
        sudo "$@"
    else
        printf 'error: %s requires root privileges and sudo is unavailable\n' "$*" >&2
        return 1
    fi
}

install_ansible_prerequisites() {
    if ! have apt-get; then
        printf 'error: unsupported package manager; Codex Cloud provisioning requires apt-get\n' >&2
        return 1
    fi

    log "Installing Ansible bootstrap prerequisites"
    run_sudo apt-get update
    run_sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        sudo \
        locales
}

install_ansible() {
    install_ansible_prerequisites
    log "Installing the image's Ansible toolchain"
    ANSIBLE_VERSION=$ANSIBLE_VERSION docker/ansible/setup-ansible.sh
}

provision_environment() {
    log "Provisioning the agent-desktop environment"
    ansible-playbook ansible/playbooks/setup-dev.yml \
        -vvv \
        -e "workspace_folder=$WORKSPACE_FOLDER \
             install_xpra=true \
             install_docker=true \
             install_agentic_tools=true \
             install_devcontainer_firewall=true \
             install_validate_agent_files=true \
             agentic_tools_stage_catalog=true \
             agentic_tools_catalog_source_dir=$REPO_ROOT \
             agentic_tools_plugin_version=$AGENTDEV_PLUGIN_VERSION \
             agentic_tools_catalog_root=$AGENTDEV_CATALOG_DIR \
             validate_agent_files_source_dir=$REPO_ROOT/py_packages/validate_agent_files \
             validate_agent_files_version=$VALIDATE_AGENT_FILES_VERSION \
           "
}

verify_github_auth() {
    if gh auth status >/dev/null 2>&1; then
        log "GitHub CLI is authenticated"
        return 0
    fi

    if [[ -n "${GH_TOKEN:-${GITHUB_TOKEN:-}}" ]]; then
        log "GitHub token detected in environment; gh can use it for non-interactive commands"
        return 0
    fi

    log "GitHub CLI is installed but not authenticated"
    cat <<'MSG'
Set GH_TOKEN or GITHUB_TOKEN in the Codex Cloud environment, or run `gh auth login`
interactively before tasks that need GitHub API access.
MSG
}

main() {
    install_ansible
    provision_environment
    verify_github_auth

    log "Codex Cloud environment is ready"
}

main "$@"
