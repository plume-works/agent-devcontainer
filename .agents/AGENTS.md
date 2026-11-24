# Agent catalog contributor instructions

These instructions apply only to the catalog publisher source under `.agents/`. They are
intentionally outside the reusable root instructions so a project created from this
repository can delete the publisher source without inheriting its maintenance rules.

## Validation and test ownership

- Validate catalog changes with
  `uv run validate_agent_files --recommend . --require-marketplace claude`.
- After editing a script a plugin ships, also run that plugin's suite, for example
  `uv run pytest .agents/plugins/agentdev/tests`.
- Tests for scripts shipped by a plugin belong in its own `tests/` directory, such as
  `.agents/plugins/agentdev-iwe/tests/`, and anchor on the plugin root. A plugin's suite
  imports nothing from another plugin's suite. Validator library and CLI behavior belongs in
  `py_packages/validate_agent_files/tests/`; never mix the two suites.
- Plugin tests run only in this repository, never from a consumer's plugin cache, and may
  rely on the publisher checkout around the plugin. Resolve scripts through the
  `plugin_root` fixture instead of spelling out `.agents/plugins/<plugin>/...`.
- Each plugin test suite owns its `plugin_tmp_path` scratch fixture and `.gitignore` because
  the repository's root ignore rules do not travel with an installed plugin.
- Build fixtures from made-up marketplace, plugin, organization, and path values rather
  than this repository's published identity.
- Keep reusable mock identity in one shared module per plugin test package and import its
  constants and builders so a fixture change lands in one place.

## Catalog locations and portability

- Each directory under `.agents/plugins/` is the canonical source of one plugin's
  Claude Code and OpenCode agents, skills, hooks, helper commands, and tests:
  `agentdev` for general development work, `agentdev-iwe` for the IWE workflow. Skills
  are namespaced by their plugin, as `/agentdev:<skill-name>` and
  `/agentdev-iwe:<skill-name>`.
- Claude Code consumes the plugins through the marketplace in `.claude-plugin/`; never
  create a separate copy for either harness.
- OpenCode consumes every plugin that the marketplace lists through the OpenCode bridge in
  `.agents/opencode-bridge/`. The bridge takes no runtime dependencies: type-only imports
  and Bun built-ins, nothing to install.
- Update the `.agents/plugins/<plugin>/` sources directly.
- Every Python script under a plugin's `bin/` and `skills/*/agent-code/` runs through a
  `#!/usr/bin/env -S uv run --quiet` shebang in its plugin's uv project, whose
  `pyproject.toml` pins `agentdev-lib`. Shared helpers come from the `agentdev_lib`
  package (`py_packages/agentdev_lib/`), never from another plugin's files; the
  `skill-scripts` skill holds the output contract. The one exception is
  `bin/macos-bootstrap.zsh`, which provisions `uv` and so runs before it exists.
- Never write a repository-relative catalog path inside the plugin. A skill references its
  own bundled code as `agent-code/<file>`, relative to the skill directory, and reaches a
  sibling skill by its namespaced invocation. `${CLAUDE_SKILL_DIR}` appears only in
  `allowed-tools`: `Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`.
- No link inside the plugin may resolve outside the plugin root. Describe per-repository
  files such as `AGENTS.md`, lint configuration, and pull request templates in prose so
  they resolve in the repository using the installed plugin.
- The validator enforces plugin containment across every Markdown file the plugin ships,
  including `references/` pages and the plugin README.
