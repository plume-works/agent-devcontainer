# agentdev: fish defaults for every account and every fish shell.
# A `docker exec` shell has no login session; see /etc/profile.d/agentdev-xdg-runtime.sh.
if not set -q XDG_RUNTIME_DIR; and test -d /run/user/(id -u)
    set -gx XDG_RUNTIME_DIR /run/user/(id -u)
end
fish_add_path -g "$HOME/.local/bin"
if test -d "$HOME/.bun/bin"
    fish_add_path -g "$HOME/.bun/bin"
end
