---
type: codebase
description: The independently released Python package that validates skills, agents, prompts, and plugin packaging; its CLI is the repository gate and ships in the image as a uv tool.
source: py_packages/validate_agent_files
source_digest: sha256:3130f9e88bca3d31e6089d423434c2729edd3afd86b6a628cdf3167077e41384
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
sources:
- id: code
  resource: py_packages/validate_agent_files
---

# validate_agent_files package

A setuptools package (`version = "1.0.0"`, Python 3.11+, depending on `PyYAML`
and `skills-ref`) exposing the `validate_agent_files` console script. It must
build and test with no knowledge of this repository, because the image installs
it from its own directory alone.

## Contains

[Validators](validate_agent_files/validators.md)

[Package tests](validate_agent_files/tests.md)

## Public surface

- `validate_agent_files` console script → `__main__:main` → `main.main()`; the
  CLI contract is
  [the validator CLI interface](../api-validate-agent-files-cli.md)
- `validate_agent_files.__init__` exports `CustomizationsValidationEngine`,
  `ValidationEngine`, `ValidationIssue`, `ValidationLevel`, `ValidationResult`,
  `skills_ref_validate`
- `loaders.find_skill_files`, `find_agent_files`, `find_prompt_files` —
  gitignore-aware discovery
- `paths.find_plugin_roots` — plugins published by the two marketplace manifests

## How it works

`cli.parse_arguments` builds the namespace; `main` constructs
`CustomizationsValidationEngine` with warnings, required marketplaces, and mode,
calls `validate_paths`, and exits `1` if any result is invalid. `validate_paths`
resolves every requested path (a missing or empty path is itself a failure),
validates required and present marketplaces, then plugin manifests and bundled
Markdown containment for every plugin root it can see, then discovers and
validates skills, agents, and prompts by `kind`. Discovery walks the tree
skipping gitignored entries when inside a work tree. Formatters render text,
JSON, or CSV.

## Depends on

`skills-ref` as the primary skill validator; `git` for ignore-aware discovery;
nothing in this repository.

## Invariants & gotchas

- Package tests may not reference a path outside the package; verify with
  `uv run --isolated --extra dev pytest` from the package directory.
- `version` is pinned by `VALIDATE_AGENT_FILES_VERSION` in the Dockerfile and
  verified by [its role](../ansible/roles/validate_agent_files.md).
- Plugin mode is implied by `--require-marketplace`; `files` mode still
  validates the manifests of any plugin a requested path sits inside.

## Key references

Verified anchor points (line numbers as of 2026-09-04):

- `py_packages/validate_agent_files/validate_agent_files/main.py:15` — `main`
- `py_packages/validate_agent_files/validate_agent_files/cli.py:13` —
  `parse_arguments`
- `py_packages/validate_agent_files/validate_agent_files/core.py:145` —
  `CustomizationsValidationEngine`
- `py_packages/validate_agent_files/validate_agent_files/core.py:167` —
  `validate_paths`
- `py_packages/validate_agent_files/validate_agent_files/loaders.py:40` —
  `_git_ignored`
- `py_packages/validate_agent_files/validate_agent_files/paths.py:54` —
  `find_plugin_roots`
- `py_packages/validate_agent_files/pyproject.toml:9` — the version pin
