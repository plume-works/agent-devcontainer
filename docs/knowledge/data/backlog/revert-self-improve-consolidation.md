---
type: task
stage: pending
priority: medium
created: 2026-11-15
description: Remove the self-improve plugin and all that its consolidation added, because the plugin got no development and the knowledge base and its process do the same job.
sources:
- resource: https://github.com/plume-works/agent-devcontainer/pull/134
  title: Consolidate self-improve and plan resumable Claude reviews
---

# Revert the self-improve consolidation

Remove the `self-improve` plugin from this repository, with all that pull
request #134 added for it.

The plugin got no development after the consolidation. Its function is to keep a
lesson from a session in a durable file. The knowledge base and its process now
do that function: `AGENTS.md#project-memory` sends each lesson to `AGENTS.md` or
to a document under `docs/knowledge/data/`. The plugin is thus a second product
that the repository maintains and tests for no use.

The work removes these:

- `.agents/plugins/self-improve/`, and its entry in
  `.claude-plugin/marketplace.json`.
- The wiring: `SELF_IMPROVE` and its targets in `Makefile`, the test path in
  `pyproject.toml`, the steps in `.github/workflows/ci.yml` and
  `.github/workflows/validate-agent-files.yml`, and the `self-improve` lines in
  `.gitignore`.
- The text about the plugin in `README.md`, and the rules in `AGENTS.md` that
  apply only to the plugin.
- The glossary terms that only the plugin uses.

The work closes these documents in the graph:

- The open bugs, the backlog task, and the someday idea about the plugin, each
  as cancelled.
- ADR 0087, 0088, 0089, and 0090, each as deprecated.

The work makes these decisions:

- If the research under `docs/research/` that pull request #134 added stays.
- If the reinstallation of plugins in the Claude catalog keeps its loop through
  all published plugins when only `agentdev` stays.

The responder changes and the review-resume plan of pull request #134 are not
part of this task.

If one session cannot complete the work, the task becomes a plan.
