#!/usr/bin/env bash
# Startup script for Claude Code cloud sessions on this repository.
#
# `startup.sh` (the environment setup script) registers the agentdev plugin, starts the
# Docker daemon, pre-pulls the pinned images, and brings the devcontainer up.
# `startup.sh resume` (the SessionStart hook) restores what a worker restart stops.
# Design: architecture/cloud-session-devcontainer.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT
readonly DOCKERD_LOG="/var/log/dockerd.log"
readonly DOCKER_WAIT_SECONDS=30
readonly RELAY_LOG="/var/log/agent-proxy-relay.log"
readonly RELAY_PIDFILE="/var/run/agent-proxy-relay.pid"
# Fixed, so the container's proxy address survives the session proxy changing port.
readonly RELAY_PORT=3128
# The devcontainer's nested engine claims 172.17.0.1, so the host bridge, which
# host.docker.internal resolves to, needs another subnet.
readonly DOCKER_BRIDGE_CIDR="10.213.0.1/24"
readonly DEVCONTAINER_CLI_VERSION="0.80.2"
readonly PIN_DIR="${REPO_ROOT}/.tmp/comp-pin"
readonly CLOUD_ENV="${REPO_ROOT}/.devcontainer/cloud-session.env"

log() {
    printf '\n==> %s\n' "$*"
}

die() {
    printf 'startup: error: %s\n' "$*" >&2
    exit 1
}

register_plugin() {
    log "Registering agent-devcontainer marketplace and installing agentdev"
    cd "${REPO_ROOT}"
    claude plugin marketplace add ./
    claude plugin install agentdev@agent-devcontainer
}

add_cloud_instructions() {
    mkdir -p ~/.claude
    cp -f "${REPO_ROOT}/.claude/CLAUDE.cloud.md" ~/.claude/CLAUDE.md
}

start_docker() {
    if docker info >/dev/null 2>&1; then
        return 0
    fi
    log "Starting Docker daemon (log: ${DOCKERD_LOG})"
    setsid dockerd --bip "${DOCKER_BRIDGE_CIDR}" >"${DOCKERD_LOG}" 2>&1 &

    for _ in $(seq 1 "${DOCKER_WAIT_SECONDS}"); do
        docker info >/dev/null 2>&1 && return 0
        sleep 1
    done
    die "Docker daemon not ready after ${DOCKER_WAIT_SECONDS}s; see ${DOCKERD_LOG}"
}

pull_pinned_images() {
    log "Pulling pinned devcontainer images"
    mkdir -p "${PIN_DIR}"
    cp "${REPO_ROOT}/devcontainer-compose-pins.yml" "${PIN_DIR}/docker-compose.yml"
    (cd "${PIN_DIR}" && docker compose pull)
}

install_devcontainer_cli() {
    if [[ "$(devcontainer --version 2>/dev/null || true)" == "${DEVCONTAINER_CLI_VERSION}" ]]; then
        return 0
    fi
    bun install "@devcontainers/cli@${DEVCONTAINER_CLI_VERSION}" --global
}

export_git_identity() {
    local name email
    name="$(git config --get user.name || true)"
    email="$(git config --get user.email || true)"
    [[ -n "${name}" ]] && export GIT_AUTHOR_NAME="${name}" GIT_COMMITTER_NAME="${name}"
    [[ -n "${email}" ]] && export GIT_AUTHOR_EMAIL="${email}" GIT_COMMITTER_EMAIL="${email}"
    return 0
}

# The pid file holds "<pid> <target port>". A pid counts only while its command line is
# still the relay to that port: a dead relay's pid may be a zombie or reused.
relay_pid_alive() {
    local cmdline
    cmdline="$(tr '\0' ' ' <"/proc/$1/cmdline" 2>/dev/null || true)"
    [[ "${cmdline}" == *agent-proxy-relay.py*" 127.0.0.1 $2 "* ]]
}

relay_running_for() {
    local pid target
    read -r pid target <"${RELAY_PIDFILE}" 2>/dev/null || return 1
    [[ "${target}" == "$1" ]] && relay_pid_alive "${pid}" "${target}"
}

stop_relay() {
    local pid target
    if read -r pid target <"${RELAY_PIDFILE}" 2>/dev/null && relay_pid_alive "${pid}" "${target}"; then
        kill "${pid}"
    fi
    rm -f "${RELAY_PIDFILE}"
}

# gh and git authenticate only through the session's loopback agent proxy; relay it onto
# the Docker bridge for the container, re-targeted whenever the proxy's port moves.
prepare_proxy_access() {
    local proxy="${HTTPS_PROXY:-${https_proxy:-}}" port bridge_ip relay_proxy no_proxy_list
    if [[ ! "${proxy}" =~ ^http://127\.0\.0\.1:([0-9]+)/?$ ]]; then
        stop_relay
        rm -f "${CLOUD_ENV}"
        printf 'startup: warning: no loopback HTTPS_PROXY; gh and git push stay unauthenticated\n' >&2
        return 0
    fi
    port="${BASH_REMATCH[1]}"
    if ! relay_running_for "${port}"; then
        stop_relay
        bridge_ip="$(docker network inspect bridge -f '{{(index .IPAM.Config 0).Gateway}}')"
        log "Relaying agent proxy ${bridge_ip}:${RELAY_PORT} -> 127.0.0.1:${port} (log: ${RELAY_LOG})"
        setsid python3 -I "${REPO_ROOT}/.claude/agent-proxy-relay.py" \
            "${bridge_ip}" "${RELAY_PORT}" 127.0.0.1 "${port}" >"${RELAY_LOG}" 2>&1 &
        echo "$! ${port}" >"${RELAY_PIDFILE}"
    fi
    relay_proxy="http://host.docker.internal:${RELAY_PORT}"
    no_proxy_list="${NO_PROXY:-${no_proxy:-}}"
    {
        printf 'HTTPS_PROXY=%s\nhttps_proxy=%s\n' "${relay_proxy}" "${relay_proxy}"
        printf 'NO_PROXY=%s\nno_proxy=%s\n' "${no_proxy_list}" "${no_proxy_list}"
        printf 'GH_TOKEN=%s\n' "${GH_TOKEN:-${GITHUB_TOKEN:-}}"
    } >"${CLOUD_ENV}"
}

bring_devcontainer_up() {
    log "Bringing up devcontainer"
    install_devcontainer_cli
    export_git_identity
    prepare_proxy_access
    devcontainer up --workspace-folder "${REPO_ROOT}"
}

devcontainer_running() {
    [[ -n "$(docker ps -q --filter "label=devcontainer.local_folder=${REPO_ROOT}")" ]]
}

setup() {
    time register_plugin
    add_cloud_instructions
    time start_docker
    time pull_pinned_images
    time bring_devcontainer_up
    log "Startup complete"
}

# Runs from the SessionStart hook, which the devcontainer's own sessions also load.
resume() {
    if [[ "${CLAUDE_CODE_REMOTE:-}" != true || -n "${AGENTDEV_RUNTIME_MODE:-}" ]]; then
        return 0
    fi
    {
        start_docker
        if devcontainer_running; then
            install_devcontainer_cli
            prepare_proxy_access
        else
            bring_devcontainer_up
        fi
    } >&2
}

main() {
    case "${1:-setup}" in
    setup) setup ;;
    resume) resume ;;
    *) die "usage: startup.sh [setup|resume]" ;;
    esac
}

main "$@"
