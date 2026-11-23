# agentdev: interactive fish defaults for every account.
if status is-interactive
    fish_add_path -g "$HOME/.local/bin"
    if test -d "$HOME/.bun/bin"
        fish_add_path -g "$HOME/.bun/bin"
    end
end
