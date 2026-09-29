# shellcheck shell=bash
# Sourced by skill scripts that must recognize a repository's default branch;
# not executable on its own.

is_default_branch() {
  local branch_name="$1"
  [[ "${branch_name}" == "main" || "${branch_name}" == "master" ]]
}

# Print the branch the remote calls its default: refs/remotes/<remote>/HEAD
# first, then GitHub's answer for the remote URL. Returns 1 when neither knows.
remote_default_branch() {
  local remote_name="$1"
  local symref remote_url name

  if symref="$(git symbolic-ref --quiet --short "refs/remotes/${remote_name}/HEAD" 2>/dev/null)"; then
    printf '%s\n' "${symref#"${remote_name}"/}"
    return 0
  fi

  command -v gh >/dev/null 2>&1 || return 1
  remote_url="$(git remote get-url "${remote_name}" 2>/dev/null)" || return 1
  name="$(gh repo view "${remote_url}" --json defaultBranchRef --jq '.defaultBranchRef.name' \
    2>/dev/null)" || return 1
  [[ -n "${name}" ]] || return 1
  printf '%s\n' "${name}"
}
