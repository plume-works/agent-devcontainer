---
type: spec
description: validate_agent_files directory discovery uses git ignore rules inside work trees and caller-supplied directory pruning outside work trees.
generated:
  by: codex/gpt-5
  at: 2026-09-02T05:46:35Z
sources:
- resource: py_packages/validate_agent_files/validate_agent_files/loaders.py
- resource: py_packages/validate_agent_files/tests/test_gitignore_discovery.py
---

# Agent file discovery

## Purpose

`validate_agent_files` discovers skill, agent, and prompt markdown files from
either explicit file paths or directory walks. Directory discovery must avoid
validating generated, vendored, or scratch files that the repository has already
excluded from ownership, while still working in plain directories that have no
git ignore rules.

## Requirements

### Requirement: Git work-tree discovery follows git ignore rules

When a directory walk root is inside a git work tree, discovery SHALL use
`git check-ignore` to prune ignored directories and filter ignored matching
files for `SKILL.md`, `.agent.md`, and `.prompt.md` discovery. The hardcoded
excluded-directory set SHALL NOT be applied in this mode.

#### Scenario: A matching file is under an ignored directory

- **WHEN** a gitignored directory contains a matching skill, agent, or prompt
  file
- **THEN** discovery omits that file

#### Scenario: A matching file is ignored beside an unignored match

- **WHEN** a gitignored matching file shares a walked directory with an
  unignored matching file
- **THEN** discovery omits the ignored file and keeps the unignored file

### Requirement: Git internals are never discovered

Directory discovery SHALL prune `.git/` in both git work trees and plain
directories.

#### Scenario: A matching file appears under `.git/`

- **WHEN** a `.git/` directory contains a matching skill, agent, or prompt file
- **THEN** discovery omits that file even if `.git` is absent from the caller's
  excluded-directory set

### Requirement: Plain-directory discovery uses caller-supplied pruning

When a directory walk root is not inside a git work tree, discovery SHALL prune
directories whose basename is in the caller-supplied excluded-directory set and
SHALL apply no file-level ignore filtering.

#### Scenario: The default excluded-directory set applies outside git

- **WHEN** a plain directory contains a matching file under a directory named in
  the default excluded-directory set
- **THEN** discovery omits that file

#### Scenario: A caller supplies a custom excluded-directory set

- **WHEN** a plain-directory walk receives a custom excluded-directory set
- **THEN** discovery uses that set instead of the default set

### Requirement: Git failures do not abort discovery

Discovery SHALL continue when git is unavailable, reports that a root is not
inside a work tree, or cannot classify ignore status for candidate paths. A
failure to identify a work tree SHALL use plain-directory discovery; a failure
while classifying candidates inside an identified work tree SHALL treat those
candidates as not ignored.

#### Scenario: Git cannot identify a work tree

- **WHEN** the work-tree probe fails or reports a non-work-tree root
- **THEN** discovery falls back to plain-directory discovery

#### Scenario: Git cannot classify ignored candidates

- **WHEN** ignore classification fails for candidate directories or files inside
  an identified work tree
- **THEN** discovery keeps those candidates and continues
