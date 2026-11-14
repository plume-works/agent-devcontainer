---
type: spec
description: validate_agent_files directory discovery uses git ignore rules inside work trees and caller-supplied directory pruning outside work trees, and agent tooling reads its own namespaced key from `.agent.metadata.json` files.
sources:
- resource: py_packages/validate_agent_files/validate_agent_files/loaders.py
- resource: py_packages/validate_agent_files/tests/test_gitignore_discovery.py
- resource: .agents/plugins/agentdev/skills/template-consume/agent-code/check-updates.py
- resource: .agents/plugins/agentdev/tests/test_template_consume_check_updates.py
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: py_packages/validate_agent_files/validate_agent_files/validators/bundled_markdown.py
- resource: py_packages/validate_agent_files/validate_agent_files/core.py
- resource: py_packages/validate_agent_files/validate_agent_files/main.py
- resource: py_packages/validate_agent_files/validate_agent_files/cli.py
---

# Agent file discovery

## Purpose

`validate_agent_files` discovers skill, agent, and prompt markdown files from
either explicit file paths or directory walks. Directory discovery must avoid
validating generated, vendored, or scratch files that the repository has already
excluded from ownership, while still working in plain directories that have no
git ignore rules.

Agent tooling also finds per-directory metadata in `.agent.metadata.json` files,
each a JSON object whose top-level keys belong to one consumer apiece.

## Requirements

### Requirement: Git failures do not abort discovery

Discovery SHALL continue when git is unavailable, reports that a root is not
inside a work tree, or cannot classify ignore status for candidate paths. A
failure to identify a work tree SHALL use plain-directory discovery; a failure
while classifying candidates inside an identified work tree SHALL treat those
candidates as not ignored.

#### Scenario: Git cannot classify ignored candidates

- **WHEN** ignore classification fails for candidate directories or files inside
  an identified work tree
- **THEN** discovery keeps those candidates and continues

### Requirement: Agent metadata files namespace one consumer per key

An `.agent.metadata.json` file SHALL be a JSON object whose top-level keys each
belong to one consumer. A consumer SHALL read only its own key, and SHALL treat
a file that carries keys of other tools as valid. A file the consumer cannot
parse SHALL be reported as broken metadata rather than skipped. The
`template-consume` key is root-only, as `template-consumption` specifies.

#### Scenario: The file carries only another tool's key

- **WHEN** `check-updates.py` reads a root `.agent.metadata.json` that holds an
  `other-skill` key and no `template-consume` key
- **THEN** it reports `NO_MARKER` and selects setup mode, rather than failing on
  the unknown key

#### Scenario: The file is not valid JSON

- **WHEN** `check-updates.py` reads a root `.agent.metadata.json` it cannot
  parse
- **THEN** it reports `INVALID_MARKER` and diffs nothing

## Rationale

### Inside a work tree, git is the one ignore authority

Discovery asks `git check-ignore` whether each candidate is ignored, feeding a
walked directory's candidates to one `git check-ignore --stdin -z` call rather
than a process per path. It answers for any path, tracked or not, and leaves
nested `.gitignore` precedence entirely to git. A repository says "skip
`__pycache__`" in its `.gitignore`, so the excluded-directory set is a
caller-supplied parameter for the no-git fallback only. Git's ignore rules say
nothing about `.git/` itself unless a repository names it, which is why
discovery prunes `.git/` in both modes.

Rejected:

- **`git ls-files --others --exclude-standard`.** It conflates ignore state with
  tracked state.
- **Applying the excluded-directory set inside a work tree too.** Two ignore
  authorities, and a repository could not un-skip a directory the set names.

### One flag hides warnings

`--errors-only` is the one flag that hides warnings, and it wins over
`--recommend`.

Rejected:

- **A `--no-warnings` flag beside `--errors-only`.** Both resolve to the same
  setting, so the second flag is a synonym to keep in step.

### A skill's assets are output, not documents read in place

In the Agent Skills layout, `assets/` beside a `SKILL.md` holds files the skill
copies out as output, whose references resolve where they land. The
`iwe-bootstrap` scaffold is the case in point: its Markdown uses IWE
extension-less links that resolve only once installed in a workspace.

### Agent metadata is a colocated file with one key per consumer

Agent tooling keeps per-directory metadata in `.agent.metadata.json` files that
sit in the directory they describe, one top-level key per consumer, so a file
can carry metadata for tooling a given checkout does not have. A colocated file
inherits the template-boundary class of its directory and travels with it when
the directory is adopted. A consumer whose data is a repository-level singleton,
such as `template-consume`, declares its key root-only and reads the root file
without walking; that key in a nested file is broken metadata.

A per-directory key resolves root-to-leaf from `git rev-parse --show-toplevel`,
accumulates sections shallowest first, reads its globs relative to the directory
of the file that declares them, and marks a file it cannot parse as breaking
every scope whose walk reads it. A metadata file's own bytes are not tracked
content: a consumer fingerprinting a directory excludes them.

Rejected:

- **A single repository-level map.** It is edited at a distance from the
  directories it describes, does not travel when a directory is copied, needs
  its own template-boundary entry, and leaves a stale entry behind when a
  directory moves.
- **Replace rather than accumulate, as `.gitignore` precedence does.** A subtree
  adding one rule would silently drop every inherited one, so a tool quietly
  does less than before.
- **Repository-root-relative globs in every file.** A copied directory's globs
  would point at its old location, removing the portability colocation exists
  for.
- **Skipping an unreadable metadata file.** The tool would silently compute the
  wrong answer, such as reporting content unchanged because the rule that would
  flag it never loaded.
