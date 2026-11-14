---
type: adr
stage: accepted
description: Inside a git work tree, agent file discovery asks git which paths to ignore, and the excluded-directory set applies only outside a work tree.
---

# Git decides which paths agent file discovery ignores

`validate_agent_files` examines directories to find skill, agent, and prompt
files. Inside a git work tree, it sends the paths of each directory to one
`git check-ignore --stdin -z` call. It does not use a path that git ignores. The
excluded-directory set applies only outside a work tree, so the `.gitignore`
files of a repository are the one source of ignore rules.

## Considered Options

- `git ls-files --others --exclude-standard`. Rejected: it mixes the ignore
  state of a path with its tracked state.
- Use the excluded-directory set inside a work tree too. Rejected: a repository
  then cannot include a directory that the set names.

## Consequences

- Discovery never examines `.git/`, because the ignore rules of git do not name
  it
  (`py_packages/validate_agent_files/validate_agent_files/loaders.py::_kept_subdirs`).
