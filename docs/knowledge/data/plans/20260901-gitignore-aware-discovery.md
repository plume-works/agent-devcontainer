---
created: 2026-09-01
type: plan
---

# Gitignore-aware file discovery in validate_agent_files

## Context

`validate_agent_files` discovers `SKILL.md`, `*.agent.md`, and `*.prompt.md` by
raw `os.walk`, pruning only a hardcoded `EXCLUDED_DIRS` denylist. It never
consults `.gitignore`. When the CLI walks a repository root (the CI job runs
`validate_agent_files --recommend .`), any gitignored tree that happens to
contain a matching file — a vendored or generated `SKILL.md`, scratch copies
under `.tmp/` — is validated as if the repo owned it, producing spurious
findings and wasted traversal. The tool always runs inside this repository's
Docker image, where `git` is guaranteed present.

The pre-commit hook is unaffected: it passes a tight staged-file list
(`pass_filenames: true`), so gitignored files never reach discovery there. The
gap is only the directory-walking entry points.

## Approach

Consult git at each walk root and let it decide what is ignored. When the walk
root is inside a git work tree, `git check-ignore` is the sole authority for
what to skip; the `EXCLUDED_DIRS` denylist is *not* applied. When the root is
not a git work tree, no ignore source exists, so discovery falls back to the
denylist — now an injectable parameter defaulting to today's set. `.git/` is
pruned unconditionally in both cases, because `git check-ignore` does not report
it and it never holds a matching file.

`git check-ignore` (rejected alternative:
`git ls-files --others --exclude-standard`) is the correct primitive: it answers
"is this path ignored" for any path whether tracked or not, whereas `ls-files`
conflates ignore state with tracked state. One batched
`git check-ignore --stdin -z` invocation per walk root feeds it every candidate
path at once, rather than a process per directory.

Making `EXCLUDED_DIRS` a parameter (rejected alternative: keep it a module
constant applied always, alongside git) keeps a single ignore authority in the
common case — a repo expresses "skip `__pycache__`" through `.gitignore`, which
every real repo already does — and reserves the hardcoded list for the
no-git-context fallback where nothing else can answer.

## Implementation Steps

### Task 1: Git ignore helper

**Files:** Modify:
`py_packages/validate_agent_files/validate_agent_files/loaders.py`

- [x] Add `_in_work_tree(root)` — returns whether `root` is inside a git work
  tree via `git -C <root> rev-parse --is-inside-work-tree`, treating a non-zero
  exit, missing binary, or any subprocess error as `False` (degrade, never
  raise).
  - **Evidence:** `_in_work_tree` added in
    `py_packages/validate_agent_files/validate_agent_files/loaders.py:22`; smoke
    test returned `True` for the repo root and `False` for `/`;
    `uv run ruff check` / `ruff format --check` on `loaders.py` pass.
- [x] Add `_git_ignored(root, candidates)` — runs one
  `git -C <root> check-ignore --stdin -z` fed all candidate paths NUL-
  separated, returning the subset git reports as ignored as a set of absolute
  paths. On any subprocess failure return an empty set (nothing ignored) so
  discovery degrades to the fallback rather than failing.
  - **Evidence:** `_git_ignored` added in
    `py_packages/validate_agent_files/validate_agent_files/loaders.py:38`; smoke
    test reported `.tmp/x` ignored and `README.md` not; exit codes 0/1 treated
    as success, others degrade to empty set; ruff check/format pass.

### Task 2: Apply the decision in both walkers

**Files:** Modify:
`py_packages/validate_agent_files/validate_agent_files/loaders.py`

- [x] Rename the module constant to `DEFAULT_EXCLUDED_DIRS` (keep membership
  identical to today) and add `excluded_dirs` keyword parameters defaulting to
  it on `find_skill_files`, `find_agent_files`, `find_prompt_files`, and the
  shared `_find_matching_files`. `SkillFileLoader.find_skill_files` forwards the
  parameter.
  - **Evidence:** constant renamed at `loaders.py:19` (membership unchanged) and
    `excluded_dirs` added to all four functions plus the loader method; no
    remaining importers of the old name (`grep` clean); ruff check/format pass.
