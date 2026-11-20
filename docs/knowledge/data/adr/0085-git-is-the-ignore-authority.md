---
type: adr
stage: accepted
description: Inside a git work tree, agent file discovery asks git which paths to ignore, and the excluded-directory set applies only outside a work tree.
---

# Git decides which paths agent file discovery ignores

`validate_agent_files` examines directories to find skill, agent, and prompt
files. Inside a git work tree, it sends the candidate paths of each directory to
one `git check-ignore --stdin -z` call rather than run a process per path, and
it does not use a path that git ignores. Git answers for any path, tracked or
not, and handles the precedence of nested `.gitignore` files itself. The
excluded-directory set, a list of directory names that discovery skips, applies
only outside a work tree, so the `.gitignore` files of a repository are the one
source of ignore rules.

## Considered Options

- `git ls-files --others --exclude-standard`. Rejected: it mixes the ignore
  state of a path with its tracked state.
- Use the excluded-directory set inside a work tree too. Rejected: it makes two
  ignore authorities, and a repository could not un-skip a directory that the
  set names.
