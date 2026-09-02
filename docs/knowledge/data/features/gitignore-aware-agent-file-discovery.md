---
type: feature
stage: implemented
description: validate_agent_files skips gitignored files during repository-wide discovery while preserving explicit-file validation and plain-directory fallbacks.
generated:
  by: codex/gpt-5
  at: 2026-09-02T05:46:35Z
sources:
- resource: docs/knowledge/data/plans/20260901-gitignore-aware-discovery.md
- resource: docs/knowledge/data/spec/agent-file-discovery.md
- resource: py_packages/validate_agent_files/validate_agent_files/loaders.py
- resource: py_packages/validate_agent_files/tests/test_gitignore_discovery.py
---

# Gitignore-aware agent file discovery

## Purpose

Repository-wide validation should inspect files the repository owns, not
generated or vendored material that `.gitignore` already excludes. This keeps
`validate_agent_files --recommend .` focused on the canonical agent, skill, and
prompt sources while retaining standalone package behavior outside git work
trees.

## Behaviour

**Directory walks inside git work trees follow git ignore rules.**
`validate_agent_files` asks git to classify candidate directories and matching
files during discovery, so ignored `SKILL.md`, `.agent.md`, and `.prompt.md`
files are skipped before validation.

**Plain directories still use explicit directory pruning.** When there is no git
work tree, callers can supply an excluded-directory set; absent that, discovery
uses the package default.

**Explicit file paths stay direct.** A caller that passes a matching file path
gets that file back from discovery; the gitignore behavior only governs
directory walks.

**Git failures degrade instead of failing validation.** If git cannot identify a
work tree, discovery uses the plain-directory fallback. If git cannot classify
candidates inside a work tree, discovery keeps walking and treats those
candidates as not ignored.

## References

- Plan:
  [Gitignore-aware file discovery in validate_agent_files](../plans/20260901-gitignore-aware-discovery.md)
- Spec: [Agent file discovery](../spec/agent-file-discovery.md)