- [x] In both `os.walk` bodies compute `in_repo = _in_work_tree(root)` once per
  root. When `in_repo`, prune a directory iff it is `.git` OR `git check-ignore`
  flags it; when not, prune iff its basename is `.git` OR in `excluded_dirs`.
  `.git` is pruned in both branches.
  - **Evidence:** `in_repo` computed once per walk root in `find_skill_files`
    (`loaders.py:108`) and `_find_matching_files` (`loaders.py:~248`); shared
    `_kept_subdirs` (`loaders.py:73`) drops `.git` unconditionally then applies
    git-vs-`excluded_dirs`; 136 existing package tests pass unchanged.
- [x] Filter matched files through `_git_ignored` when `in_repo` so an ignored
  file beside tracked siblings in a walked directory is dropped; when not
  `in_repo` keep all matched files (no file-level filtering in the fallback).
  - **Evidence:** both walkers filter matched files through `_git_ignored` only
    when `in_repo` (`loaders.py:113-115` and the `_find_matching_files` body),
    keeping all matches in the fallback; Task 3 tests exercise the drop and the
    fallback; ruff check/format pass and 136 existing tests stay green.

### Task 3: Tests

**Files:** Create:
`py_packages/validate_agent_files/tests/test_gitignore_discovery.py`

- [ ] Temp git repo with `.gitignore`: an ignored directory containing a
  matching file is pruned, an ignored file beside a tracked matching sibling is
  dropped, and tracked matching files are kept. Covers all three suffixes
  (`SKILL.md`, `.agent.md`, `.prompt.md`).
- [ ] Non-repo directory: the `excluded_dirs` parameter governs dir pruning; a
  custom `excluded_dirs` overrides the default; a directory name absent from
  `excluded_dirs` is walked (proving git rules are not applied outside a repo).
- [ ] `.git/` is pruned in both the repo and non-repo cases.
- [ ] Fixtures build their own temp git repo and use invented names — no
  dependence on this repository's identity, per the package's `AGENTS.md`.

## Spec changes

`data/spec/agent-file-discovery` (does not exist yet): **When the walk root is
inside a git work tree, `validate_agent_files` discovery SHALL skip every path
`git check-ignore` reports as ignored and SHALL always skip `.git/`; when the
root is not a git work tree, discovery SHALL fall back to pruning directories
named in the caller-supplied excluded-directory set and SHALL apply no file-
level filtering.** Any git failure SHALL degrade to the non-repo fallback rather
than aborting discovery.

## Verification

- `uv run --isolated --extra dev pytest tests/test_gitignore_discovery.py` from
  the package root passes (isolated proves the package-standalone constraint).
- `uv run pytest` from the package root — full package suite green, confirming
  the parameter default preserves existing discovery behavior.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  from the repo root passes and no longer reports files under gitignored trees.

## Out of scope

- The pre-commit hook path (already staged-file-scoped; unaffected).
- Nested `.gitignore` precedence logic beyond what `git check-ignore` already
  resolves — git owns it; the tool does not reimplement it.
- Caching git results across multiple requested paths in one CLI run.

## Key references

Verified anchor points (line numbers as of 2026-09-01):

- `py_packages/validate_agent_files/validate_agent_files/loaders.py:18` —
  `EXCLUDED_DIRS` constant
- `py_packages/validate_agent_files/validate_agent_files/loaders.py:31` —
  `find_skill_files`
- `py_packages/validate_agent_files/validate_agent_files/loaders.py:42-43` —
  skill walk + `dirs[:]` prune
- `py_packages/validate_agent_files/validate_agent_files/loaders.py:167` —
  `SkillFileLoader.find_skill_files`
- `py_packages/validate_agent_files/validate_agent_files/loaders.py:176` —
  `_find_matching_files`
- `py_packages/validate_agent_files/validate_agent_files/loaders.py:184-185` —
  matching walk + `dirs[:]` prune
- `py_packages/validate_agent_files/validate_agent_files/loaders.py:193` —
  `find_agent_files`
- `py_packages/validate_agent_files/validate_agent_files/loaders.py:198` —
  `find_prompt_files`
