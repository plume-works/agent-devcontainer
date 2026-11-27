#!/bin/zsh
# Provision a stock macOS host to run the agentdev catalog natively.
# Why zsh: see ADR-0040.
emulate -R zsh
setopt err_exit no_unset pipe_fail

typeset -r PYTHON_VERSION=3.12
# The repository files that declare and install the catalog's toolchain: see ADR-0111.
typeset -r TOOLCHAIN_URL=${AGENTDEV_TOOLCHAIN_URL:-https://raw.githubusercontent.com/plume-works/agent-devcontainer/main}
typeset -r TOOLCHAIN_FILES=(scripts/install-toolchain mise.toml mise.lock)

typeset -r MARKETPLACE_REPO=plume-works/agent-devcontainer
typeset -r MARKETPLACE=agent-devcontainer
typeset -r PLUGIN=agentdev
typeset -r BIN_DIR=$HOME/.local/bin
typeset -r ZPROFILE=$HOME/.zprofile
typeset -r FISH_CONF=$HOME/.config/fish/conf.d/agentdev.fish
typeset -r MARKER_BEGIN='# >>> agentdev macos-bootstrap >>>'
typeset -r MARKER_END='# <<< agentdev macos-bootstrap <<<'
typeset -r BREW_INSTALL='/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
typeset -r LOGIN_PATH=/usr/bin:/bin:/usr/sbin:/sbin

die() {
  print -ru2 -- "macos-bootstrap: $*"
  exit 1
}

step() {
  print -r -- "==> $*"
}

usage() {
  print -r -- "Usage: macos-bootstrap.zsh [--skip-plugins]

Install the tools the agentdev catalog needs on macOS: mise and Claude Code from
Homebrew, the toolchain mise.toml declares linked into ~/.local/bin, a
uv-managed Python $PYTHON_VERSION as the default python3,
a PATH block in ~/.zprofile, and the $PLUGIN plugin for Claude Code. When fish is installed, the same PATH setup
goes in ~/.config/fish/conf.d/agentdev.fish.

  --skip-plugins  Leave Claude Code's plugins untouched."
}

# Run a command in a login zsh that starts from the system PATH, as a new terminal does.
login_shell() {
  PATH=$LOGIN_PATH ${commands[zsh]:-/bin/zsh} -l -c "$1"
}

install_brew_packages() {
  step "Installing Homebrew packages"
  brew bundle --file=- <<'BREWFILE'
brew "mise"
cask "claude-code"
BREWFILE
}

# The same script and lockfile the devcontainer image and cloud sessions install from.
install_toolchain() {
  local file
  step "Installing the toolchain from $TOOLCHAIN_URL"
  for file in $TOOLCHAIN_FILES; do
    mkdir -p $work/toolchain/${file:h}
    curl -fsSL -o $work/toolchain/$file $TOOLCHAIN_URL/$file
  done
  bash $work/toolchain/scripts/install-toolchain $BIN_DIR
}

install_python() {
  step "Installing Python $PYTHON_VERSION with uv"
  UV_PYTHON_BIN_DIR=$BIN_DIR $BIN_DIR/uv python install $PYTHON_VERSION --default
}

# Replace the marker block in a file in place, or append it; content outside it is kept.
write_block() {
  local file=$1 body=$2 current=$work/${1:t}
  local block="$MARKER_BEGIN
$body
$MARKER_END"
  step "Writing the PATH block in $file"
  mkdir -p ${file:h}
  if [[ -e $file ]]; then
    cat -- $file >$current
  else
    : >$current
  fi
  # ENVIRON, not -v: macOS awk rejects a newline inside a -v value.
  BEGIN_LINE=$MARKER_BEGIN END_LINE=$MARKER_END BLOCK=$block awk '
    BEGIN { begin = ENVIRON["BEGIN_LINE"]; end = ENVIRON["END_LINE"]; block = ENVIRON["BLOCK"] }
    $0 == begin { if (inside || done) { bad = 1; exit } inside = 1; print block; next }
    $0 == end { if (!inside) { bad = 1; exit } inside = 0; done = 1; next }
    !inside { print }
    END { if (bad || inside) exit 2; if (!done) print block }
  ' $current >$current.new ||
    die "$file holds a malformed '$MARKER_BEGIN' block; fix it by hand and re-run"
  cat -- $current.new >$file
}

write_path_blocks() {
  local brew=${(qq)commands[brew]}
  write_block $ZPROFILE "eval \"\$($brew shellenv)\"
export PATH=\"\$HOME/.local/bin:\$PATH\""
  if (( $+commands[fish] )) || [[ ${SHELL:-} == */fish ]]; then
    write_block $FISH_CONF "$brew shellenv fish | source
fish_add_path --move --path \$HOME/.local/bin"
  fi
}

# Fail unless a login shell resolves python3 to the provisioned interpreter.
check_python() {
  local shell=$1 python_path python_version
  python_path=$(PATH=$LOGIN_PATH $shell -l -c 'command -v python3') || python_path='(none)'
  python_version=$(PATH=$LOGIN_PATH $shell -l -c 'python3 --version' 2>&1) ||
    python_version='(failed)'
  print -r -- "  python3 in ${shell:t}: $python_path, $python_version"
  [[ $python_path == $BIN_DIR/python3 && $python_version == "Python $PYTHON_VERSION."* ]] ||
    failures+=("python3 in ${shell:t} (expected Python $PYTHON_VERSION at $BIN_DIR/python3)")
}

install_plugins() {
  step "Installing the $PLUGIN plugin for Claude Code"
  if [[ $(claude plugin marketplace list --json) == *\"$MARKETPLACE\"* ]]; then
    claude plugin marketplace update $MARKETPLACE
  else
    claude plugin marketplace add $MARKETPLACE_REPO --scope user
  fi
  claude plugin install $PLUGIN@$MARKETPLACE --scope user
}

verify() {
  local -a failures
  local tool output
  step "Verifying from a fresh login shell"
  for tool in mise uv jq gh shellcheck bun pre-commit iwe iwes claude; do
    # iwes is a language server without --version; --skip-plugins promises no claude call.
    if [[ $tool == iwes ]] || { (( skip_plugins )) && [[ $tool == claude ]] }; then
      output=$(login_shell "command -v $tool") || { failures+=($tool); continue }
    else
      output=$(login_shell "$tool --version" 2>&1) || { failures+=($tool); continue }
    fi
    print -r -- "  $tool: ${output%%$'\n'*}"
  done

  check_python ${commands[zsh]:-/bin/zsh}
  if [[ -n ${SHELL:-} && ${SHELL:t} != zsh ]]; then
    check_python $SHELL
  fi

  (( $#failures == 0 )) || die "verification failed: ${(j:, :)failures}"
  step "Done. Open a new terminal to pick up the PATH changes."
}

main() {
  local arg work
  local -i skip_plugins=0
  for arg; do
    case $arg in
      --skip-plugins) skip_plugins=1 ;;
      -h | --help) usage; return 0 ;;
      *) usage >&2; die "unknown argument: $arg" ;;
    esac
  done

  [[ $(uname -s) == Darwin ]] || die "macOS only; this host runs $(uname -s)"
  if (( ! $+commands[brew] )); then
    print -ru2 -- "Homebrew is required. Install it with:"
    print -ru2 -- "  $BREW_INSTALL"
    die "then follow its instructions to put brew on PATH and re-run this script"
  fi
  work=$(mktemp -d)
  trap "rm -rf -- ${(q)work}" EXIT

  install_brew_packages
  install_toolchain
  install_python
  write_path_blocks
  (( skip_plugins )) || install_plugins
  verify
}

# Reading stdin from /dev/null keeps `curl ... | zsh` from feeding the script to its own commands.
main "$@" </dev/null
