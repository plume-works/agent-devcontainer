#!/bin/zsh
# Provision a stock macOS host to run the agentdev catalog natively.
# Behavior: see spec/macos-native-bootstrap; why zsh: see openspec/specs/catalog-scripts.
emulate -R zsh
setopt err_exit no_unset pipe_fail

typeset -r PYTHON_VERSION=3.12
# renovate: datasource=github-releases depName=iwe-org/iwe versioning=regex:^iwe-v(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)$
typeset -r IWE_VERSION=iwe-v0.32.0
# Renovate bumps the versions; scripts/refresh-pin-checksums.py rewrites these digests.
typeset -rA SHA256=(
  iwe-arm64 a616c3df4b992df568ff5357172e8162b7a72b8a4f8a1d35ba5fe718e0a8786b
  iwe-amd64 0a168ede305c25632060fe9f9080e7e0964f3c5e7e5037b1b6034b91694036c0
)

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

Install the tools the agentdev catalog needs on macOS: Homebrew packages, a
uv-managed Python $PYTHON_VERSION as the default python3, iwe in ~/.local/bin,
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
brew "uv"
brew "jq"
brew "gh"
brew "shellcheck"
brew "bun"
brew "pre-commit"
cask "claude-code"
BREWFILE
}

install_python() {
  step "Installing Python $PYTHON_VERSION with uv"
  UV_PYTHON_BIN_DIR=$BIN_DIR uv python install $PYTHON_VERSION --default
}

# Download a release archive, verify its SHA-256, and install only the named binaries.
install_release() {
  local key=$1 url=$2
  shift 2
  local archive=$work/${url:t} unpacked=$work/$key digest binary
  step "Installing ${(j:, :)@} from ${url:t}"
  curl -fsSL -o $archive $url
  digest=$(shasum -a 256 $archive)
  digest=${digest%% *}
  [[ $digest == $SHA256[$key] ]] ||
    die "SHA-256 mismatch for ${url:t}: expected $SHA256[$key], got $digest"
  mkdir -p $unpacked $BIN_DIR
  tar -xzf $archive -C $unpacked $@
  for binary; do
    install -m 0755 $unpacked/$binary $BIN_DIR/$binary
  done
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
  for tool in uv jq gh shellcheck bun pre-commit iwe iwes claude; do
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
  local arg arch iwe_target work
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
  case $(uname -m) in
    arm64) arch=arm64 iwe_target=aarch64-apple-darwin ;;
    x86_64) arch=amd64 iwe_target=x86_64-apple-darwin ;;
    *) die "unsupported architecture: $(uname -m)" ;;
  esac

  work=$(mktemp -d)
  trap "rm -rf -- ${(q)work}" EXIT

  install_brew_packages
  install_python
  install_release iwe-$arch \
    https://github.com/iwe-org/iwe/releases/download/$IWE_VERSION/$IWE_VERSION-$iwe_target.tar.gz \
    iwe iwes
  write_path_blocks
  (( skip_plugins )) || install_plugins
  verify
}

# Reading stdin from /dev/null keeps `curl ... | zsh` from feeding the script to its own commands.
main "$@" </dev/null
