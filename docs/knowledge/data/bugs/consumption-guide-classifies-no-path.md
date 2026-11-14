---
type: bug
description: The consumption guide names its five path classes one time but gives no path a class. Many tracked template paths are not in the guide.
stage: pending
severity: low
sources:
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: the consumption guide does not give each template path a class

## Symptom

The guide must put each tracked template path in one of its five classes. Then a
consumer knows what to keep, merge, or remove. The guide names the classes in
its opening only. It gives no path a class, and it does not name many tracked
paths. A consumer must guess what to do with them.

## Reproduction

1. Read
   `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`.
2. No path has a class label.
3. The guide does not name `Makefile`, `compose.opencode.yml`,
   `compose.opencode.bind.yml`, `opencode-compose-pins.yml`,
   `agent-devcontainer-and-project.code-workspace`, `docs/research/`,
   `docs/user-stories/`, `scripts/tests/`, `scripts/check-anchors.py`, or nine
   other files under `scripts/`.

## Root cause

`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`
gives its steps by workflow, not by path. The guide did not change when the
template tree received these paths.
