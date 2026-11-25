# shellcheck shell=sh
# agentdev: a `docker exec` shell has no login session, so point `systemctl --user` at the
# lingering user manager's runtime directory.
if [ -z "${XDG_RUNTIME_DIR:-}" ] && [ -d "/run/user/$(id -u)" ]; then
  XDG_RUNTIME_DIR="/run/user/$(id -u)"
  export XDG_RUNTIME_DIR
fi
