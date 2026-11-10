# validate_agent_files

CLI tools for validating skills, agent files, and prompt files.

## Installation

```bash
pip install -e .
```

## Usage

```bash
validate_agent_files                     # Validate skills, agents, and prompts under .
validate_agent_files <plugin>/skills <plugin>/agents         # Validate specific directories
validate_agent_files --kind skills       # Validate only skill files
validate_agent_files --kind agents       # Validate only agent files
validate_agent_files --kind prompts      # Validate only prompt files
validate_agent_files --recommend         # Show recommendations
validate_agent_files --ci                # CI mode (nonzero exit on errors)
validate_agent_files . --mode plugin     # Also validate the plugin packaging it finds
validate_agent_files . --require-marketplace claude codex   # Require both ecosystems
```

## Notes

- `skills-ref` is a required dependency and the primary validator for skill files.
- Every argument is a real path and must exist. A path that resolves to nothing — a typo, or
  a location the catalog has moved away from — is an error, so a run that validates nothing
  can never be mistaken for a pass. A path that exists but holds no skills, agents, or
  prompts is an error for the same reason.
- `--mode plugin` adds plugin packaging to the run, which is how a repository root — sitting
  above its plugins rather than inside one — gets its manifests validated. Plugins are found
  through the well-known marketplace manifests (`.claude-plugin/marketplace.json` and
  `.agents/plugins/marketplace.json`), so the catalog keeps being validated after it moves.
  Both source forms are understood (`"./path"` and `{"source": "local", "path": "./path"}`),
  remote sources are skipped, and a plugin reached both from the command line and from a
  marketplace is validated once. Nothing is required in this mode: a missing marketplace or a
  plugin that ships for one ecosystem and not another is fine, while everything present must
  be valid, and a manifest pointing at a source that is not on disk is still an error.
- `--require-marketplace <ecosystem>...` implies `--mode plugin` and turns an ecosystem's
  packaging into a gate. Nothing
  is required by default: a plugin that ships for Claude but not Codex is a normal plugin, so
  requiring a manifest unconditionally would make the tool specific to one repository. For
  each named ecosystem — `claude` (`.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`)
  and `codex` (`.agents/plugins/marketplace.json`, `.codex-plugin/plugin.json`) — the
  marketplace manifest must exist and parse, every plugin it references must be on disk, and
  each of those plugins must carry a definition that parses, declares a `name` and `version`,
  and names the same plugin the marketplace publishes. A repository that promises to publish
  for both ecosystems names both in CI: `--require-marketplace claude codex`.
- Local validation still checks repository-specific rules such as duplicate skill names
  (identical copies of one skill, such as one installed for both `.claude/skills/` and
  `.opencode/skills/`, are not duplicates), cross-references, agent handoffs, and prompt `#file:` references.
- The test suite is self-contained: run `pytest` from this directory. Its fixtures describe a
  fictional repository (see `tests/mock_catalog.py`), and nothing in `tests/` may reference a
  path outside this package — the tool is general, so its tests must not encode the identity
  or layout of whichever repository happens to develop it.
- When a validated path sits inside a Claude Code plugin, its manifests are checked in every
  mode: the plugin manifest and its marketplace entry must parse and agree on `version`, the
  Claude and Codex manifests must describe the same release, and no skill body may contain a
  literal repository-relative catalog path (`.claude/skills/...`), which does not resolve
  from a plugin cache.
