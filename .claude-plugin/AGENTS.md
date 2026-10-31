# Claude marketplace publisher instructions

This directory publishes the catalog developed under `.agents/plugins/agentdev/`.

- Validate changes with
  `uv run validate_agent_files --recommend . --require-marketplace claude`.
- Keep the marketplace entry version aligned with the Claude plugin manifest.
- `.claude/settings.json` is this repository's own strict-JSON Claude configuration; do not
  add comments or trailing commas to it.
- The devcontainer lifecycle registers the marketplace declared here when this repository
  is the active workspace; `.claude/settings.json` does not declare the local installation.
