---
type: spec
description: How the iwe-bootstrap skill installs a blank IWE workspace from the installed agentdev catalog without overwriting existing knowledge, and stops before onboarding.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.py
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md
- resource: .agents/plugins/agentdev/tests/test_iwe_bootstrap.py
- resource: .agents/plugins/agentdev/tests/test_iwe_seed.py
---

# IWE bootstrap

## Purpose

`/agentdev:iwe-bootstrap` installs a blank IWE project-memory workspace into a
repository root from assets shipped with the installed agentdev catalog. Direct
use and full template adoption share it; see [Template
consumption](template-consumption.md) for how adoption composes it.

## Rationale

### The scaffold ships the publisher's own workspace files

The scaffold's `.iwe/` configuration and schemas and its knowledge instructions,
under `skills/iwe-bootstrap/assets/`, are the same bytes this repository's own
workspace uses, so a schema or instruction change here is a scaffold change. A
publisher-side test keeps the two identical and every asset tracked, because a
catalog install copies tracked files only.
