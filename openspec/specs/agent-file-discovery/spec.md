# Agent file discovery Specification

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

### Requirement: agent metadata files namespace one consumer per key

An `.agent.metadata.json` file SHALL be a JSON object whose top-level keys each
belong to one consuming tool. A consumer SHALL read only its own key and leave
every other key as it found it. `template-consume` SHALL read its key only from
the repository-root file, and SHALL treat a `template-consume` key in a nested
`.agent.metadata.json` as broken metadata rather than a value to merge.

#### Scenario: the root file carries a key no installed tool claims

- **WHEN** update mode runs in a repository whose root `.agent.metadata.json`
  holds `template-consume` beside another key
- **THEN** update mode reads `template-consume.consumed_ref` and leaves the other
  key unchanged

## Rationale

### Agent metadata is colocated, namespaced, and accumulates root to leaf

Metadata for agent tooling lives in `.agent.metadata.json` files anywhere in the
tree, one top-level key per consumer, so a directory can declare rules for a
tool a given checkout lacks. The format is general, and template-consume's
root-only adoption state is its only consumer today; a future colocated consumer
follows the contract decided for it. Resolving a file walks from the repository
root, from `git rev-parse --show-toplevel`, down to the file's directory;
sections accumulate shallowest first, with no removal operation; globs are
relative to the directory of the file that declares them, `**` crossing
separators and `*` not; a metadata file is excluded from any consumer's
fingerprint; and a file that cannot be parsed or is rejected marks its own
subtree unresolvable, so a tool never computes an answer from rules it failed to
load. A consumer whose data is a repository singleton declares its key
root-only. A colocated file inherits its directory's template-boundary class,
except the root file, which is classified per key.

Rejected:

- **A single repository-level map of root-relative globs.** It is edited at a
  distance, does not travel when a directory is copied, and leaves stale paths
  behind when a directory moves.
- **Replace rather than accumulate, like `.gitignore` precedence.** A subtree
  adding one rule would silently drop every inherited one.
- **Repository-root-relative globs in every file.** A copied directory's globs
  would point at its old location.
