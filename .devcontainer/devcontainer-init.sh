#!/usr/bin/env bash
set -euo pipefail

script_dir=$(dirname "${BASH_SOURCE[0]}")

# GitHub Codespaces runs initializeCommand via `/bin/sh -c` with no HOME in the
# environment. The host MCP/secrets integration below is a local Docker Desktop
# convenience keyed off $HOME; under `set -u` an unbound HOME aborts the whole
# init (and thus the container build). Default it to empty so those host-path
# `-d`/`-S` probes simply fall through to their stub branches in Codespaces.
: "${HOME:=}"

if [[ -f "$script_dir/local.env" ]]; then
    cp -f "$script_dir/local.env" "$script_dir/.env"
else
    rm -f "$script_dir/.env"
    touch "$script_dir/.env"
fi

# This named volume intentionally outlives a single Compose project so agent
# authentication can be shared by every local worktree. Declare it as external
# in Compose to avoid ownership warnings, and create it here so a first-ever
# devcontainer startup still has everything it needs.
docker volume create agentdev-agents-auth >/dev/null

gitdir=$(realpath "$(git rev-parse --git-common-dir)")
echo "GIT_REPO=$gitdir" >> "$script_dir/.env"

LOCAL_WORKSPACE_FOLDER=$(realpath "$script_dir/..")
# Remote Control names its environment after this hostname; spec: claude-remote-control.
# Inline because a migrated consumer keeps no .devcontainer/scripts/.
host="${HOSTNAME:-$(hostname)}"
host="${host%%.*}"
stem="$(basename "$LOCAL_WORKSPACE_FOLDER")"
if [[ -n "${CODER_WORKSPACE_NAME:-}" ]]; then
    container_hostname="coder-$CODER_WORKSPACE_NAME"
elif [[ -n "${VSCODE_PID:-}" || -n "${VSCODE_IPC_HOOK:-}" ]]; then
    container_hostname="vscode-$host-$stem"
else
    container_hostname="cli-$host-$stem"
fi
container_hostname="$(printf '%s' "$container_hostname" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-')"
container_hostname="${container_hostname#-}"
container_hostname="${container_hostname:0:63}"
container_hostname="${container_hostname%-}"
{
    echo "LOCAL_WORKSPACE_FOLDER=$LOCAL_WORKSPACE_FOLDER"
    # Compose has no equivalent of devcontainer.json's ${localWorkspaceFolderBasename},
    # so export it here. It must stay in sync with `workspaceFolder` in
    # devcontainer.json, which is /workspaces/${localWorkspaceFolderBasename}.
    echo "WORKSPACE_BASENAME=$(basename "$LOCAL_WORKSPACE_FOLDER")"
    echo "CONTAINER_HOSTNAME=$container_hostname"
} >> "$script_dir/.env"

HOST_MCP_DIR="$HOME/.docker/mcp"
CONTAINER_MCP_DIR="/root/.docker/mcp"
if [[ -d "$HOST_MCP_DIR" ]]; then
    {
        echo "HOST_MCP_DIR=$HOST_MCP_DIR"
        echo "CONTAINER_MCP_DIR=$CONTAINER_MCP_DIR"
        echo "COMPOSE_PROFILES=mcp"
    } >> "$script_dir/.env"
    # Ensure the secrets socket stub exists so Docker Compose always bind-mounts a file,
    # not a directory (Linux creates a directory when the source path is missing).
    touch "/tmp/stub-secrets-engine.sock"
else
    # Ensure the container MCP dir exists to avoid bind mount errors, even if empty.
    mkdir -p "/tmp/stub-mcp"
fi

# docker/mcp/ secrets are served to the container by mounting the host's
# docker-secrets-engine socket directly (see HOST_SECRETS_SOCKET below); the
# gateway and the devcontainer service both talk to that socket, so no
# secret export/import step is needed here.
HOST_SECRETS_SOCKET="$HOME/Library/Caches/docker-secrets-engine/engine.sock"
DOCKER_SECRETS_ENGINE_SOCKET="/root/.cache/docker-secrets-engine/engine.sock"
if [[ -S "$HOST_SECRETS_SOCKET" ]]; then
    {
        echo "HOST_SECRETS_SOCKET=$HOST_SECRETS_SOCKET"
        echo "DOCKER_SECRETS_ENGINE_SOCKET=$DOCKER_SECRETS_ENGINE_SOCKET"
    } >> "$script_dir/.env"
else
    touch "/tmp/stub-secrets-engine.sock"
fi
