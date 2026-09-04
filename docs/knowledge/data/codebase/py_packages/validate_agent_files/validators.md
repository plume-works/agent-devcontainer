---
type: codebase
description: 'The rule modules the engine composes: skill frontmatter and structure, agent handoffs, prompts, name uniqueness, cross-references, plugin manifests, marketplaces, bundled Markdown containment, and literal catalog paths.'
source: py_packages/validate_agent_files/validate_agent_files/validators
source_digest: sha256:9c3d6ff531d5822eab54ba4839334a12f2b3e4806ac5a9e0923b26341b3edcb8
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
sources:
- id: code
  resource: py_packages/validate_agent_files/validate_agent_files/validators
---

# Validator rules

One module per concern, each returning `ValidationIssue`s or a
`ValidationResult` and holding no state beyond its inputs.

## Public surface

| Module                | Entry points                                                                        | Rule                                                                   |
| --------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `skill.py`            | `SkillFrontmatterValidator`, `SkillStructureValidator`                              | frontmatter keys and description quality; directory shape              |
| `agents.py`           | `validate_agent_frontmatter`, `validate_handoff`, `build_known_agent_targets`       | `.agent.md` frontmatter and handoff targets that exist                 |
| `prompts.py`          | `validate_prompt_frontmatter`, `validate_prompt_body`, `validate_prompt_references` | `.prompt.md` shape and `#file:` references                             |
| `uniqueness.py`       | `UniquenessValidator`                                                               | no two skills share a name                                             |
| `cross_reference.py`  | `CrossReferenceValidator`                                                           | links between catalog files resolve                                    |
| `plugin_manifest.py`  | `find_plugin_root`, `find_packaged_plugin_root`, `validate_plugin_manifests`        | manifests parse, agree on `version`, name the same plugin              |
| `marketplace.py`      | `validate_required_marketplaces`, `validate_present_marketplaces`                   | an ecosystem's manifest exists, parses, and points at plugins on disk  |
| `bundled_markdown.py` | `find_bundled_markdown`, `validate_bundled_markdown`                                | `references/` pages and the plugin README stay inside the plugin       |
| `catalog_paths.py`    | `validate_catalog_paths`                                                            | no literal `.claude/skills/` or `.claude/agents/` path in a skill body |

## How it works

`core.py` calls the marketplace and manifest validators once per run and the
per-file validators per discovered file; `catalog_paths` runs on skill bodies
because a repository-relative path resolves nowhere from a plugin cache.

## Depends on

`loaders.py` for frontmatter parsing and `types.py` for the result types.

## Invariants & gotchas

- `~/.claude/...` is a personal catalog and is not flagged; only
  repository-relative `.claude/` paths are.
- Marketplace requirements are opt-in per ecosystem so the tool stays general;
  nothing is required by default.

## Key references

Verified anchor points (line numbers as of 2026-09-04):

- `.../validators/skill.py:11,123` — the two skill validators
- `.../validators/agents.py:12,67` — frontmatter and handoff
- `.../validators/plugin_manifest.py:69` — `validate_plugin_manifests`
- `.../validators/marketplace.py:32,51` — required and present marketplaces
- `.../validators/bundled_markdown.py:47` — containment
- `.../validators/catalog_paths.py:30` — literal-path guard

(`...` is `py_packages/validate_agent_files/validate_agent_files`.)
