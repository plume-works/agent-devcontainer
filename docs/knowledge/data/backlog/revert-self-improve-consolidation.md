---
type: task
stage: pending
priority: medium
created: 2026-11-15
description: Remove the self-improve plugin, because it got no development and the knowledge base and its process do its function.
sources:
- resource: https://github.com/plume-works/agent-devcontainer/pull/134
  title: Consolidate self-improve and plan resumable Claude reviews
---

# Remove the self-improve plugin

Remove the `self-improve` plugin from this repository, with all that pull
request #134 added for it.

The plugin got no development after pull request #134 put it in this repository.
Its function is to keep a lesson from a session in a permanent file. The
knowledge base and its process now do that function: `AGENTS.md#project-memory`
sends each lesson to `AGENTS.md` or to a document under `docs/knowledge/data/`.
The plugin is thus a second product that the repository maintains and does tests
on for no use.

The work removes these:

- `.agents/plugins/self-improve/`, and its entry in
  `.claude-plugin/marketplace.json`.
- The connections to the plugin: `SELF_IMPROVE` and its targets in `Makefile`,
  the test path in `pyproject.toml`, the steps in `.github/workflows/ci.yml` and
  `.github/workflows/validate-agent-files.yml`, and the `self-improve` lines in
  `.gitignore`.
- The text about the plugin in `README.md`, and the rules in `AGENTS.md` that
  apply only to the plugin.
- The glossary terms that only the plugin uses.

The work closes these documents in the graph:

- The open bugs, the backlog task, and the idea in `data/someday/` about the
  plugin, each as cancelled.
- ADR 0087, 0088, 0089, and 0090, each as deprecated.

The work makes these decisions:

- If the research under `docs/research/` that pull request #134 added stays.
- If the reinstallation of plugins in the Claude catalog keeps its loop through
  all published plugins when only `agentdev` stays.

The changes to the review responder and the review-resume plan of pull request
#134 are not part of this task.

If one session cannot complete the work, the task becomes a plan.
