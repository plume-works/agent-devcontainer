---
type: task
stage: done
priority: medium
created: 2026-11-15
description: Remove the self-improve plugin, because no person changed it after it came into the repository, and the graph and its process do its function.
sources:
- resource: https://github.com/plume-works/agent-devcontainer/pull/134
  title: Consolidate self-improve and plan resumable Claude reviews
completed: 2026-11-15
---

# Remove the self-improve plugin

Remove the `self-improve` plugin from this repository, with all that pull
request #134 added for it.

No person changed the plugin after pull request #134 put it in this repository.
Its function is to keep a lesson from a session in a permanent file. The graph
and its process now do that function: `AGENTS.md#project-memory` sends each
lesson to `AGENTS.md` or to a document under `docs/knowledge/data/`. For this
reason, the plugin is a second product that the repository keeps and tests, but
that nothing uses.

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

- Keep or delete the research under `docs/research/` that pull request #134
  added.
- Keep or change the loop that installs all published plugins in the Claude
  catalog again, when only `agentdev` stays.

The changes to the review responder and the review-resume plan of pull request
#134 are not part of this task.

If one session cannot complete the work, the task becomes a plan.
