# Agent catalog contributor instructions

These instructions apply only to the catalog publisher source under `.agents/`. They are
intentionally outside the reusable root instructions so a project created from this
repository can delete the publisher source without inheriting its maintenance rules.

## Validation and test ownership

- Validate catalog changes with
  `uv run validate_agent_files --recommend . --require-marketplace claude codex`.
- After editing a script the plugin ships, also run
  `uv run pytest .agents/plugins/agentdev/tests`.
- Tests for scripts shipped by the plugin belong in `.agents/plugins/agentdev/tests/` and
  anchor on the plugin root. Validator library and CLI behavior belongs in
  `py_packages/validate_agent_files/tests/`; never mix the two suites.
- Plugin tests must pass from a consumer's plugin cache. Resolve scripts through the
  `plugin_root` fixture instead of spelling out `.agents/plugins/agentdev/...`.
- The plugin test suite owns its `plugin_tmp_path` scratch fixture and `.gitignore` because
  the repository's root ignore rules do not travel with an installed plugin.
- Build fixtures from made-up marketplace, plugin, organization, and path values rather
  than this repository's published identity.
- Keep reusable mock identity in one shared module per plugin test package and import its
  constants and builders so a fixture change lands in one place.

## Catalog locations and portability

- `.agents/plugins/agentdev/` is the canonical source for Claude Code and Codex agents,
  skills, hooks, helper commands, and plugin tests. Skills are namespaced as
  `/agentdev:<skill-name>`.
- Codex consumes the same tree through
  `.agents/plugins/agentdev/.codex-plugin/plugin.json`; never create a separate Codex copy.
- Update `.agents/plugins/agentdev/` sources directly.
- Never write a repository-relative catalog path inside the plugin. A skill references its
  own bundled code as `agent-code/<file>`, relative to the skill directory, and reaches a
  sibling skill by its namespaced invocation. `${CLAUDE_SKILL_DIR}` appears only in
  `allowed-tools`: `Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`.
- No link inside the plugin may resolve outside the plugin root. Describe per-repository
  files such as `AGENTS.md`, lint configuration, and pull request templates in prose so
  they resolve in the repository using the installed plugin.
- The validator enforces plugin containment across every Markdown file the plugin ships,
  including `references/` pages and the plugin README.
- Keep the Claude and Codex plugin manifest versions aligned when releasing the catalog.
